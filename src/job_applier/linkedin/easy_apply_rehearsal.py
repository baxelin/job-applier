import logging
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from job_applier.linkedin.easy_apply_filler import EasyApplyFiller, FillOutcome, FillStatus
from job_applier.linkedin.easy_apply_form import EasyApplyUnavailableError
from job_applier.linkedin.job_page_parser import JobPageParser
from job_applier.linkedin.job_scanner import ScanResult
from job_applier.linkedin.linkedin_browser import ApplicationBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.rehearsal_evidence import RehearsalEvidence
from job_applier.linkedin.session_guard import SessionBlockedError, SessionGuard
from job_applier.models.job_application import JobApplication, ScanStatus
from job_applier.models.job_posting import JobPosting
from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from job_applier.storage.application_repository import ApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class _Tally(StrEnum):
    READY = "prontas para envio"
    PENDING = "com pergunta sem resposta"
    CLOSED = "encerradas"
    UNAVAILABLE = "indisponíveis"
    FAILED = "com erro"


class _StopRehearsal(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EasyApplyRehearsal:
    """Modo de ensaio: preenche o formulário de cada vaga simplificada e para antes de enviar.

    Cada vaga deixa prints e um respostas.txt em data/ensaios, e o modal é sempre descartado. Perguntas
    sem resposta vão para a aba Perguntas e a vaga fica pendente. Para na hora ao primeiro sinal de
    captcha, logout ou bloqueio, ou quando várias vagas seguidas falharem (provável mudança de layout).
    Vaga encerrada é ignorada sem contar como falha: vagas antigas na fila encerram com frequência, e isso
    não diz nada sobre o layout.
    """

    _CLOSED_REASON = "Vaga encerrada: não aceita mais candidaturas."

    def __init__(
        self,
        browser: ApplicationBrowser,
        filler: EasyApplyFiller,
        resumes: ResumeUploadFileLoader,
        tracker: ApplicationTracker,
        applications: ApplicationRepository,
        pacer: Pacer,
        evidence_dir: Path,
        max_consecutive_failures: int,
        max_jobs: int | None = None,
        now: Callable[[], datetime] = datetime.now,
        page_parser: JobPageParser | None = None,
        retry_pending: bool = False,
    ) -> None:
        self._browser = browser
        self._filler = filler
        self._resumes = resumes
        self._tracker = tracker
        self._applications = applications
        self._pacer = pacer
        self._evidence_dir = evidence_dir
        self._max_consecutive_failures = max_consecutive_failures
        self._max_jobs = max_jobs
        self._now = now
        self._page_parser = page_parser or JobPageParser()
        self._retry_pending = retry_pending
        self._guard = SessionGuard()
        self._tally: Counter[_Tally] = Counter()
        self._consecutive_failures = 0

    def run(self) -> ScanResult:
        jobs = self._applications.list_ready_for_easy_apply(self._max_jobs, self._retry_pending)
        try:
            for position, application in enumerate(jobs, start=1):
                self._rehearse(application)
                if position < len(jobs):
                    self._pacer.after_job(position)
        except _StopRehearsal as stop:
            return self._result(ScanStatus.STOPPED, stop.reason)
        except SessionBlockedError as blocked:
            snapshot = self._browser.save_snapshot("bloqueio")
            return self._result(ScanStatus.STOPPED, f"{blocked.reason} Página salva em {snapshot}.")
        except Exception as error:
            logger.exception("Erro inesperado durante o ensaio.")
            return self._result(ScanStatus.STOPPED, f"Erro inesperado: {error!r}")
        return self._result(ScanStatus.COMPLETED, "Ensaio concluído, nada foi enviado.")

    def _rehearse(self, application: JobApplication) -> None:
        job_id = JobPosting.id_from_url(application.url or "")
        logger.info("Ensaio: %s - %s", application.company, application.title)
        self._pacer.between_actions()
        page = self._browser.open_job(job_id)
        self._guard.check(page)
        if self._page_parser.is_closed(page.text):
            self._handle_closed(application)
            return
        try:
            form = self._browser.open_application_form()
        except EasyApplyUnavailableError as error:
            self._handle_unavailable(application, job_id, str(error))
            return

        evidence = self._evidence_for(application)
        outcome = self._filler.fill(form, application, self._resumes.load(application), evidence)
        if outcome.status is FillStatus.FAILED:
            self._browser.save_snapshot(f"ensaio-{job_id}")
        form.close_without_sending()
        self._record(application, outcome, evidence)

    def _evidence_for(self, application: JobApplication) -> RehearsalEvidence:
        resume_name = Path(application.resume_path or application.job_key).stem
        return RehearsalEvidence(self._evidence_dir / f"{self._now():%Y-%m-%d_%H-%M-%S}_{resume_name}", application)

    def _handle_closed(self, application: JobApplication) -> None:
        logger.info("%s - %s: %s", application.company, application.title, self._CLOSED_REASON)
        self._tracker.record_unavailable(application, self._CLOSED_REASON)
        self._tally[_Tally.CLOSED] += 1

    def _handle_unavailable(self, application: JobApplication, job_id: str, reason: str) -> None:
        snapshot = self._browser.save_snapshot(f"ensaio-{job_id}")
        logger.warning("%s - %s: %s Página salva em %s.", application.company, application.title, reason, snapshot)
        self._tracker.record_unavailable(application, reason)
        self._count_failure(_Tally.UNAVAILABLE, snapshot)

    def _record(self, application: JobApplication, outcome: FillOutcome, evidence: RehearsalEvidence) -> None:
        match outcome.status:
            case FillStatus.READY_TO_SUBMIT:
                self._tracker.record_rehearsal_ready(application, f"Ensaio em {evidence.folder.name}")
                evidence.record_result("pronta para enviar (nada foi enviado)")
                self._count_success(_Tally.READY)
            case FillStatus.UNKNOWN_QUESTIONS:
                self._tracker.record_unknown_questions(application, outcome.questions)
                evidence.record_result("pendente, há pergunta sem resposta")
                self._count_success(_Tally.PENDING)
            case FillStatus.FAILED:
                self._tracker.record_failure(application, outcome.detail or "Falha no formulário.")
                evidence.record_result(f"erro: {outcome.detail}")
                self._count_failure(_Tally.FAILED, evidence.folder)
        logger.info("Resultado: %s (%s)", outcome.status.name, evidence.folder.name)

    def _count_success(self, tally: _Tally) -> None:
        self._tally[tally] += 1
        self._consecutive_failures = 0

    def _count_failure(self, tally: _Tally, evidence: Path) -> None:
        self._tally[tally] += 1
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures:
            raise _StopRehearsal(
                f"{self._consecutive_failures} vagas seguidas falharam; o layout do LinkedIn pode ter mudado. "
                f"Última evidência em {evidence}."
            )

    def _result(self, status: ScanStatus, reason: str) -> ScanResult:
        summary = ", ".join(f"{self._tally[tally]} {tally.value}" for tally in _Tally)
        return ScanResult(
            status=status,
            reason=f"{reason} Resultado: {summary}.",
            jobs_seen=self._tally.total(),
            jobs_recorded=self._tally[_Tally.READY],
        )

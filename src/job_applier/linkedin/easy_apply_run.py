import logging
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from job_applier.linkedin.easy_apply_filler import EasyApplyFiller, FillOutcome, FillStatus
from job_applier.linkedin.easy_apply_form import ApplicationForm, EasyApplyFormError, EasyApplyUnavailableError
from job_applier.linkedin.job_page_parser import JobPageParser
from job_applier.linkedin.job_scanner import ScanResult
from job_applier.linkedin.linkedin_browser import ApplicationBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.rehearsal_evidence import RehearsalEvidence
from job_applier.linkedin.run_stop import StopRun
from job_applier.linkedin.session_guard import SessionBlockedError, SessionGuard
from job_applier.matching.location_policy import LocationPolicy
from job_applier.models.job_application import JobApplication, ScanStatus
from job_applier.models.job_posting import JobPosting
from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from job_applier.storage.application_repository import ApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class EasyApplyRun(ABC):
    """Percorre a fila de vagas simplificadas: abre cada uma, preenche o formulário e registra o resultado.

    O que acontece na tela final (descartar no ensaio, enviar na candidatura real) fica com as subclasses.
    Perguntas sem resposta vão para a aba Perguntas e a vaga fica pendente. Para na hora ao primeiro sinal
    de captcha, logout ou bloqueio, ou quando várias vagas seguidas falharem (provável mudança de layout).
    Vaga encerrada é ignorada sem contar como falha: vagas antigas na fila encerram com frequência, e isso
    não diz nada sobre o layout.
    """

    PENDING = "com pergunta sem resposta"
    CLOSED = "encerradas"
    UNWANTED = "fora do local aceito"
    UNAVAILABLE = "indisponíveis"
    FAILED = "com erro"
    _CLOSED_REASON = "Vaga encerrada: não aceita mais candidaturas."
    _SNAPSHOT_PREFIX = "vaga"

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
        location_policy: LocationPolicy | None = None,
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
        self._location_policy = location_policy or LocationPolicy([])
        self._guard = SessionGuard()
        self._tally: Counter[str] = Counter()
        self._consecutive_failures = 0

    @property
    @abstractmethod
    def finished_label(self) -> str:
        """Como o resumo chama as vagas que chegaram ao fim ("prontas para envio", "enviadas")."""

    @abstractmethod
    def _jobs(self) -> list[JobApplication]:
        """A fila desta execução."""

    @abstractmethod
    def _finish(self, form: ApplicationForm, application: JobApplication, evidence: RehearsalEvidence) -> None:
        """O que fazer quando o formulário chegou à tela do botão de enviar."""

    @abstractmethod
    def _completion_message(self) -> str:
        """Motivo de término quando a fila inteira foi percorrida."""

    def _ensure_can_continue(self) -> None:
        """Chamado antes de cada vaga; lança StopRun para encerrar (por exemplo, um limite atingido)."""

    def run(self) -> ScanResult:
        try:
            self._ensure_can_continue()
            jobs = self._jobs()
            for position, application in enumerate(jobs, start=1):
                self._ensure_can_continue()
                self._process(application)
                if position < len(jobs):
                    self._pacer.after_job(position)
        except StopRun as stop:
            return self._result(stop.status, stop.reason)
        except SessionBlockedError as blocked:
            snapshot = self._browser.save_snapshot("bloqueio")
            return self._result(ScanStatus.STOPPED, f"{blocked.reason} Página salva em {snapshot}.")
        except Exception as error:
            logger.exception("Erro inesperado na execução.")
            return self._result(ScanStatus.STOPPED, f"Erro inesperado: {error!r}")
        return self._result(ScanStatus.COMPLETED, self._completion_message())

    def apply_to(self, application: JobApplication) -> None:
        """Uma vaga só, fora da fila: usado pela busca que se candidata logo depois de gerar o CV.

        StopRun e SessionBlockedError sobem para quem chamou, que encerra a execução.
        """
        self._ensure_can_continue()
        self._process(application)

    def summary(self) -> str:
        labels = (self.finished_label, self.PENDING, self.CLOSED, self.UNWANTED, self.UNAVAILABLE, self.FAILED)
        return ", ".join(f"{self._tally[label]} {label}" for label in labels)

    def _process(self, application: JobApplication) -> None:
        job_id = self._job_id(application)
        logger.info("Vaga: %s - %s", application.company, application.title)
        self._pacer.between_actions()
        page = self._browser.open_job(job_id)
        self._guard.check(page)
        if self._page_parser.is_closed(page.text):
            self._handle_closed(application)
            return
        workplace = self._page_parser.workplace(page.html, job_id)
        if reason := self._location_policy.skip_reason(workplace, application.title, application.location):
            self._handle_unwanted(application, reason)
            return
        try:
            form = self._browser.open_application_form()
        except EasyApplyUnavailableError as error:
            self._handle_unavailable(application, job_id, str(error))
            return

        evidence = self._evidence_for(application)
        outcome = self._filler.fill(form, application, self._resumes.load(application), evidence)
        if outcome.status is FillStatus.READY_TO_SUBMIT:
            self._finish(form, application, evidence)
            return
        if outcome.status is FillStatus.FAILED:
            self._browser.save_snapshot(f"{self._SNAPSHOT_PREFIX}-{job_id}")
        self._discard(form, job_id)
        self._record_unfinished(application, outcome, evidence)

    def _discard(self, form: ApplicationForm, job_id: str) -> None:
        """Fecha sem enviar. Se o modal não fechar, a vaga segue com o resultado que teve e a execução continua:
        abrir a próxima vaga sai desta página e descarta o formulário.
        """
        try:
            form.close_without_sending()
        except EasyApplyFormError as error:
            snapshot = self._browser.save_snapshot(f"{self._SNAPSHOT_PREFIX}-{job_id}-fechar")
            logger.warning("%s A execução segue. Página salva em %s.", error, snapshot)

    @staticmethod
    def _job_id(application: JobApplication) -> str:
        return JobPosting.id_from_url(application.url or "")

    def _evidence_for(self, application: JobApplication) -> RehearsalEvidence:
        resume_name = Path(application.resume_path or application.job_key).stem
        return RehearsalEvidence(self._evidence_dir / f"{self._now():%Y-%m-%d_%H-%M-%S}_{resume_name}", application)

    def _handle_closed(self, application: JobApplication) -> None:
        logger.info("%s - %s: %s", application.company, application.title, self._CLOSED_REASON)
        self._tracker.record_unavailable(application, self._CLOSED_REASON)
        self._tally[self.CLOSED] += 1

    def _handle_unwanted(self, application: JobApplication, reason: str) -> None:
        """Vagas da fila registradas antes da regra de local (ou cuja modalidade mudou) são conferidas aqui."""
        logger.info("%s - %s: ignorada (%s).", application.company, application.title, reason)
        self._tracker.record_unavailable(application, reason)
        self._tally[self.UNWANTED] += 1

    def _handle_unavailable(self, application: JobApplication, job_id: str, reason: str) -> None:
        snapshot = self._browser.save_snapshot(f"{self._SNAPSHOT_PREFIX}-{job_id}")
        logger.warning("%s - %s: %s Página salva em %s.", application.company, application.title, reason, snapshot)
        self._tracker.record_unavailable(application, reason)
        self._count_failure(self.UNAVAILABLE, snapshot)

    def _record_unfinished(self, application: JobApplication, outcome: FillOutcome, evidence: RehearsalEvidence) -> None:
        if outcome.status is FillStatus.UNKNOWN_QUESTIONS:
            self._tracker.record_unknown_questions(application, outcome.questions)
            evidence.record_result("pendente, há pergunta sem resposta")
            self._count_success(self.PENDING)
        else:
            self._tracker.record_failure(application, outcome.detail or "Falha no formulário.")
            evidence.record_result(f"erro: {outcome.detail}")
            self._count_failure(self.FAILED, evidence.folder)
        logger.info("Resultado: %s (%s)", outcome.status.name, evidence.folder.name)

    def _count_success(self, tally: str) -> None:
        self._tally[tally] += 1
        self._consecutive_failures = 0

    def _count_failure(self, tally: str, evidence: Path) -> None:
        self._tally[tally] += 1
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures:
            raise StopRun(
                f"{self._consecutive_failures} vagas seguidas falharam; o layout do LinkedIn pode ter mudado. "
                f"Última evidência em {evidence}."
            )

    def _result(self, status: ScanStatus, reason: str) -> ScanResult:
        return ScanResult(
            status=status,
            reason=f"{reason} Resultado: {self.summary()}.",
            jobs_seen=self._tally.total(),
            jobs_recorded=self._tally[self.finished_label],
        )

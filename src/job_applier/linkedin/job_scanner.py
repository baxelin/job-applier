import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from job_applier.linkedin.job_page_parser import JobExtractionError, JobPageParser
from job_applier.linkedin.linkedin_browser import JobBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.search_results_parser import SearchResultsParser
from job_applier.linkedin.search_url_builder import LinkedInSearchUrlBuilder
from job_applier.linkedin.session_guard import SessionBlockedError, SessionGuard
from job_applier.matching.word_filter import WordFilter
from job_applier.models.automation_settings import AutomationSettings, SearchQuery
from job_applier.models.job_application import ScanStatus
from job_applier.models.job_posting import ApplyType, JobPosting
from job_applier.resume.resume_generator import JobEvaluation, ResumeGenerator
from job_applier.storage.application_repository import ApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    reason: str
    jobs_seen: int
    jobs_recorded: int


class _StopScan(Exception):
    def __init__(self, status: ScanStatus, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


class JobScanner:
    """Percorre as buscas do config.json e registra cada vaga nova com análise e CV, sem se candidatar.

    Vagas de empresas bloqueadas, com título proibido, de suporte ou encerradas são registradas
    como ignoradas (sem CV), para não serem abertas de novo.

    Para na hora ao primeiro sinal de captcha, logout ou bloqueio, ao atingir o limite diário,
    ou quando várias páginas seguidas não forem reconhecidas (provável mudança de layout).
    """

    def __init__(
        self,
        browser: JobBrowser,
        settings: AutomationSettings,
        generator: ResumeGenerator,
        tracker: ApplicationTracker,
        applications: ApplicationRepository,
        pacer: Pacer,
        today: Callable[[], date] = date.today,
        max_jobs: int | None = None,
    ) -> None:
        self._browser = browser
        self._settings = settings
        self._generator = generator
        self._tracker = tracker
        self._applications = applications
        self._pacer = pacer
        self._today = today
        self._max_jobs = max_jobs
        self._url_builder = LinkedInSearchUrlBuilder(settings.filters)
        self._search_parser = SearchResultsParser()
        self._job_parser = JobPageParser()
        self._guard = SessionGuard()
        self._title_filter = WordFilter(settings.filters.forbidden_title_words)
        self._company_filter = WordFilter(settings.filters.blocked_companies)
        self._jobs_seen = 0
        self._jobs_recorded = 0
        self._resumes_left_today = 0
        self._consecutive_extraction_errors = 0

    def run(self) -> ScanResult:
        self._resumes_left_today = self._settings.daily_application_limit - self._applications.count_processed_on(
            self._today()
        )
        try:
            self._ensure_can_continue()
            for search in self._settings.searches:
                self._scan_search(search)
        except _StopScan as stop:
            return self._result(stop.status, stop.reason)
        except SessionBlockedError as blocked:
            snapshot = self._browser.save_snapshot("bloqueio")
            return self._result(ScanStatus.STOPPED, f"{blocked.reason} Página salva em {snapshot}.")
        return self._result(ScanStatus.COMPLETED, "Todas as buscas foram percorridas.")

    def _scan_search(self, search: SearchQuery) -> None:
        logger.info("Busca: %s (%s)", search.keywords, search.location)
        for page in range(self._settings.scan.max_pages_per_search):
            self._pacer.between_actions()
            snapshot = self._browser.open_search(self._url_builder.build(search, page))
            self._guard.check(snapshot)
            job_ids = self._search_parser.job_ids(snapshot.html)
            if not job_ids:
                return
            for job_id in job_ids:
                if not self._applications.exists(JobPosting.url_for(job_id)):
                    self._scan_job(job_id)

    def _scan_job(self, job_id: str) -> None:
        self._ensure_can_continue()
        self._pacer.between_actions()
        snapshot = self._browser.open_job(job_id)
        self._guard.check(snapshot)
        try:
            posting = self._job_parser.parse(snapshot.html, job_id, self._today())
        except JobExtractionError as error:
            self._handle_extraction_error(error)
            return

        self._consecutive_extraction_errors = 0
        self._jobs_seen += 1
        self._record(posting)
        self._pacer.after_job(self._jobs_seen)

    def _record(self, posting: JobPosting) -> None:
        evaluation = self._generator.evaluate(posting.description)
        if reason := self._skip_reason(posting, evaluation):
            self._tracker.record_skipped(evaluation, posting, reason)
            logger.info("Ignorada: %s - %s (%s)", posting.description.company, posting.description.title, reason)
        else:
            self._tracker.record(self._generator.generate_for(evaluation), posting)
            self._resumes_left_today -= 1
            logger.info(
                "CV gerado: %s - %s (aderência %d%%)",
                posting.description.company,
                posting.description.title,
                evaluation.fit.percentage,
            )
        self._jobs_recorded += 1

    def _skip_reason(self, posting: JobPosting, evaluation: JobEvaluation) -> str | None:
        if company := self._company_filter.first_match_in(posting.description.company):
            return f"Empresa bloqueada ({company})"
        if word := self._title_filter.first_match_in(posting.description.title):
            return f"Título contém '{word}'"
        if evaluation.analysis.is_support_role:
            return "Vaga de suporte"
        if posting.apply_type is ApplyType.CLOSED:
            return "Vaga não aceita mais candidaturas"
        return None

    def _ensure_can_continue(self) -> None:
        if self._resumes_left_today <= 0:
            raise _StopScan(ScanStatus.COMPLETED, "Limite diário de vagas atingido.")
        if self._max_jobs is not None and self._jobs_seen >= self._max_jobs:
            raise _StopScan(ScanStatus.COMPLETED, f"Limite desta execução atingido ({self._max_jobs} vagas).")

    def _handle_extraction_error(self, error: JobExtractionError) -> None:
        snapshot = self._browser.save_snapshot(f"vaga-{error.linkedin_id}")
        self._consecutive_extraction_errors += 1
        logger.warning("%s Página salva em %s.", error, snapshot)
        if self._consecutive_extraction_errors >= self._settings.scan.max_consecutive_extraction_errors:
            raise _StopScan(
                ScanStatus.STOPPED,
                f"{self._consecutive_extraction_errors} páginas de vaga seguidas não foram reconhecidas; "
                f"o layout do LinkedIn pode ter mudado. Última página salva em {snapshot}.",
            )

    def _result(self, status: ScanStatus, reason: str) -> ScanResult:
        return ScanResult(status=status, reason=reason, jobs_seen=self._jobs_seen, jobs_recorded=self._jobs_recorded)

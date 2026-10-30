from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from job_applier.models.job_application import ApplicationStatus, JobApplication
from job_applier.models.job_posting import JobPosting
from job_applier.resume.resume_generator import GeneratedResume, JobEvaluation
from job_applier.storage.application_repository import ApplicationRepository
from job_applier.storage.excel_report_writer import ExcelReportWriter
from job_applier.storage.scan_run_repository import ScanRunRepository
from job_applier.storage.unknown_question_repository import UnknownQuestionRepository


class ApplicationTracker:
    """Registra no banco cada vaga processada e mantém a planilha de acompanhamento em dia."""

    _RECENT_RUNS_IN_REPORT = 100

    def __init__(
        self,
        applications: ApplicationRepository,
        questions: UnknownQuestionRepository,
        runs: ScanRunRepository,
        report: ExcelReportWriter,
        project_root: Path,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._applications = applications
        self._questions = questions
        self._runs = runs
        self._report = report
        self._project_root = project_root
        self._now = now

    def record(self, generated: GeneratedResume, posting: JobPosting | None = None) -> JobApplication:
        return self._save(
            generated.evaluation,
            posting,
            resume_path=self._relative_to_project(generated.path),
            status=ApplicationStatus.CV_GENERATED,
        )

    def record_skipped(self, evaluation: JobEvaluation, posting: JobPosting | None, reason: str) -> JobApplication:
        return self._save(evaluation, posting, resume_path=None, status=ApplicationStatus.SKIPPED, notes=reason)

    def refresh_report(self) -> None:
        """Recria a planilha; lança SpreadsheetLockedError se ela estiver aberta no Excel."""
        self._report.write(
            self._applications.list_all(),
            self._questions.list_all(),
            self._runs.list_recent(self._RECENT_RUNS_IN_REPORT),
        )

    def _save(
        self,
        evaluation: JobEvaluation,
        posting: JobPosting | None,
        resume_path: str | None,
        status: ApplicationStatus,
        notes: str | None = None,
    ) -> JobApplication:
        moment = self._now().replace(microsecond=0)
        job = evaluation.job
        return self._applications.save(
            JobApplication(
                job_key=job.key(),
                company=job.company,
                title=job.title,
                location=job.location,
                url=str(job.url) if job.url else None,
                description=job.text,
                locale=evaluation.analysis.locale,
                focus=" + ".join(sorted(evaluation.analysis.focus)),
                is_support_role=evaluation.analysis.is_support_role,
                fit_percentage=evaluation.fit.percentage,
                matched_terms=evaluation.fit.matched_terms,
                missing_terms=evaluation.fit.missing_terms,
                resume_path=resume_path,
                apply_type=posting.apply_type if posting else None,
                applicants=posting.applicants if posting else None,
                posted_on=posting.posted_on if posting else None,
                status=status,
                notes=notes,
                created_at=moment,
                updated_at=moment,
            )
        )

    def _relative_to_project(self, path: Path) -> str:
        """Caminho relativo à raiz do projeto, válido tanto no Docker quanto no Windows."""
        return path.resolve().relative_to(self._project_root.resolve()).as_posix()

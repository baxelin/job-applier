from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from job_applier.models.job_application import JobApplication
from job_applier.resume.resume_generator import GeneratedResume
from job_applier.storage.application_repository import ApplicationRepository
from job_applier.storage.excel_report_writer import ExcelReportWriter
from job_applier.storage.unknown_question_repository import UnknownQuestionRepository


class ApplicationTracker:
    """Registra no banco cada CV gerado e mantém a planilha de acompanhamento em dia."""

    def __init__(
        self,
        applications: ApplicationRepository,
        questions: UnknownQuestionRepository,
        report: ExcelReportWriter,
        project_root: Path,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._applications = applications
        self._questions = questions
        self._report = report
        self._project_root = project_root
        self._now = now

    def record(self, generated: GeneratedResume) -> JobApplication:
        moment = self._now().replace(microsecond=0)
        return self._applications.save(
            JobApplication(
                job_key=generated.job.key(),
                company=generated.job.company,
                title=generated.job.title,
                location=generated.job.location,
                url=str(generated.job.url) if generated.job.url else None,
                locale=generated.analysis.locale,
                focus=" + ".join(sorted(generated.analysis.focus)),
                is_support_role=generated.analysis.is_support_role,
                fit_percentage=generated.fit.percentage,
                matched_terms=generated.fit.matched_terms,
                missing_terms=generated.fit.missing_terms,
                resume_path=self._relative_to_project(generated.path),
                created_at=moment,
                updated_at=moment,
            )
        )

    def refresh_report(self) -> None:
        """Recria a planilha; lança SpreadsheetLockedError se ela estiver aberta no Excel."""
        self._report.write(self._applications.list_all(), self._questions.list_all())

    def _relative_to_project(self, path: Path) -> str:
        """Caminho relativo à raiz do projeto, válido tanto no Docker quanto no Windows."""
        return path.resolve().relative_to(self._project_root.resolve()).as_posix()

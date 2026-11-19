from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from job_applier.models.job_application import ApplicationStatus, JobApplication
from job_applier.models.job_posting import ApplyType, JobPosting
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
            status=self._status_with_resume(posting),
        )

    def record_skipped(self, evaluation: JobEvaluation, posting: JobPosting | None, reason: str) -> JobApplication:
        return self._save(evaluation, posting, resume_path=None, status=ApplicationStatus.SKIPPED, notes=reason)

    def record_rehearsal_ready(self, application: JobApplication, notes: str) -> None:
        self._update_status(application, ApplicationStatus.REHEARSED, notes)

    def record_unknown_questions(self, application: JobApplication, questions: Sequence[str]) -> None:
        """Guarda as perguntas para o usuário responder e deixa a vaga pendente até lá.

        Perguntas e vaga levam o mesmo instante: assim o resumo do dia sabe quais perguntas são da última
        tentativa (as de tentativas anteriores podem já ter sido respondidas por regras novas).
        """
        moment = self._moment()
        for question in questions:
            self._questions.register(question, application.id, moment)
        self._applications.update_status(
            application.job_key,
            ApplicationStatus.UNKNOWN_QUESTION_PENDING,
            f"Sem resposta para: {' | '.join(questions)}",
            moment,
        )

    def record_unavailable(self, application: JobApplication, reason: str) -> None:
        self._update_status(application, ApplicationStatus.SKIPPED, reason)

    def record_applied(self, application: JobApplication, notes: str) -> None:
        self._applications.mark_applied(application.job_key, notes, self._moment())

    def record_failure(self, application: JobApplication, reason: str) -> None:
        self._update_status(application, ApplicationStatus.FAILED, reason)

    def refresh_report(self) -> None:
        """Recria a planilha; lança SpreadsheetLockedError se ela estiver aberta no Excel."""
        self._report.write(
            self._applications.list_all(),
            self._questions.list_all(),
            self._runs.list_recent(self._RECENT_RUNS_IN_REPORT),
        )

    @staticmethod
    def _status_with_resume(posting: JobPosting | None) -> ApplicationStatus:
        if posting and posting.apply_type is ApplyType.EXTERNAL:
            return ApplicationStatus.MANUAL_APPLICATION_PENDING
        return ApplicationStatus.CV_GENERATED

    def _save(
        self,
        evaluation: JobEvaluation,
        posting: JobPosting | None,
        resume_path: str | None,
        status: ApplicationStatus,
        notes: str | None = None,
    ) -> JobApplication:
        moment = self._moment()
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
                external_apply_url=posting.external_apply_url if posting else None,
                applicants=posting.applicants if posting else None,
                posted_on=posting.posted_on if posting else None,
                status=status,
                notes=notes,
                created_at=moment,
                updated_at=moment,
            )
        )

    def _update_status(self, application: JobApplication, status: ApplicationStatus, notes: str) -> None:
        self._applications.update_status(application.job_key, status, notes, self._moment())

    def _moment(self) -> datetime:
        return self._now().replace(microsecond=0)

    def _relative_to_project(self, path: Path) -> str:
        """Caminho relativo à raiz do projeto, válido tanto no Docker quanto no Windows."""
        return path.resolve().relative_to(self._project_root.resolve()).as_posix()

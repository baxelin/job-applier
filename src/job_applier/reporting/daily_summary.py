from dataclasses import dataclass
from datetime import date

from job_applier.models.job_application import ApplicationStatus, JobApplication, UnknownQuestion
from job_applier.storage.application_repository import ApplicationRepository
from job_applier.storage.unknown_question_repository import UnknownQuestionRepository


@dataclass(frozen=True)
class DailySummary:
    """O que aconteceu num dia e o que está esperando pelo usuário (este último, de todos os dias)."""

    day: date
    sent: tuple[JobApplication, ...]
    seen: int
    skipped: int
    ready_to_send: int
    manual_pending: int
    question_pending: int
    failed: tuple[JobApplication, ...]
    open_questions: tuple[UnknownQuestion, ...]

    @property
    def with_resume(self) -> int:
        return self.seen - self.skipped


class DailySummaryBuilder:
    """Monta o resumo do dia a partir do banco: enviadas, vagas novas, pendências e perguntas que travam vagas."""

    def __init__(self, applications: ApplicationRepository, questions: UnknownQuestionRepository) -> None:
        self._applications = applications
        self._questions = questions

    def build(self, day: date) -> DailySummary:
        records = self._applications.list_all()
        seen_today = [item for item in records if item.created_at.date() == day]
        return DailySummary(
            day=day,
            sent=tuple(item for item in records if item.applied_at and item.applied_at.date() == day),
            seen=len(seen_today),
            skipped=sum(item.status is ApplicationStatus.SKIPPED for item in seen_today),
            ready_to_send=len(self._applications.list_ready_for_submission()),
            manual_pending=self._count(records, ApplicationStatus.MANUAL_APPLICATION_PENDING),
            question_pending=self._count(records, ApplicationStatus.UNKNOWN_QUESTION_PENDING),
            failed=tuple(item for item in records if item.status is ApplicationStatus.FAILED),
            open_questions=tuple(question for question in self._questions.list_all() if question.blocks_a_job),
        )

    @staticmethod
    def _count(records: list[JobApplication], status: ApplicationStatus) -> int:
        return sum(item.status is status for item in records)

from datetime import date, datetime

import pytest

from job_applier.models.job_application import ApplicationStatus
from job_applier.reporting.daily_report_text import DailyReportText
from job_applier.reporting.daily_summary import DailySummaryBuilder
from tests.factories import tracker_for
from tests.storage.conftest import application

DAY = date(2026, 11, 19)
TODAY = datetime(2026, 11, 19, 10, 0)
YESTERDAY = datetime(2026, 11, 18, 10, 0)


def save(applications, job_id: str, created_at: datetime = TODAY, **changes):
    url = f"https://www.linkedin.com/jobs/view/{job_id}/"
    return applications.save(
        application(
            job_key=url,
            url=url,
            company=f"Empresa {job_id}",
            apply_type="candidatura_simplificada",
            created_at=created_at,
            updated_at=created_at,
            **changes,
        )
    )


@pytest.fixture
def builder(applications, questions) -> DailySummaryBuilder:
    return DailySummaryBuilder(applications, questions)


class TestDailySummaryBuilder:
    def test_counts_what_happened_on_the_day(self, builder, applications):
        save(applications, "1", status=ApplicationStatus.APPLIED, applied_at=TODAY)
        save(applications, "2", status=ApplicationStatus.SKIPPED, resume_path=None)
        save(applications, "3")
        save(applications, "4", created_at=YESTERDAY, status=ApplicationStatus.APPLIED, applied_at=YESTERDAY)

        summary = builder.build(DAY)

        assert [item.company for item in summary.sent] == ["Empresa 1"]
        assert (summary.seen, summary.with_resume, summary.skipped) == (3, 2, 1)

    def test_pending_work_comes_from_every_day(self, builder, applications):
        save(applications, "1", created_at=YESTERDAY)
        save(applications, "2", created_at=YESTERDAY, status=ApplicationStatus.MANUAL_APPLICATION_PENDING)
        save(applications, "3", created_at=YESTERDAY, status=ApplicationStatus.UNKNOWN_QUESTION_PENDING)
        save(applications, "4", created_at=YESTERDAY, status=ApplicationStatus.FAILED)

        summary = builder.build(DAY)

        assert (summary.ready_to_send, summary.manual_pending, summary.question_pending) == (1, 1, 1)
        assert [item.company for item in summary.failed] == ["Empresa 4"]

    def test_lists_only_the_questions_that_still_block_a_job(self, builder, applications, questions):
        pending = save(applications, "1", status=ApplicationStatus.UNKNOWN_QUESTION_PENDING)
        sent = save(applications, "2", status=ApplicationStatus.APPLIED, applied_at=TODAY)
        questions.register("Ainda trava", pending.id, TODAY)
        questions.register("Já resolvida por uma regra", sent.id, TODAY)

        assert [question.question for question in builder.build(DAY).open_questions] == ["Ainda trava"]

    def test_questions_answered_in_the_latest_attempt_are_not_listed(self, builder, applications, questions, tmp_path):
        job = save(applications, "1")
        tracker = tracker_for(tmp_path, now=lambda: YESTERDAY)
        tracker.record_unknown_questions(job, ["Respondida depois por uma regra", "Ainda sem resposta"])
        tracker_for(tmp_path, now=lambda: TODAY).record_unknown_questions(job, ["Ainda sem resposta"])

        assert [question.question for question in builder.build(DAY).open_questions] == ["Ainda sem resposta"]


class TestDailyReportText:
    def test_shows_sent_jobs_pending_work_and_blocking_questions(self, builder, applications, questions):
        save(applications, "1", status=ApplicationStatus.APPLIED, applied_at=TODAY, title="Dev Python")
        save(applications, "2", status=ApplicationStatus.FAILED, title="Dev Java")
        pending = save(applications, "3", status=ApplicationStatus.UNKNOWN_QUESTION_PENDING)
        questions.register("Você tem CNH?", pending.id, YESTERDAY)
        questions.register("Você tem CNH?", pending.id, TODAY)
        questions.register("Por que nós?", pending.id, TODAY)

        text = DailyReportText().render(builder.build(DAY))

        assert "Resumo de 19/11/2026" in text
        assert "Enviadas: 1\n  - Empresa 1: Dev Python" in text
        assert "Vagas novas: 3 (3 com CV, 0 ignoradas)" in text
        assert "1 com erro" in text and "Empresa 2: Dev Java" in text
        assert "1 pendentes de pergunta" in text
        assert '"Você tem CNH?" (2x, última: Empresa 3)\n' in text
        assert '"Por que nós?" (1x, última: Empresa 3) [nova]' in text
        assert "para aplicar no site da empresa" not in text

    def test_says_when_nothing_is_waiting(self, builder):
        text = DailyReportText().render(builder.build(DAY))

        assert "Enviadas: 0" in text
        assert "Nada esperando por você." in text
        assert "Perguntas" not in text

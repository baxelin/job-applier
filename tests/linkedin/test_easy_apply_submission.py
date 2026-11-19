from datetime import date, datetime

import pytest

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.linkedin.easy_apply_filler import EasyApplyFiller
from job_applier.linkedin.easy_apply_submission import EasyApplySubmission
from job_applier.linkedin.linkedin_browser import ApplicationBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.matching.location_policy import LocationPolicy
from job_applier.models.job_application import ApplicationStatus, ScanStatus
from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from tests.factories import tracker_for
from tests.linkedin.fake_application_form import FakeApplicationForm
from tests.linkedin.test_easy_apply_rehearsal import (  # noqa: F401 (fixtures)
    NOW,
    REVIEW,
    UNKNOWN_QUESTION,
    FakeApplicationBrowser,
    applications,
    job_key,
    save_job,
    status_of,
)

TODAY = date(2026, 10, 30)


@pytest.fixture
def make_submission(example_base_data, applications, tmp_path):  # noqa: F811
    def build(
        browser: ApplicationBrowser,
        daily_limit: int | None = 5,
        max_failures: int = 3,
        location_policy: LocationPolicy | None = None,
    ) -> EasyApplySubmission:
        data = example_base_data
        pacer = Pacer(data.settings, sleep=lambda seconds: None)
        return EasyApplySubmission(
            browser,
            EasyApplyFiller(FormAnswerer(data.answer_book, data.resume, data.glossary), pacer),
            ResumeUploadFileLoader(tmp_path, data.resume.contact),
            tracker_for(tmp_path),
            applications,
            pacer,
            tmp_path / "data" / "envios",
            max_failures,
            now=lambda: NOW,
            daily_limit=daily_limit,
            today=lambda: TODAY,
            location_policy=location_policy,
        )

    return build


def recorded(applications, job_id: str):  # noqa: F811
    return next(item for item in applications.list_all() if item.job_key == job_key(job_id))


class TestEasyApplySubmission:
    def test_sends_the_application_and_records_when_it_was_sent(
        self, make_submission, save_job, applications, tmp_path  # noqa: F811
    ):
        save_job("1")
        form = FakeApplicationForm([REVIEW])

        result = make_submission(FakeApplicationBrowser({"1": form})).run()

        job = recorded(applications, "1")
        assert form.submitted and form.closed_after_sending and not form.closed
        assert job.status is ApplicationStatus.APPLIED
        assert job.applied_at is not None
        assert (result.status, result.jobs_recorded) == (ScanStatus.COMPLETED, 1)
        assert "1 enviadas" in result.reason
        [evidence] = (tmp_path / "data" / "envios").iterdir()
        assert "Resultado: candidatura enviada" in (evidence / "respostas.txt").read_text(encoding="utf-8")

    def test_rehearsed_jobs_go_first(self, make_submission, save_job, applications):  # noqa: F811
        save_job("1", fit=90)
        save_job("2", fit=10)
        applications.update_status(job_key("2"), ApplicationStatus.REHEARSED, "Ensaio ok", NOW)
        browser = FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW]), "2": FakeApplicationForm([REVIEW])})

        make_submission(browser).run()

        assert browser.opened_jobs == ["2", "1"]

    def test_stops_at_the_daily_limit(self, make_submission, save_job):  # noqa: F811
        save_job("1", fit=90)
        save_job("2", fit=80)
        browser = FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW]), "2": FakeApplicationForm([REVIEW])})

        result = make_submission(browser, daily_limit=1).run()

        assert browser.opened_jobs == ["1"]
        assert result.status is ScanStatus.COMPLETED
        assert "Limite diário de envios atingido (1)" in result.reason

    def test_without_a_daily_limit_sends_the_whole_queue(self, make_submission, save_job, applications):  # noqa: F811
        for job_id in ("1", "2", "3"):
            save_job(job_id)
        applications.mark_applied(job_key("3"), "Enviada", datetime(2026, 10, 30, 9, 0))
        browser = FakeApplicationBrowser({job_id: FakeApplicationForm([REVIEW]) for job_id in ("1", "2")})

        result = make_submission(browser, daily_limit=None).run()

        assert sorted(browser.opened_jobs) == ["1", "2"]
        assert "2 enviadas" in result.reason

    def test_daily_limit_counts_what_was_sent_earlier_today(
        self, make_submission, save_job, applications  # noqa: F811
    ):
        save_job("1")
        save_job("2")
        applications.mark_applied(job_key("1"), "Enviada", datetime(2026, 10, 30, 9, 0))
        browser = FakeApplicationBrowser({"2": FakeApplicationForm([REVIEW])})

        make_submission(browser, daily_limit=1).run()

        assert browser.opened_jobs == []

    def test_unknown_question_is_not_sent(self, make_submission, save_job, applications):  # noqa: F811
        save_job("1")
        form = FakeApplicationForm([UNKNOWN_QUESTION])

        make_submission(FakeApplicationBrowser({"1": form})).run()

        assert not form.submitted and form.closed
        assert status_of(applications, "1") is ApplicationStatus.UNKNOWN_QUESTION_PENDING

    def test_unconfirmed_submission_stops_everything_for_a_manual_check(
        self, make_submission, save_job, applications  # noqa: F811
    ):
        save_job("1", fit=90)
        save_job("2", fit=80)
        browser = FakeApplicationBrowser(
            {"1": FakeApplicationForm([REVIEW], submission="unconfirmed"), "2": FakeApplicationForm([REVIEW])}
        )

        result = make_submission(browser).run()

        assert result.status is ScanStatus.STOPPED
        assert "não mostrou a confirmação" in result.reason
        assert browser.opened_jobs == ["1"]
        assert browser.snapshots == ["envio-1"]
        assert status_of(applications, "1") is ApplicationStatus.FAILED

    def test_failed_click_discards_the_form_and_goes_on(self, make_submission, save_job, applications):  # noqa: F811
        save_job("1", fit=90)
        save_job("2", fit=80)
        failing = FakeApplicationForm([REVIEW], submission="error")
        browser = FakeApplicationBrowser({"1": failing, "2": FakeApplicationForm([REVIEW])})

        make_submission(browser).run()

        assert failing.closed and not failing.submitted
        assert status_of(applications, "1") is ApplicationStatus.FAILED
        assert status_of(applications, "2") is ApplicationStatus.APPLIED

    def test_queued_job_outside_the_accepted_cities_is_skipped_unless_remote(
        self, make_submission, save_job, applications  # noqa: F811
    ):
        save_job("1", location="Rio de Janeiro e Região")
        form = FakeApplicationForm([REVIEW])

        result = make_submission(
            FakeApplicationBrowser({"1": form}), location_policy=LocationPolicy(["São Paulo"])
        ).run()

        assert not form.submitted
        assert status_of(applications, "1") is ApplicationStatus.SKIPPED
        assert "1 fora do local aceito" in result.reason

    def test_already_sent_jobs_are_not_opened_again(self, make_submission, save_job):  # noqa: F811
        save_job("1")
        make_submission(FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW])})).run()
        browser = FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW])})

        make_submission(browser).run()

        assert browser.opened_jobs == []

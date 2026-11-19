import pytest

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.linkedin.easy_apply_filler import EasyApplyFiller
from job_applier.linkedin.easy_apply_form import ApplicationForm
from job_applier.linkedin.easy_apply_submission import EasyApplySubmission
from job_applier.linkedin.job_scanner import JobScanner
from job_applier.linkedin.linkedin_browser import ApplicationBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.linkedin.search_and_apply import SearchAndApply
from job_applier.models.job_application import ApplicationStatus, ScanStatus
from job_applier.models.job_posting import JobPosting
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from job_applier.storage.application_repository import SqliteApplicationRepository
from tests.factories import database_for, tracker_for
from tests.linkedin.fake_application_form import FakeApplicationForm
from tests.linkedin.pages import current_job_page
from tests.linkedin.test_easy_apply_rehearsal import NOW, REVIEW, UNKNOWN_QUESTION
from tests.linkedin.test_job_scanner import TODAY, FakeBrowser, FakePdfExporter, dev_job


class SearchAndApplyBrowser(FakeBrowser, ApplicationBrowser):
    """Busca, páginas de vaga e formulários no mesmo navegador, como no LinkedIn."""

    def __init__(self, search_pages, job_pages, forms: dict[str, ApplicationForm]) -> None:
        super().__init__(search_pages, job_pages)
        self._forms = forms
        self._current = ""

    def open_job(self, linkedin_id: str) -> PageSnapshot:
        self._current = linkedin_id
        return super().open_job(linkedin_id)

    def open_application_form(self) -> ApplicationForm:
        return self._forms[self._current]


@pytest.fixture
def applications(tmp_path) -> SqliteApplicationRepository:
    return SqliteApplicationRepository(database_for(tmp_path))


@pytest.fixture
def make_run(example_base_data, applications, tmp_path):
    def build(browser: SearchAndApplyBrowser) -> SearchAndApply:
        data = example_base_data
        settings = data.settings.model_copy(update={"searches": data.settings.searches[:1]})
        pacer = Pacer(settings, sleep=lambda seconds: None)
        tracker = tracker_for(tmp_path)
        submission = EasyApplySubmission(
            browser,
            EasyApplyFiller(FormAnswerer(data.answer_book, data.resume, data.glossary), pacer),
            ResumeUploadFileLoader(tmp_path, data.resume.contact),
            tracker,
            applications,
            pacer,
            tmp_path / "data" / "envios",
            3,
            now=lambda: NOW,
        )
        generator = ResumeGenerator(
            data, ResumeArchive(tmp_path / "data" / "cvs"), exporter=FakePdfExporter(), today=lambda: TODAY
        )
        scanner = JobScanner(
            browser,
            settings,
            generator,
            tracker,
            applications,
            pacer,
            today=lambda: TODAY,
            on_easy_apply_resume=submission.apply_to,
        )
        return SearchAndApply(scanner, submission)

    return build


def status_of(applications, job_id: str) -> ApplicationStatus:
    return next(item.status for item in applications.list_all() if item.url == JobPosting.url_for(job_id))


class TestSearchAndApply:
    def test_applies_right_after_generating_the_resume(self, make_run, applications):
        form = FakeApplicationForm([REVIEW])
        browser = SearchAndApplyBrowser(
            [["1", "2"]],
            {"1": dev_job(), "2": dev_job("Desenvolvedor Vue Júnior")},
            {"1": form, "2": FakeApplicationForm([REVIEW])},
        )

        result = make_run(browser).run()

        assert browser.opened_jobs == ["1", "1", "2", "2"]
        assert form.submitted
        assert status_of(applications, "1") is ApplicationStatus.APPLIED
        assert result.status is ScanStatus.COMPLETED
        assert "Candidaturas: 2 enviadas" in result.reason

    def test_external_and_skipped_jobs_are_only_recorded(self, make_run, applications):
        external = current_job_page(job_id="2", apply_href="https://empresa.example/vaga-2")
        browser = SearchAndApplyBrowser([["1", "2"]], {"1": dev_job("Desenvolvedor Python Sênior"), "2": external}, {})

        make_run(browser).run()

        assert browser.opened_jobs == ["1", "2"]
        assert status_of(applications, "1") is ApplicationStatus.SKIPPED
        assert status_of(applications, "2") is ApplicationStatus.MANUAL_APPLICATION_PENDING

    def test_unknown_question_leaves_the_job_pending_and_the_search_goes_on(self, make_run, applications):
        browser = SearchAndApplyBrowser(
            [["1", "2"]],
            {"1": dev_job(), "2": dev_job("Desenvolvedor Vue Júnior")},
            {"1": FakeApplicationForm([UNKNOWN_QUESTION]), "2": FakeApplicationForm([REVIEW])},
        )

        result = make_run(browser).run()

        assert status_of(applications, "1") is ApplicationStatus.UNKNOWN_QUESTION_PENDING
        assert status_of(applications, "2") is ApplicationStatus.APPLIED
        assert "1 enviadas, 1 com pergunta sem resposta" in result.reason

    def test_unconfirmed_submission_stops_the_search(self, make_run, applications):
        browser = SearchAndApplyBrowser(
            [["1", "2"]],
            {"1": dev_job(), "2": dev_job("Desenvolvedor Vue Júnior")},
            {"1": FakeApplicationForm([REVIEW], submission="unconfirmed"), "2": FakeApplicationForm([REVIEW])},
        )

        result = make_run(browser).run()

        assert browser.opened_jobs == ["1", "1"]
        assert result.status is ScanStatus.STOPPED
        assert "não mostrou a confirmação" in result.reason
        assert status_of(applications, "1") is ApplicationStatus.FAILED

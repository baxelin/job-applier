from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import load_workbook

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.linkedin.easy_apply_filler import EasyApplyFiller
from job_applier.linkedin.easy_apply_form import ApplicationForm, EasyApplyUnavailableError
from job_applier.linkedin.easy_apply_rehearsal import EasyApplyRehearsal
from job_applier.linkedin.linkedin_browser import ApplicationBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.models.job_application import ApplicationStatus, ScanStatus
from job_applier.models.job_posting import JobPosting
from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from job_applier.storage.application_repository import SqliteApplicationRepository
from tests.factories import database_for, tracker_for
from tests.linkedin.easy_apply_pages import modal, question_input
from tests.linkedin.fake_application_form import FakeApplicationForm
from tests.storage.conftest import application

NOW = datetime(2026, 10, 30, 18, 0, 5)
REVIEW = modal("<p>Revise</p>", buttons=("Enviar candidatura",))
UNKNOWN_QUESTION = modal(question_input("Por que nós?"))


def job_key(job_id: str) -> str:
    return JobPosting.url_for(job_id)


class FakeApplicationBrowser(ApplicationBrowser):
    def __init__(self, forms: dict[str, ApplicationForm | Exception], job_url: str | None = None) -> None:
        self._forms = forms
        self._job_url = job_url
        self._current = ""
        self.opened_jobs: list[str] = []
        self.snapshots: list[str] = []

    def open_job(self, linkedin_id: str) -> PageSnapshot:
        self._current = linkedin_id
        self.opened_jobs.append(linkedin_id)
        return PageSnapshot(url=self._job_url or JobPosting.url_for(linkedin_id), html="", text="Vaga " * 1000)

    def open_application_form(self) -> ApplicationForm:
        form = self._forms[self._current]
        if isinstance(form, Exception):
            raise form
        return form

    def save_snapshot(self, name: str) -> Path:
        self.snapshots.append(name)
        return Path(f"data/debug/{name}.html")


@pytest.fixture
def applications(tmp_path) -> SqliteApplicationRepository:
    return SqliteApplicationRepository(database_for(tmp_path))


@pytest.fixture
def save_job(applications, tmp_path):
    def save(job_id: str, fit: int = 80) -> None:
        resume = tmp_path / "data" / "cvs" / f"cv-{job_id}.pdf"
        resume.parent.mkdir(parents=True, exist_ok=True)
        resume.write_bytes(b"%PDF-fake")
        applications.save(
            application(
                job_key=job_key(job_id),
                url=job_key(job_id),
                apply_type="candidatura_simplificada",
                fit_percentage=fit,
                resume_path=f"data/cvs/cv-{job_id}.pdf",
            )
        )

    return save


@pytest.fixture
def make_rehearsal(example_base_data, applications, tmp_path):
    def build(browser: ApplicationBrowser, max_jobs: int | None = None, max_failures: int = 3) -> EasyApplyRehearsal:
        data = example_base_data
        pacer = Pacer(data.settings, sleep=lambda seconds: None)
        return EasyApplyRehearsal(
            browser,
            EasyApplyFiller(FormAnswerer(data.answer_book, data.resume, data.glossary), pacer),
            ResumeUploadFileLoader(tmp_path, data.resume.contact),
            tracker_for(tmp_path),
            applications,
            pacer,
            tmp_path / "data" / "ensaios",
            max_failures,
            max_jobs=max_jobs,
            now=lambda: NOW,
        )

    return build


def status_of(applications, job_id: str) -> ApplicationStatus:
    return next(item for item in applications.list_all() if item.job_key == job_key(job_id)).status


class TestEasyApplyRehearsal:
    def test_completed_form_is_marked_as_rehearsed_and_discarded(self, make_rehearsal, save_job, applications):
        save_job("1")
        form = FakeApplicationForm([REVIEW])

        result = make_rehearsal(FakeApplicationBrowser({"1": form})).run()

        assert result.status is ScanStatus.COMPLETED
        assert "nada foi enviado" in result.reason
        assert form.closed
        assert status_of(applications, "1") is ApplicationStatus.REHEARSED

    def test_unknown_question_leaves_the_job_pending_and_is_saved(
        self, make_rehearsal, save_job, applications, tmp_path
    ):
        save_job("1")
        form = FakeApplicationForm([UNKNOWN_QUESTION, REVIEW])

        make_rehearsal(FakeApplicationBrowser({"1": form})).run()
        tracker_for(tmp_path).refresh_report()

        assert form.closed
        assert status_of(applications, "1") is ApplicationStatus.UNKNOWN_QUESTION_PENDING
        questions = load_workbook(tmp_path / "data" / "candidaturas.xlsx")["Perguntas"]
        assert questions["A2"].value == "Por que nós?"

    def test_failure_keeps_the_page_for_diagnosis_and_goes_on(self, make_rehearsal, save_job, applications):
        save_job("1", fit=90)
        save_job("2", fit=80)
        browser = FakeApplicationBrowser(
            {"1": FakeApplicationForm([modal("", buttons=("Outro botão",))]), "2": FakeApplicationForm([REVIEW])}
        )

        result = make_rehearsal(browser).run()

        assert browser.snapshots == ["ensaio-1"]
        assert status_of(applications, "1") is ApplicationStatus.FAILED
        assert status_of(applications, "2") is ApplicationStatus.REHEARSED
        assert "1 prontas para envio" in result.reason
        assert "1 com erro" in result.reason

    def test_unavailable_job_is_skipped(self, make_rehearsal, save_job, applications):
        save_job("1")
        browser = FakeApplicationBrowser({"1": EasyApplyUnavailableError("Sem botão.")})

        make_rehearsal(browser).run()

        assert status_of(applications, "1") is ApplicationStatus.SKIPPED
        assert browser.snapshots == ["ensaio-1"]

    def test_stops_after_consecutive_failures(self, make_rehearsal, save_job):
        for job_id, fit in (("1", 90), ("2", 80), ("3", 70)):
            save_job(job_id, fit=fit)
        browser = FakeApplicationBrowser(
            {job_id: EasyApplyUnavailableError("Sem botão.") for job_id in ("1", "2", "3")}
        )

        result = make_rehearsal(browser, max_failures=2).run()

        assert result.status is ScanStatus.STOPPED
        assert "2 vagas seguidas" in result.reason
        assert browser.opened_jobs == ["1", "2"]

    def test_stops_when_the_session_is_blocked(self, make_rehearsal, save_job, applications):
        save_job("1")
        browser = FakeApplicationBrowser(
            {"1": FakeApplicationForm([REVIEW])}, job_url="https://www.linkedin.com/checkpoint/challenge/1"
        )

        result = make_rehearsal(browser).run()

        assert result.status is ScanStatus.STOPPED
        assert "verificação de segurança" in result.reason
        assert browser.snapshots == ["bloqueio"]
        assert status_of(applications, "1") is ApplicationStatus.CV_GENERATED

    def test_respects_the_job_limit(self, make_rehearsal, save_job):
        save_job("1", fit=90)
        save_job("2", fit=80)
        browser = FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW]), "2": FakeApplicationForm([REVIEW])})

        make_rehearsal(browser, max_jobs=1).run()

        assert browser.opened_jobs == ["1"]

    def test_rehearsed_job_is_not_opened_again(self, make_rehearsal, save_job):
        save_job("1")
        make_rehearsal(FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW])})).run()
        browser = FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW])})

        result = make_rehearsal(browser).run()

        assert browser.opened_jobs == []
        assert result.jobs_seen == 0

    def test_evidence_folder_identifies_the_job(self, make_rehearsal, save_job, tmp_path):
        save_job("1")

        make_rehearsal(FakeApplicationBrowser({"1": FakeApplicationForm([REVIEW])})).run()

        folder = tmp_path / "data" / "ensaios" / "2026-10-30_18-00-05_cv-1"
        text = (folder / "respostas.txt").read_text(encoding="utf-8")
        assert "Resultado: pronta para enviar (nada foi enviado)" in text

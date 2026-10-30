from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from job_applier.linkedin.job_scanner import JobScanner
from job_applier.linkedin.linkedin_browser import JobBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.page_snapshot import PageSnapshot
from job_applier.models.job_application import ApplicationStatus, ScanStatus
from job_applier.models.job_posting import JobPosting
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.storage.application_repository import SqliteApplicationRepository
from tests.factories import database_for, tracker_for
from tests.linkedin.pages import current_job_page, job_page, search_page
from tests.storage.conftest import application

TODAY = date(2026, 10, 29)


class FakeBrowser(JobBrowser):
    """Simula o LinkedIn: páginas de busca (por número de página) e páginas de vaga (por id)."""

    def __init__(self, search_pages: list[list[str]], job_pages: dict[str, str], job_url: str | None = None) -> None:
        self._search_pages = search_pages
        self._job_pages = job_pages
        self._job_url = job_url
        self.opened_jobs: list[str] = []
        self.snapshots: list[str] = []

    def open_search(self, url: str) -> PageSnapshot:
        start = int(parse_qs(urlsplit(url).query).get("start", ["0"])[0])
        page = start // 25
        ids = self._search_pages[page] if page < len(self._search_pages) else []
        return PageSnapshot(url=url, html=search_page(*ids), text="Vagas")

    def open_job(self, linkedin_id: str) -> PageSnapshot:
        self.opened_jobs.append(linkedin_id)
        url = self._job_url or JobPosting.url_for(linkedin_id)
        return PageSnapshot(url=url, html=self._job_pages[linkedin_id], text="Página da vaga " * 500)

    def save_snapshot(self, name: str) -> Path:
        self.snapshots.append(name)
        return Path(f"data/debug/{name}.html")


class FakePdfExporter:
    def export(self, html: str) -> bytes:
        return b"%PDF-fake"


def dev_job(title: str = "Desenvolvedor Python Júnior") -> str:
    return job_page(title=title, description="<p>Python, Docker e React para nosso time de produto.</p>")


@pytest.fixture
def applications(tmp_path) -> SqliteApplicationRepository:
    return SqliteApplicationRepository(database_for(tmp_path))


@pytest.fixture
def make_scanner(example_base_data, applications, tmp_path):
    def build(browser: JobBrowser, max_jobs: int | None = None, **settings_changes) -> JobScanner:
        settings = example_base_data.settings.model_copy(
            update={"searches": example_base_data.settings.searches[:1], **settings_changes}
        )
        generator = ResumeGenerator(
            example_base_data, ResumeArchive(tmp_path / "data" / "cvs"), exporter=FakePdfExporter(), today=lambda: TODAY
        )
        return JobScanner(
            browser,
            settings,
            generator,
            tracker_for(tmp_path),
            applications,
            Pacer(settings, sleep=lambda seconds: None),
            today=lambda: TODAY,
            max_jobs=max_jobs,
        )

    return build


class TestJobScanner:
    def test_records_new_jobs_with_resume_and_skips_processed_ones(self, make_scanner, applications):
        applications.save(application(job_key=JobPosting.url_for("2"), url=JobPosting.url_for("2")))
        browser = FakeBrowser([["1", "2", "3"]], {"1": dev_job(), "3": dev_job("Desenvolvedor Full Stack Júnior")})

        result = make_scanner(browser).run()

        assert browser.opened_jobs == ["1", "3"]
        assert (result.status, result.jobs_seen, result.jobs_recorded) == (ScanStatus.COMPLETED, 2, 2)
        recorded = {item.url: item for item in applications.list_all()}
        assert recorded[JobPosting.url_for("1")].status is ApplicationStatus.CV_GENERATED
        assert recorded[JobPosting.url_for("1")].resume_path.endswith(".pdf")
        assert recorded[JobPosting.url_for("1")].apply_type == "candidatura_simplificada"

    def test_follows_pages_until_an_empty_one(self, make_scanner):
        browser = FakeBrowser([["1"], ["2"]], {"1": dev_job(), "2": dev_job("Desenvolvedor Vue Júnior")})

        make_scanner(browser).run()

        assert browser.opened_jobs == ["1", "2"]

    def test_skips_forbidden_titles_and_support_roles_without_resume(self, make_scanner, applications):
        support = job_page(
            title="Assistente de TI",
            description="<p>Prestar suporte aos usuários, chamados no help desk, hardware e redes.</p>",
        )
        browser = FakeBrowser([["1", "2"]], {"1": dev_job("Desenvolvedor Python Sênior"), "2": support})

        make_scanner(browser).run()

        notes = {item.url: (item.status, item.notes, item.resume_path) for item in applications.list_all()}
        assert notes[JobPosting.url_for("1")] == (ApplicationStatus.SKIPPED, "Título contém 'sênior'", None)
        assert notes[JobPosting.url_for("2")] == (ApplicationStatus.SKIPPED, "Vaga de suporte", None)

    def test_skips_blocked_companies_without_resume(self, make_scanner, applications):
        browser = FakeBrowser([["1"]], {"1": current_job_page(job_id="1", company="BairesDev")})

        make_scanner(browser).run()

        [recorded] = applications.list_all()
        assert (recorded.status, recorded.notes, recorded.resume_path) == (
            ApplicationStatus.SKIPPED,
            "Empresa bloqueada (BairesDev)",
            None,
        )

    def test_reads_jobs_in_the_current_linkedin_layout(self, make_scanner, applications):
        browser = FakeBrowser([["1"]], {"1": current_job_page(job_id="1")})

        result = make_scanner(browser).run()

        [recorded] = applications.list_all()
        assert result.jobs_recorded == 1
        assert (recorded.company, recorded.status) == ("Jungle Gaming", ApplicationStatus.CV_GENERATED)

    def test_stops_at_the_daily_limit_counting_todays_resumes(self, make_scanner, applications):
        applications.save(application(job_key="antiga", created_at=TODAY.isoformat() + "T08:00:00"))
        browser = FakeBrowser([["1", "2"]], {"1": dev_job(), "2": dev_job()})

        result = make_scanner(browser, daily_application_limit=2).run()

        assert browser.opened_jobs == ["1"]
        assert result.reason == "Limite diário de vagas atingido."

    def test_stops_at_the_run_limit(self, make_scanner):
        browser = FakeBrowser([["1", "2"]], {"1": dev_job(), "2": dev_job()})

        result = make_scanner(browser, max_jobs=1).run()

        assert browser.opened_jobs == ["1"]
        assert "Limite desta execução" in result.reason

    def test_stops_immediately_on_security_check_saving_the_page(self, make_scanner, applications):
        browser = FakeBrowser(
            [["1", "2"]], {"1": dev_job(), "2": dev_job()}, job_url="https://www.linkedin.com/checkpoint/challenge/x"
        )

        result = make_scanner(browser).run()

        assert result.status is ScanStatus.STOPPED
        assert "verificação de segurança" in result.reason
        assert browser.opened_jobs == ["1"]
        assert browser.snapshots == ["bloqueio"]
        assert applications.list_all() == []

    def test_stops_after_consecutive_unrecognized_pages(self, make_scanner, example_base_data):
        broken = "<html><body><h1>Layout novo</h1></body></html>"
        browser = FakeBrowser([["1", "2", "3", "4"]], {"1": broken, "2": dev_job(), "3": broken, "4": broken})
        scan = example_base_data.settings.scan.model_copy(update={"max_consecutive_extraction_errors": 2})

        result = make_scanner(browser, scan=scan).run()

        assert result.status is ScanStatus.STOPPED
        assert "layout do LinkedIn pode ter mudado" in result.reason
        assert browser.snapshots == ["vaga-1", "vaga-3", "vaga-4"]
        assert result.jobs_seen == 1

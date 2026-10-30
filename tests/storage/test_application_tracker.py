from datetime import date, datetime

import pytest
from openpyxl import load_workbook

from job_applier.models.job_application import ApplicationStatus
from job_applier.models.job_description import JobDescription
from job_applier.models.job_posting import ApplyType, JobPosting
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from tests.factories import tracker_for

JOB = JobDescription(
    company="Empresa X",
    title="Desenvolvedor Python Júnior",
    text="Buscamos pessoa com Python, Docker e Kubernetes.",
    location="São Paulo",
    url="https://www.linkedin.com/jobs/view/42/",
)
POSTING = JobPosting(
    linkedin_id="42", description=JOB, apply_type=ApplyType.EASY_APPLY, applicants=37, posted_on=date(2026, 10, 27)
)


class FakePdfExporter:
    def export(self, html: str) -> bytes:
        return b"%PDF-fake"


@pytest.fixture
def generator(example_base_data, tmp_path) -> ResumeGenerator:
    return ResumeGenerator(
        example_base_data,
        ResumeArchive(tmp_path / "data" / "cvs"),
        exporter=FakePdfExporter(),
        today=lambda: date(2026, 10, 29),
    )


def tracker(tmp_path):
    return tracker_for(tmp_path, now=lambda: datetime(2026, 10, 29, 10, 30, 15, 123456))


class TestApplicationTracker:
    def test_records_generated_resume_end_to_end(self, generator, tmp_path):
        app_tracker = tracker(tmp_path)

        recorded = app_tracker.record(generator.generate(JOB))
        app_tracker.refresh_report()

        assert recorded.job_key == "https://www.linkedin.com/jobs/view/42/"
        assert recorded.resume_path == "data/cvs/2026-10-29_Empresa-X_Desenvolvedor-Python-Junior.pdf"
        assert recorded.created_at == datetime(2026, 10, 29, 10, 30, 15)
        assert recorded.description == JOB.text
        assert "Kubernetes" in recorded.missing_terms
        sheet = load_workbook(tmp_path / "data" / "candidaturas.xlsx")["Vagas"]
        assert sheet["B2"].value == "Empresa X"

    def test_records_linkedin_posting_details(self, generator, tmp_path):
        recorded = tracker(tmp_path).record(generator.generate(JOB), POSTING)

        assert (recorded.apply_type, recorded.applicants, recorded.posted_on) == (
            "candidatura_simplificada",
            37,
            date(2026, 10, 27),
        )

    def test_records_skipped_job_without_resume(self, generator, tmp_path):
        recorded = tracker(tmp_path).record_skipped(generator.evaluate(JOB), POSTING, "Vaga de suporte")

        assert recorded.status is ApplicationStatus.SKIPPED
        assert recorded.notes == "Vaga de suporte"
        assert recorded.resume_path is None
        assert not (tmp_path / "data" / "cvs").exists()

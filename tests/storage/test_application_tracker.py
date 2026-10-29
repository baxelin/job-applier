from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from job_applier.models.job_description import JobDescription
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.excel_report_writer import ExcelReportWriter


class FakePdfExporter:
    def export(self, html: str) -> bytes:
        return b"%PDF-fake"


def tracker(tmp_path: Path, applications, questions) -> ApplicationTracker:
    return ApplicationTracker(
        applications,
        questions,
        ExcelReportWriter(tmp_path / "data" / "candidaturas.xlsx", tmp_path),
        project_root=tmp_path,
        now=lambda: datetime(2026, 10, 29, 10, 30, 15, 123456),
    )


class TestApplicationTracker:
    def test_records_generated_resume_end_to_end(self, example_base_data, applications, questions, tmp_path):
        generator = ResumeGenerator(
            example_base_data,
            ResumeArchive(tmp_path / "data" / "cvs"),
            exporter=FakePdfExporter(),
            today=lambda: date(2026, 10, 29),
        )
        job = JobDescription(
            company="Empresa X",
            title="Desenvolvedor Python Júnior",
            text="Buscamos pessoa com Python, Docker e Kubernetes.",
            location="São Paulo",
            url="https://www.linkedin.com/jobs/view/42/",
        )
        app_tracker = tracker(tmp_path, applications, questions)

        recorded = app_tracker.record(generator.generate(job))
        app_tracker.refresh_report()

        assert recorded.job_key == "https://www.linkedin.com/jobs/view/42/"
        assert recorded.resume_path == "data/cvs/2026-10-29_Empresa-X_Desenvolvedor-Python-Junior.pdf"
        assert recorded.created_at == datetime(2026, 10, 29, 10, 30, 15)
        assert "Kubernetes" in recorded.missing_terms
        sheet = load_workbook(tmp_path / "data" / "candidaturas.xlsx")["Vagas"]
        assert sheet["B2"].value == "Empresa X"

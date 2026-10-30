from datetime import date, datetime

import pytest
from openpyxl import load_workbook

from job_applier.models.job_application import ApplicationStatus
from job_applier.models.job_description import JobDescription
from job_applier.models.job_posting import ApplyType, JobPosting
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.storage.application_repository import SqliteApplicationRepository
from tests.factories import database_for, tracker_for

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

    def test_easy_apply_job_stays_as_generated_resume(self, generator, tmp_path):
        recorded = tracker(tmp_path).record(generator.generate(JOB), POSTING)

        assert recorded.status is ApplicationStatus.CV_GENERATED
        assert recorded.external_apply_url is None

    def test_external_job_is_pending_with_its_link(self, generator, tmp_path):
        posting = POSTING.model_copy(
            update={"apply_type": ApplyType.EXTERNAL, "external_apply_url": "https://empresa.example/vaga"}
        )

        recorded = tracker(tmp_path).record(generator.generate(JOB), posting)

        assert recorded.status is ApplicationStatus.MANUAL_APPLICATION_PENDING
        assert recorded.external_apply_url == "https://empresa.example/vaga"

    def test_rehearsed_job_is_marked_as_ready(self, generator, tmp_path):
        app_tracker = tracker(tmp_path)
        recorded = app_tracker.record(generator.generate(JOB), POSTING)

        app_tracker.record_rehearsal_ready(recorded, "Ensaio em data/ensaios/x")

        saved = SqliteApplicationRepository(database_for(tmp_path)).list_all()[0]
        assert (saved.status, saved.notes) == (ApplicationStatus.REHEARSED, "Ensaio em data/ensaios/x")

    def test_unknown_questions_are_saved_and_leave_the_job_pending(self, generator, tmp_path):
        app_tracker = tracker(tmp_path)
        recorded = app_tracker.record(generator.generate(JOB), POSTING)

        app_tracker.record_unknown_questions(recorded, ["Primeira?", "Segunda?"])
        app_tracker.refresh_report()

        saved = SqliteApplicationRepository(database_for(tmp_path)).list_all()[0]
        assert saved.status is ApplicationStatus.UNKNOWN_QUESTION_PENDING
        assert saved.notes == "Sem resposta para: Primeira? | Segunda?"
        workbook = load_workbook(tmp_path / "data" / "candidaturas.xlsx")
        assert workbook["Vagas"]["E2"].value == "Pendente – pergunta sem resposta"
        assert {row[0].value for row in workbook["Perguntas"].iter_rows(min_row=2)} == {"Primeira?", "Segunda?"}
        assert workbook["Perguntas"]["C2"].value == "Empresa X - Desenvolvedor Python Júnior"

    def test_unavailable_job_is_skipped_with_the_reason(self, generator, tmp_path):
        app_tracker = tracker(tmp_path)
        recorded = app_tracker.record(generator.generate(JOB), POSTING)

        app_tracker.record_unavailable(recorded, "Sem botão de candidatura")

        saved = SqliteApplicationRepository(database_for(tmp_path)).list_all()[0]
        assert (saved.status, saved.notes) == (ApplicationStatus.SKIPPED, "Sem botão de candidatura")

    def test_failure_keeps_the_reason(self, generator, tmp_path):
        app_tracker = tracker(tmp_path)
        recorded = app_tracker.record(generator.generate(JOB), POSTING)

        app_tracker.record_failure(recorded, "A página não avançou")
        app_tracker.refresh_report()

        saved = SqliteApplicationRepository(database_for(tmp_path)).list_all()[0]
        assert (saved.status, saved.notes) == (ApplicationStatus.FAILED, "A página não avançou")

    def test_records_skipped_job_without_resume(self, generator, tmp_path):
        recorded = tracker(tmp_path).record_skipped(generator.evaluate(JOB), POSTING, "Vaga de suporte")

        assert recorded.status is ApplicationStatus.SKIPPED
        assert recorded.notes == "Vaga de suporte"
        assert recorded.resume_path is None
        assert not (tmp_path / "data" / "cvs").exists()

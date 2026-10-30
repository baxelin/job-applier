from datetime import date
from pathlib import Path

from job_applier.commands.generate_resumes_command import GenerateResumesCommand
from job_applier.config.json_model_loader import DataFileNotFoundError
from job_applier.resume.pdf_exporter import PdfExportError
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.storage.application_repository import SqliteApplicationRepository
from tests.factories import database_for, tracker_for


class FakeBaseDataLoader:
    def __init__(self, base_data) -> None:
        self._base_data = base_data

    def load(self):
        return self._base_data


class MissingBaseDataLoader:
    def load(self):
        raise DataFileNotFoundError(Path("personal/cv_base.json"))


class FakePdfExporter:
    def export(self, html: str) -> bytes:
        return b"%PDF-fake"


class UnavailablePdfExporter:
    def export(self, html: str) -> bytes:
        raise PdfExportError("WeasyPrint indisponível")


def write_job(directory: Path) -> Path:
    path = directory / "vaga.txt"
    path.write_text("Empresa: Empresa X\nVaga: Dev Júnior\n---\nPython e React.", encoding="utf-8")
    return path


def saved_applications(tmp_path: Path) -> SqliteApplicationRepository:
    return SqliteApplicationRepository(database_for(tmp_path))


def command(base_data_loader, tmp_path: Path, exporter) -> GenerateResumesCommand:
    return GenerateResumesCommand(
        base_data_loader,
        lambda base_data: ResumeGenerator(
            base_data, ResumeArchive(tmp_path / "cvs"), exporter=exporter, today=lambda: date(2026, 10, 29)
        ),
        tracker_for(tmp_path),
    )


class TestGenerateResumesCommand:
    def test_prints_analysis_and_resume_path(self, example_base_data, tmp_path, capsys):
        exit_code = command(FakeBaseDataLoader(example_base_data), tmp_path, FakePdfExporter()).run([write_job(tmp_path)])

        output = capsys.readouterr().out
        assert exit_code == 0
        assert "[Empresa X] Dev Júnior" in output
        assert "Aderência: 100%" in output
        assert "2026-10-29_Empresa-X_Dev-Junior.pdf" in output

    def test_records_job_in_database_and_spreadsheet(self, example_base_data, tmp_path, capsys):
        exit_code = command(FakeBaseDataLoader(example_base_data), tmp_path, FakePdfExporter()).run([write_job(tmp_path)])

        assert exit_code == 0
        assert [item.company for item in saved_applications(tmp_path).list_all()] == ["Empresa X"]
        assert (tmp_path / "data" / "candidaturas.xlsx").exists()
        assert "Planilha atualizada" in capsys.readouterr().out

    def test_locked_spreadsheet_keeps_data_and_only_warns(self, example_base_data, tmp_path, capsys):
        (tmp_path / "data" / "candidaturas.xlsx").mkdir(parents=True)

        exit_code = command(FakeBaseDataLoader(example_base_data), tmp_path, FakePdfExporter()).run([write_job(tmp_path)])

        assert exit_code == 0
        assert "próxima execução" in capsys.readouterr().err
        assert len(saved_applications(tmp_path).list_all()) == 1

    def test_warns_about_support_roles(self, example_base_data, tmp_path, capsys):
        job = tmp_path / "suporte.txt"
        job.write_text("Empresa: Y\nVaga: Analista de Suporte N1\n---\nAtendimento de chamados no help desk.", encoding="utf-8")

        command(FakeBaseDataLoader(example_base_data), tmp_path, FakePdfExporter()).run([job])

        assert "Parece vaga de SUPORTE" in capsys.readouterr().out

    def test_reports_missing_base_data(self, tmp_path, capsys):
        exit_code = command(MissingBaseDataLoader(), tmp_path, FakePdfExporter()).run([write_job(tmp_path)])

        assert exit_code == 1
        assert "Arquivo não encontrado" in capsys.readouterr().err

    def test_reports_pdf_export_failure(self, example_base_data, tmp_path, capsys):
        exit_code = command(FakeBaseDataLoader(example_base_data), tmp_path, UnavailablePdfExporter()).run(
            [write_job(tmp_path)]
        )

        assert exit_code == 1
        assert "WeasyPrint indisponível" in capsys.readouterr().err

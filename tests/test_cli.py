import pytest

from job_applier.cli import CommandLine


class TestCommandLine:
    def test_cv_command_requires_at_least_one_job(self):
        with pytest.raises(SystemExit):
            CommandLine().run(["cv"])

    def test_planilha_command_creates_spreadsheet_from_empty_database(self, tmp_path, capsys):
        exit_code = CommandLine(project_root=tmp_path).run(["planilha"])

        assert exit_code == 0
        assert (tmp_path / "data" / "candidaturas.xlsx").exists()
        assert (tmp_path / "data" / "job_applier.db").exists()

    def test_cv_command_reports_missing_base_data(self, tmp_path, capsys):
        job = tmp_path / "vaga.txt"
        job.write_text("Empresa: X\nVaga: Y\n---\nPython", encoding="utf-8")

        exit_code = CommandLine(project_root=tmp_path).run(["cv", str(job)])

        assert exit_code == 1
        assert "cv_base.json" in capsys.readouterr().err

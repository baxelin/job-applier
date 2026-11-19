import pytest

from job_applier.cli import CommandLine
from job_applier.linkedin.easy_apply_rehearsal import EasyApplyRehearsal
from job_applier.linkedin.easy_apply_submission import EasyApplySubmission
from job_applier.linkedin.job_scanner import JobScanner
from job_applier.linkedin.search_and_apply import SearchAndApply


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

    def test_rehearsal_command_validates_the_data_before_opening_the_browser(self, tmp_path, capsys):
        exit_code = CommandLine(project_root=tmp_path).run(["ensaiar", "--max-vagas", "1"])

        assert exit_code == 1
        assert "cv_base.json" in capsys.readouterr().err


class TestCommandFactories:
    """Montam o scanner e o ensaio sem abrir o navegador: pegam erros de ligação entre os argumentos."""

    def test_scan_command_builds_the_scanner(self, tmp_path, example_base_data):
        command = CommandLine(project_root=tmp_path)._scan_command(max_jobs=3)

        assert isinstance(command._scanner_factory(example_base_data, object()), JobScanner)

    @pytest.mark.parametrize("retry_pending", [True, False])
    def test_rehearsal_command_builds_the_rehearsal(self, tmp_path, example_base_data, retry_pending):
        command = CommandLine(project_root=tmp_path)._rehearsal_command(max_jobs=3, retry_pending=retry_pending)

        rehearsal = command._scanner_factory(example_base_data, object())

        assert isinstance(rehearsal, EasyApplyRehearsal)
        assert rehearsal._retry_pending is retry_pending

    @pytest.mark.parametrize("retry_pending", [True, False])
    def test_submission_command_builds_the_submission(self, tmp_path, example_base_data, retry_pending):
        command = CommandLine(project_root=tmp_path)._submission_command(max_jobs=3, retry_pending=retry_pending)

        submission = command._scanner_factory(example_base_data, object())

        assert isinstance(submission, EasyApplySubmission)
        assert submission._retry_pending is retry_pending

    def test_search_and_apply_command_links_the_scanner_to_the_submission(self, tmp_path, example_base_data):
        command = CommandLine(project_root=tmp_path)._search_and_apply_command(max_jobs=3)

        run = command._scanner_factory(example_base_data, object())

        assert isinstance(run, SearchAndApply)
        assert run._scanner._on_easy_apply_resume == run._submission.apply_to
        assert run._scanner._max_jobs == 3

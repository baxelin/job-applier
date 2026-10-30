from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import load_workbook

from job_applier.commands.scan_command import ScanCommand
from job_applier.config.json_model_loader import DataFileNotFoundError
from job_applier.linkedin.job_scanner import ScanResult
from job_applier.models.job_application import ScanStatus
from job_applier.storage.scan_run_repository import SqliteScanRunRepository
from tests.factories import database_for, tracker_for


class FakeBaseDataLoader:
    def __init__(self, base_data) -> None:
        self._base_data = base_data

    def load(self):
        return self._base_data


class MissingBaseDataLoader:
    def load(self):
        raise DataFileNotFoundError(Path("personal/cv_base.json"))


class FakeScanner:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def run(self) -> ScanResult:
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


class FakeBrowserSession:
    def __init__(self) -> None:
        self.closed = False

    @contextmanager
    def open(self):
        try:
            yield "navegador"
        finally:
            self.closed = True


def command(tmp_path: Path, outcome, browser: FakeBrowserSession, base_data_loader) -> ScanCommand:
    return ScanCommand(
        base_data_loader,
        browser.open,
        lambda base_data, opened_browser: FakeScanner(outcome),
        SqliteScanRunRepository(database_for(tmp_path)),
        tracker_for(tmp_path),
        now=lambda: datetime(2026, 10, 29, 9, 0, 0, 999),
    )


def recorded_runs(tmp_path: Path):
    return SqliteScanRunRepository(database_for(tmp_path)).list_recent(10)


class TestScanCommand:
    def test_records_completed_run_and_updates_spreadsheet(self, example_base_data, tmp_path, capsys):
        browser = FakeBrowserSession()
        outcome = ScanResult(ScanStatus.COMPLETED, "Todas as buscas foram percorridas.", jobs_seen=3, jobs_recorded=3)

        exit_code = command(tmp_path, outcome, browser, FakeBaseDataLoader(example_base_data)).run()

        assert exit_code == 0
        assert browser.closed
        [run] = recorded_runs(tmp_path)
        assert (run.status, run.jobs_recorded, run.finished_at) == (ScanStatus.COMPLETED, 3, datetime(2026, 10, 29, 9))
        sheet = load_workbook(tmp_path / "data" / "candidaturas.xlsx")["Execuções"]
        assert sheet["C2"].value == "Concluída"
        assert "3 vagas vistas" in capsys.readouterr().out

    def test_stopped_run_returns_error_code_with_reason(self, example_base_data, tmp_path):
        outcome = ScanResult(ScanStatus.STOPPED, "Captcha", jobs_seen=1, jobs_recorded=1)

        exit_code = command(tmp_path, outcome, FakeBrowserSession(), FakeBaseDataLoader(example_base_data)).run()

        assert exit_code == 1
        assert recorded_runs(tmp_path)[0].reason == "Captcha"

    def test_ctrl_c_is_recorded_as_interrupted_by_the_user(self, example_base_data, tmp_path):
        browser = FakeBrowserSession()

        exit_code = command(tmp_path, KeyboardInterrupt(), browser, FakeBaseDataLoader(example_base_data)).run()

        assert exit_code == 1
        assert browser.closed
        assert recorded_runs(tmp_path)[0].reason == "Interrompida pelo usuário (Ctrl+C)."

    def test_unexpected_error_is_recorded_and_raised(self, example_base_data, tmp_path):
        with pytest.raises(RuntimeError):
            command(tmp_path, RuntimeError("timeout"), FakeBrowserSession(), FakeBaseDataLoader(example_base_data)).run()

        assert recorded_runs(tmp_path)[0].reason == "Erro inesperado: RuntimeError('timeout')"

    def test_missing_base_data_does_not_open_the_browser(self, tmp_path, capsys):
        browser = FakeBrowserSession()

        exit_code = command(tmp_path, None, browser, MissingBaseDataLoader()).run()

        assert exit_code == 1
        assert not browser.closed
        assert recorded_runs(tmp_path) == []

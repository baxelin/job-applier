from pathlib import Path

from job_applier.app import Application
from job_applier.config.json_model_loader import DataFileNotFoundError


class FakeHealthCheck:
    def run(self) -> str:
        return "mensagem de teste"


class FakeBaseData:
    def describe(self) -> str:
        return "dados válidos"


class FakeBaseDataLoader:
    def load(self) -> FakeBaseData:
        return FakeBaseData()


class MissingBaseDataLoader:
    def load(self) -> FakeBaseData:
        raise DataFileNotFoundError(Path("personal/cv_base.json"))


class TestApplication:
    def test_run_prints_health_check_and_base_data_summary(self, capsys):
        exit_code = Application(FakeHealthCheck(), FakeBaseDataLoader()).run()

        assert exit_code == 0
        assert capsys.readouterr().out.splitlines() == ["mensagem de teste", "dados válidos"]

    def test_run_reports_base_data_error_and_fails(self, capsys):
        exit_code = Application(FakeHealthCheck(), MissingBaseDataLoader()).run()

        assert exit_code == 1
        assert "Arquivo não encontrado" in capsys.readouterr().err

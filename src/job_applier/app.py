import sys
from pathlib import Path

from job_applier.browser.firefox_health_check import FirefoxHealthCheck
from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.config.json_model_loader import DataFileError


class Application:
    """Ponto de entrada da aplicação."""

    def __init__(
        self,
        health_check: FirefoxHealthCheck | None = None,
        base_data_loader: BaseDataLoader | None = None,
    ) -> None:
        self._health_check = health_check or FirefoxHealthCheck()
        self._base_data_loader = base_data_loader or BaseDataLoader(BaseDataPaths.from_project_root(Path.cwd()))

    def run(self) -> int:
        print(self._health_check.run())

        try:
            base_data = self._base_data_loader.load()
        except DataFileError as error:
            print(f"Erro nos dados base. {error}", file=sys.stderr)
            return 1

        print(base_data.describe())
        return 0

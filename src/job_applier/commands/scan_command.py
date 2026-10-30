import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime

from job_applier.commands.refresh_report_command import RefreshReportCommand
from job_applier.config.base_data_loader import BaseDataLoader
from job_applier.config.json_model_loader import DataFileError
from job_applier.linkedin.job_scanner import JobScanner, ScanResult
from job_applier.linkedin.linkedin_browser import JobBrowser
from job_applier.models.base_data import BaseData
from job_applier.models.job_application import ScanRun, ScanStatus
from job_applier.resume.pdf_exporter import PdfExportError
from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.scan_run_repository import ScanRunRepository


class ScanCommand:
    """Executa a varredura de vagas no LinkedIn (só leitura) e registra a execução com o motivo de término."""

    def __init__(
        self,
        base_data_loader: BaseDataLoader,
        browser_factory: Callable[[], AbstractContextManager[JobBrowser]],
        scanner_factory: Callable[[BaseData, JobBrowser], JobScanner],
        runs: ScanRunRepository,
        tracker: ApplicationTracker,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._base_data_loader = base_data_loader
        self._browser_factory = browser_factory
        self._scanner_factory = scanner_factory
        self._runs = runs
        self._tracker = tracker
        self._now = now

    def run(self) -> int:
        try:
            base_data = self._base_data_loader.load()
        except DataFileError as error:
            print(f"Erro nos dados base. {error}", file=sys.stderr)
            return 1

        run = self._runs.save(ScanRun(started_at=self._timestamp()))
        try:
            with self._browser_factory() as browser:
                result = self._scanner_factory(base_data, browser).run()
        except PdfExportError as error:
            result = ScanResult(ScanStatus.STOPPED, str(error), jobs_seen=0, jobs_recorded=0)
        except KeyboardInterrupt:
            result = ScanResult(ScanStatus.STOPPED, "Interrompida pelo usuário (Ctrl+C).", jobs_seen=0, jobs_recorded=0)
        except Exception as error:
            result = ScanResult(ScanStatus.STOPPED, f"Erro inesperado: {error!r}", jobs_seen=0, jobs_recorded=0)
            raise
        finally:
            self._finish(run, result)

        return 0 if result.status is ScanStatus.COMPLETED else 1

    def _finish(self, run: ScanRun, result: ScanResult) -> None:
        self._runs.save(
            run.model_copy(
                update={
                    "finished_at": self._timestamp(),
                    "status": result.status,
                    "reason": result.reason,
                    "jobs_seen": result.jobs_seen,
                    "jobs_recorded": result.jobs_recorded,
                }
            )
        )
        print(
            f"Execução {result.status}: {result.reason} "
            f"({result.jobs_seen} vagas vistas, {result.jobs_recorded} registradas)."
        )
        RefreshReportCommand(self._tracker).run()

    def _timestamp(self) -> datetime:
        return self._now().replace(microsecond=0)

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from job_applier.app import Application
from job_applier.commands.generate_resumes_command import GenerateResumesCommand
from job_applier.commands.login_command import LoginCommand
from job_applier.commands.refresh_report_command import RefreshReportCommand
from job_applier.commands.scan_command import ScanCommand
from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.linkedin.job_scanner import JobScanner
from job_applier.linkedin.linkedin_browser import JobBrowser, LinkedInBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.models.base_data import BaseData
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.storage.application_repository import SqliteApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.database import Database
from job_applier.storage.excel_report_writer import ExcelReportWriter
from job_applier.storage.scan_run_repository import SqliteScanRunRepository
from job_applier.storage.unknown_question_repository import SqliteUnknownQuestionRepository


class CommandLine:
    """Interpreta os argumentos e executa o comando escolhido (padrão: validar o ambiente e os dados)."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._data_dir = self._project_root / "data"
        self._database = Database(self._data_dir / "job_applier.db")

    def run(self, arguments: Sequence[str]) -> int:
        parsed = self._parser().parse_args(arguments)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%d/%m %H:%M:%S")
        match parsed.command:
            case "cv":
                return self._generate_resumes_command().run(parsed.paths)
            case "planilha":
                return RefreshReportCommand(self._tracker()).run()
            case "login":
                return self._login_command().run()
            case "buscar":
                return self._scan_command(parsed.max_jobs).run()
            case _:
                return Application().run()

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="job_applier", description="Candidatura automatizada a vagas.")
        commands = parser.add_subparsers(dest="command")
        commands.add_parser("validar", help="Verifica o navegador e valida os dados base (padrão).")
        resume = commands.add_parser("cv", help="Gera CVs adaptados, registra no banco e atualiza a planilha.")
        resume.add_argument("paths", nargs="+", type=Path, metavar="vaga", help="Arquivo .txt ou pasta com vagas.")
        commands.add_parser("planilha", help="Recria data/candidaturas.xlsx a partir do banco.")
        commands.add_parser("login", help="Abre o LinkedIn para login manual (perfil persistente).")
        scan = commands.add_parser("buscar", help="Percorre as buscas do config.json e registra as vagas (sem aplicar).")
        scan.add_argument("--max-vagas", dest="max_jobs", type=int, help="Para depois de abrir N vagas.")
        return parser

    def _generate_resumes_command(self) -> GenerateResumesCommand:
        return GenerateResumesCommand(self._base_data_loader(), self._resume_generator, self._tracker())

    def _login_command(self) -> LoginCommand:
        timeout = self._base_data_loader().load().settings.scan.login_timeout_minutes
        return LoginCommand(self._browser, timeout)

    def _scan_command(self, max_jobs: int | None) -> ScanCommand:
        tracker = self._tracker()

        def scanner_factory(base_data: BaseData, browser: JobBrowser) -> JobScanner:
            return JobScanner(
                browser,
                base_data.settings,
                self._resume_generator(base_data),
                tracker,
                SqliteApplicationRepository(self._database),
                Pacer(base_data.settings),
                max_jobs=max_jobs,
            )

        return ScanCommand(
            self._base_data_loader(),
            self._browser,
            scanner_factory,
            SqliteScanRunRepository(self._database),
            tracker,
        )

    def _browser(self) -> LinkedInBrowser:
        return LinkedInBrowser(self._project_root / "profile", self._data_dir / "debug")

    def _resume_generator(self, base_data: BaseData) -> ResumeGenerator:
        return ResumeGenerator(base_data, ResumeArchive(self._data_dir / "cvs"))

    def _base_data_loader(self) -> BaseDataLoader:
        return BaseDataLoader(BaseDataPaths.from_project_root(self._project_root))

    def _tracker(self) -> ApplicationTracker:
        return ApplicationTracker(
            SqliteApplicationRepository(self._database),
            SqliteUnknownQuestionRepository(self._database),
            SqliteScanRunRepository(self._database),
            ExcelReportWriter(self._data_dir / "candidaturas.xlsx", self._project_root),
            self._project_root,
        )

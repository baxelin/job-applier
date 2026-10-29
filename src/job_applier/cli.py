import argparse
from collections.abc import Sequence
from pathlib import Path

from job_applier.app import Application
from job_applier.commands.generate_resumes_command import GenerateResumesCommand
from job_applier.commands.refresh_report_command import RefreshReportCommand
from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.storage.application_repository import SqliteApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.database import Database
from job_applier.storage.excel_report_writer import ExcelReportWriter
from job_applier.storage.unknown_question_repository import SqliteUnknownQuestionRepository


class CommandLine:
    """Interpreta os argumentos e executa o comando escolhido (padrão: validar o ambiente e os dados)."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._data_dir = self._project_root / "data"

    def run(self, arguments: Sequence[str]) -> int:
        parsed = self._parser().parse_args(arguments)
        if parsed.command == "cv":
            return self._generate_resumes_command().run(parsed.paths)
        if parsed.command == "planilha":
            return RefreshReportCommand(self._tracker()).run()
        return Application().run()

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="job_applier", description="Candidatura automatizada a vagas.")
        commands = parser.add_subparsers(dest="command")
        commands.add_parser("validar", help="Verifica o navegador e valida os dados base (padrão).")
        resume = commands.add_parser("cv", help="Gera CVs adaptados, registra no banco e atualiza a planilha.")
        resume.add_argument("paths", nargs="+", type=Path, metavar="vaga", help="Arquivo .txt ou pasta com vagas.")
        commands.add_parser("planilha", help="Recria data/candidaturas.xlsx a partir do banco.")
        return parser

    def _generate_resumes_command(self) -> GenerateResumesCommand:
        archive = ResumeArchive(self._data_dir / "cvs")
        return GenerateResumesCommand(
            BaseDataLoader(BaseDataPaths.from_project_root(self._project_root)),
            lambda base_data: ResumeGenerator(base_data, archive),
            self._tracker(),
        )

    def _tracker(self) -> ApplicationTracker:
        database = Database(self._data_dir / "job_applier.db")
        return ApplicationTracker(
            SqliteApplicationRepository(database),
            SqliteUnknownQuestionRepository(database),
            ExcelReportWriter(self._data_dir / "candidaturas.xlsx", self._project_root),
            self._project_root,
        )

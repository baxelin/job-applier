import argparse
from collections.abc import Sequence
from pathlib import Path

from job_applier.app import Application
from job_applier.commands.generate_resumes_command import GenerateResumesCommand
from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.models.base_data import BaseData
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator


class CommandLine:
    """Interpreta os argumentos e executa o comando escolhido (padrão: validar o ambiente e os dados)."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()

    def run(self, arguments: Sequence[str]) -> int:
        parsed = self._parser().parse_args(arguments)
        if parsed.command == "cv":
            return self._generate_resumes_command().run(parsed.paths)
        return Application().run()

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="job_applier", description="Candidatura automatizada a vagas.")
        commands = parser.add_subparsers(dest="command")
        commands.add_parser("validar", help="Verifica o navegador e valida os dados base (padrão).")
        resume = commands.add_parser("cv", help="Gera CVs adaptados a partir de vagas salvas em .txt.")
        resume.add_argument("paths", nargs="+", type=Path, metavar="vaga", help="Arquivo .txt ou pasta com vagas.")
        return parser

    def _generate_resumes_command(self) -> GenerateResumesCommand:
        archive = ResumeArchive(self._project_root / "data" / "cvs")
        return GenerateResumesCommand(
            BaseDataLoader(BaseDataPaths.from_project_root(self._project_root)),
            lambda base_data: ResumeGenerator(base_data, archive),
        )

import argparse
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from job_applier.answering.form_answerer import FormAnswerer
from job_applier.app import Application
from job_applier.commands.daily_report_command import DailyReportCommand
from job_applier.commands.generate_resumes_command import GenerateResumesCommand
from job_applier.commands.login_command import LoginCommand
from job_applier.commands.refresh_report_command import RefreshReportCommand
from job_applier.commands.scan_command import BrowserRun, ScanCommand
from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.execution_log import ExecutionLog
from job_applier.linkedin.easy_apply_filler import EasyApplyFiller
from job_applier.linkedin.easy_apply_rehearsal import EasyApplyRehearsal
from job_applier.linkedin.easy_apply_run import EasyApplyRun
from job_applier.linkedin.easy_apply_submission import EasyApplySubmission
from job_applier.linkedin.job_scanner import JobScanner
from job_applier.linkedin.linkedin_browser import JobBrowser, LinkedInBrowser
from job_applier.linkedin.pacer import Pacer
from job_applier.linkedin.search_and_apply import SearchAndApply
from job_applier.matching.location_policy import LocationPolicy
from job_applier.models.automation_settings import AutomationSettings
from job_applier.models.base_data import BaseData
from job_applier.models.job_application import JobApplication
from job_applier.reporting.daily_summary import DailySummaryBuilder
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_generator import ResumeGenerator
from job_applier.resume.resume_upload_file import ResumeUploadFileLoader
from job_applier.storage.application_repository import SqliteApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.database import Database
from job_applier.storage.excel_report_writer import ExcelReportWriter
from job_applier.storage.scan_run_repository import SqliteScanRunRepository
from job_applier.storage.search_progress_repository import SqliteSearchProgressRepository
from job_applier.storage.unknown_question_repository import SqliteUnknownQuestionRepository
from job_applier.termination import TerminationSignal


class CommandLine:
    """Interpreta os argumentos e executa o comando escolhido (padrão: validar o ambiente e os dados)."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._data_dir = self._project_root / "data"
        self._database = Database(self._data_dir / "job_applier.db")
        self._log = ExecutionLog(self._data_dir / "logs")

    def run(self, arguments: Sequence[str]) -> int:
        parsed = self._parser().parse_args(arguments)
        self._log.configure()
        try:
            with TerminationSignal():
                return self._run_command(parsed)
        finally:
            self._log.close()

    def _run_command(self, parsed: argparse.Namespace) -> int:
        match parsed.command:
            case "cv":
                return self._generate_resumes_command().run(parsed.paths)
            case "planilha":
                return RefreshReportCommand(self._tracker()).run()
            case "login":
                return self._login_command().run()
            case "relatorio":
                return self._daily_report_command().run(parsed.day)
            case "buscar":
                return self._then_report(self._scan_command(parsed.max_jobs).run())
            case "ensaiar":
                return self._then_report(self._rehearsal_command(parsed.max_jobs, parsed.retry_pending).run())
            case "aplicar":
                return self._then_report(self._submission_command(parsed.max_jobs, parsed.retry_pending).run())
            case "buscar-e-aplicar":
                return self._then_report(self._search_and_apply_command(parsed.max_jobs).run())
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
        report = commands.add_parser("relatorio", help="Resumo do dia: enviadas, pendências e perguntas novas.")
        report.add_argument(
            "--data", dest="day", type=date.fromisoformat, metavar="AAAA-MM-DD", help="Outro dia (padrão: hoje)."
        )
        scan = commands.add_parser("buscar", help="Percorre as buscas do config.json e registra as vagas (sem aplicar).")
        scan.add_argument("--max-vagas", dest="max_jobs", type=int, help="Para depois de abrir N vagas.")
        rehearsal = commands.add_parser(
            "ensaiar", help="Preenche os formulários de Candidatura Simplificada e para antes de enviar."
        )
        rehearsal.add_argument(
            "--max-vagas", dest="max_jobs", type=int, default=20, help="Quantas vagas ensaiar (padrão: 20)."
        )
        rehearsal.add_argument(
            "--repetir-pendentes",
            dest="retry_pending",
            action="store_true",
            help="Depois das vagas novas, tenta de novo as pendentes de pergunta e as com erro.",
        )
        submission = commands.add_parser(
            "aplicar", help="Envia as candidaturas simplificadas, até o limite diário de envios do config.json."
        )
        submission.add_argument("--max-vagas", dest="max_jobs", type=int, help="Abre no máximo N vagas.")
        submission.add_argument(
            "--repetir-pendentes",
            dest="retry_pending",
            action="store_true",
            help="Depois das vagas novas, tenta de novo as pendentes de pergunta (nunca as com erro).",
        )
        search_and_apply = commands.add_parser(
            "buscar-e-aplicar",
            help="Percorre as buscas e se candidata a cada vaga simplificada logo depois de gerar o CV.",
        )
        search_and_apply.add_argument("--max-vagas", dest="max_jobs", type=int, help="Para depois de abrir N vagas.")
        return parser

    def _then_report(self, exit_code: int) -> int:
        """Depois de cada execução no navegador, o resumo do dia aparece no terminal."""
        print()
        self._daily_report_command().run()
        return exit_code

    def _daily_report_command(self) -> DailyReportCommand:
        return DailyReportCommand(
            DailySummaryBuilder(
                SqliteApplicationRepository(self._database), SqliteUnknownQuestionRepository(self._database)
            )
        )

    def _generate_resumes_command(self) -> GenerateResumesCommand:
        return GenerateResumesCommand(self._base_data_loader(), self._resume_generator, self._tracker())

    def _login_command(self) -> LoginCommand:
        timeout = self._base_data_loader().load().settings.scan.login_timeout_minutes
        return LoginCommand(self._browser, timeout)

    def _scan_command(self, max_jobs: int | None) -> ScanCommand:
        tracker = self._tracker()

        def scanner_factory(base_data: BaseData, browser: JobBrowser) -> JobScanner:
            return self._scanner(base_data, browser, tracker, max_jobs)

        return self._browser_command(scanner_factory, tracker)

    def _search_and_apply_command(self, max_jobs: int | None) -> ScanCommand[LinkedInBrowser]:
        """A busca abre a vaga e gera o CV; o envio usa o mesmo navegador logo em seguida."""
        tracker = self._tracker()

        def factory(base_data: BaseData, browser: LinkedInBrowser) -> SearchAndApply:
            submission = EasyApplySubmission(
                *self._easy_apply_parts(base_data, browser, tracker, "envios"),
                daily_limit=base_data.settings.daily_submission_limit,
                location_policy=self._location_policy(base_data.settings),
            )
            scanner = self._scanner(base_data, browser, tracker, max_jobs, on_easy_apply_resume=submission.apply_to)
            return SearchAndApply(scanner, submission)

        return self._browser_command(factory, tracker)

    def _scanner(
        self,
        base_data: BaseData,
        browser: JobBrowser,
        tracker: ApplicationTracker,
        max_jobs: int | None,
        on_easy_apply_resume: Callable[[JobApplication], None] | None = None,
    ) -> JobScanner:
        return JobScanner(
            browser,
            base_data.settings,
            self._resume_generator(base_data),
            tracker,
            SqliteApplicationRepository(self._database),
            Pacer(base_data.settings),
            max_jobs=max_jobs,
            on_easy_apply_resume=on_easy_apply_resume,
            progress=SqliteSearchProgressRepository(self._database),
        )

    def _rehearsal_command(self, max_jobs: int, retry_pending: bool) -> ScanCommand[LinkedInBrowser]:
        return self._easy_apply_command(
            "ensaios",
            lambda parts, settings: EasyApplyRehearsal(
                *parts,
                max_jobs=max_jobs,
                retry_pending=retry_pending,
                location_policy=self._location_policy(settings),
            ),
        )

    def _submission_command(self, max_jobs: int | None, retry_pending: bool) -> ScanCommand[LinkedInBrowser]:
        return self._easy_apply_command(
            "envios",
            lambda parts, settings: EasyApplySubmission(
                *parts,
                max_jobs=max_jobs,
                daily_limit=settings.daily_submission_limit,
                retry_pending=retry_pending,
                location_policy=self._location_policy(settings),
            ),
        )

    def _easy_apply_command(
        self, evidence_folder: str, build: Callable[[tuple, AutomationSettings], EasyApplyRun]
    ) -> ScanCommand[LinkedInBrowser]:
        """Ensaio e envio usam as mesmas peças; muda só o que acontece na tela final."""
        tracker = self._tracker()

        def factory(base_data: BaseData, browser: LinkedInBrowser) -> EasyApplyRun:
            return build(self._easy_apply_parts(base_data, browser, tracker, evidence_folder), base_data.settings)

        return self._browser_command(factory, tracker)

    def _easy_apply_parts(
        self, base_data: BaseData, browser: LinkedInBrowser, tracker: ApplicationTracker, evidence_folder: str
    ) -> tuple:
        answerer = FormAnswerer(
            base_data.answer_book,
            base_data.resume,
            base_data.glossary,
            location_policy=self._location_policy(base_data.settings),
        )
        pacer = Pacer(base_data.settings)
        return (
            browser,
            EasyApplyFiller(answerer, pacer),
            ResumeUploadFileLoader(self._project_root, base_data.resume.contact),
            tracker,
            SqliteApplicationRepository(self._database),
            pacer,
            self._data_dir / evidence_folder,
            base_data.settings.scan.max_consecutive_extraction_errors,
        )

    @staticmethod
    def _location_policy(settings: AutomationSettings) -> LocationPolicy:
        return LocationPolicy(settings.filters.on_site_cities)

    def _browser_command(
        self, factory: Callable[[BaseData, LinkedInBrowser], BrowserRun], tracker: ApplicationTracker
    ) -> ScanCommand[LinkedInBrowser]:
        return ScanCommand(
            self._base_data_loader(),
            self._browser,
            factory,
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

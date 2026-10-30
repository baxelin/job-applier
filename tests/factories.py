from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from job_applier.storage.application_repository import SqliteApplicationRepository
from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.database import Database
from job_applier.storage.excel_report_writer import ExcelReportWriter
from job_applier.storage.scan_run_repository import SqliteScanRunRepository
from job_applier.storage.unknown_question_repository import SqliteUnknownQuestionRepository


def database_for(project_root: Path) -> Database:
    return Database(project_root / "data" / "job_applier.db")


def tracker_for(project_root: Path, now: Callable[[], datetime] = datetime.now) -> ApplicationTracker:
    """Tracker real (SQLite + Excel) dentro de uma pasta temporária de testes."""
    database = database_for(project_root)
    return ApplicationTracker(
        SqliteApplicationRepository(database),
        SqliteUnknownQuestionRepository(database),
        SqliteScanRunRepository(database),
        ExcelReportWriter(project_root / "data" / "candidaturas.xlsx", project_root),
        project_root=project_root,
        now=now,
    )

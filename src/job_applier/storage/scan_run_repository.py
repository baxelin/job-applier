from abc import ABC, abstractmethod

from job_applier.models.job_application import ScanRun
from job_applier.storage.database import Database


class ScanRunRepository(ABC):
    """Histórico das execuções da varredura, com o motivo de cada término."""

    @abstractmethod
    def save(self, run: ScanRun) -> ScanRun:
        """Cria a execução (sem id) ou atualiza uma existente (com id)."""

    @abstractmethod
    def list_recent(self, limit: int) -> list[ScanRun]:
        """As execuções mais recentes primeiro."""


class SqliteScanRunRepository(ScanRunRepository):
    _COLUMNS = ("started_at", "finished_at", "status", "reason", "jobs_seen", "jobs_recorded")

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, run: ScanRun) -> ScanRun:
        row = run.model_dump(mode="json", include=set(self._COLUMNS))
        with self._database.connect() as connection:
            if run.id is None:
                columns = ", ".join(self._COLUMNS)
                values = ", ".join(f":{column}" for column in self._COLUMNS)
                cursor = connection.execute(f"INSERT INTO scan_runs ({columns}) VALUES ({values})", row)
                return run.model_copy(update={"id": cursor.lastrowid})
            updates = ", ".join(f"{column} = :{column}" for column in self._COLUMNS)
            connection.execute(f"UPDATE scan_runs SET {updates} WHERE id = :id", {**row, "id": run.id})
        return run

    def list_recent(self, limit: int) -> list[ScanRun]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [ScanRun.model_validate(dict(row)) for row in rows]

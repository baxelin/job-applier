from abc import ABC, abstractmethod
from datetime import datetime

from job_applier.storage.database import Database


class SearchProgressRepository(ABC):
    """Quando cada busca do config.json foi percorrida inteira pela última vez."""

    @abstractmethod
    def last_completed(self, search_key: str) -> datetime | None:
        """Início da última vez em que a busca chegou ao fim dos resultados (None se nunca chegou)."""

    @abstractmethod
    def mark_completed(self, search_key: str, started_at: datetime) -> None:
        """Registra que a busca, iniciada em started_at, chegou ao fim dos resultados."""


class SqliteSearchProgressRepository(SearchProgressRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    def last_completed(self, search_key: str) -> datetime | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT completed_at FROM search_progress WHERE search_key = ?", (search_key,)
            ).fetchone()
        return datetime.fromisoformat(row["completed_at"]) if row else None

    def mark_completed(self, search_key: str, started_at: datetime) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO search_progress (search_key, completed_at) VALUES (?, ?)
                ON CONFLICT (search_key) DO UPDATE SET completed_at = excluded.completed_at
                """,
                (search_key, started_at.isoformat()),
            )

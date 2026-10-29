import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Database:
    """Banco SQLite local (data/job_applier.db): fonte da verdade das vagas e perguntas.

    As tabelas são criadas na primeira conexão; cada bloco `with database.connect()` é uma transação.
    """

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_key TEXT NOT NULL UNIQUE,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            url TEXT,
            locale TEXT NOT NULL,
            focus TEXT NOT NULL,
            is_support_role INTEGER NOT NULL,
            fit_percentage INTEGER NOT NULL,
            matched_terms TEXT NOT NULL,
            missing_terms TEXT NOT NULL,
            resume_path TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS unknown_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_key TEXT NOT NULL UNIQUE,
            question TEXT NOT NULL,
            occurrences INTEGER NOT NULL,
            last_application_id INTEGER REFERENCES job_applications(id),
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._schema_ready = False

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                self._ensure_schema(connection)
                yield connection
        finally:
            connection.close()

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        if not self._schema_ready:
            connection.executescript(self._SCHEMA)
            self._schema_ready = True

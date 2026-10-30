import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Database:
    """Banco SQLite local (data/job_applier.db): fonte da verdade das vagas, perguntas e execuções.

    O esquema evolui por migrações numeradas (PRAGMA user_version), aplicadas na primeira conexão;
    cada bloco `with database.connect()` é uma transação.
    """

    _MIGRATIONS = (
        # 1: vagas e perguntas desconhecidas
        """
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
        """,
        # 2: dados do anúncio do LinkedIn, CV opcional (vagas ignoradas) e registro das execuções
        """
        CREATE TABLE job_applications_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_key TEXT NOT NULL UNIQUE,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            url TEXT,
            description TEXT,
            locale TEXT NOT NULL,
            focus TEXT NOT NULL,
            is_support_role INTEGER NOT NULL,
            fit_percentage INTEGER NOT NULL,
            matched_terms TEXT NOT NULL,
            missing_terms TEXT NOT NULL,
            resume_path TEXT,
            apply_type TEXT,
            applicants INTEGER,
            posted_on TEXT,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO job_applications_new (
            id, job_key, company, title, location, url, locale, focus, is_support_role, fit_percentage,
            matched_terms, missing_terms, resume_path, status, created_at, updated_at
        )
        SELECT
            id, job_key, company, title, location, url, locale, focus, is_support_role, fit_percentage,
            matched_terms, missing_terms, resume_path, status, created_at, updated_at
        FROM job_applications;
        DROP TABLE job_applications;
        ALTER TABLE job_applications_new RENAME TO job_applications;

        CREATE TABLE scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            reason TEXT,
            jobs_seen INTEGER NOT NULL,
            jobs_recorded INTEGER NOT NULL
        );
        """,
    )

    def __init__(self, path: Path) -> None:
        self._path = path
        self._schema_ready = False

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        try:
            if not self._schema_ready:
                self._migrate(connection)
                self._schema_ready = True
            with connection:
                yield connection
        finally:
            connection.close()

    def _migrate(self, connection: sqlite3.Connection) -> None:
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        for version, script in enumerate(self._MIGRATIONS[current_version:], start=current_version + 1):
            connection.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;")

import json
import sqlite3
from abc import ABC, abstractmethod

from job_applier.models.job_application import JobApplication
from job_applier.storage.database import Database


class ApplicationRepository(ABC):
    """Onde as vagas processadas ficam guardadas."""

    @abstractmethod
    def save(self, application: JobApplication) -> JobApplication:
        """Grava a vaga; se ela já existir (mesmo job_key), atualiza mantendo status e data de criação."""

    @abstractmethod
    def list_all(self) -> list[JobApplication]:
        """Todas as vagas, das mais recentes para as mais antigas."""


class SqliteApplicationRepository(ApplicationRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, application: JobApplication) -> JobApplication:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO job_applications (
                    job_key, company, title, location, url, locale, focus, is_support_role, fit_percentage,
                    matched_terms, missing_terms, resume_path, status, created_at, updated_at
                ) VALUES (
                    :job_key, :company, :title, :location, :url, :locale, :focus, :is_support_role, :fit_percentage,
                    :matched_terms, :missing_terms, :resume_path, :status, :created_at, :updated_at
                )
                ON CONFLICT (job_key) DO UPDATE SET
                    company = excluded.company, title = excluded.title, location = excluded.location,
                    url = excluded.url, locale = excluded.locale, focus = excluded.focus,
                    is_support_role = excluded.is_support_role, fit_percentage = excluded.fit_percentage,
                    matched_terms = excluded.matched_terms, missing_terms = excluded.missing_terms,
                    resume_path = excluded.resume_path, updated_at = excluded.updated_at
                """,
                self._to_row(application),
            )
            row = connection.execute(
                "SELECT * FROM job_applications WHERE job_key = ?", (application.job_key,)
            ).fetchone()
        return self._from_row(row)

    def list_all(self) -> list[JobApplication]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM job_applications ORDER BY created_at DESC, id DESC").fetchall()
        return [self._from_row(row) for row in rows]

    _TERM_COLUMNS = ("matched_terms", "missing_terms")

    @classmethod
    def _to_row(cls, application: JobApplication) -> dict[str, object]:
        row = application.model_dump(mode="json", exclude={"id"})
        for column in cls._TERM_COLUMNS:
            row[column] = json.dumps(row[column], ensure_ascii=False)
        return row

    @classmethod
    def _from_row(cls, row: sqlite3.Row) -> JobApplication:
        data = dict(row)
        for column in cls._TERM_COLUMNS:
            data[column] = json.loads(data[column])
        return JobApplication.model_validate(data)

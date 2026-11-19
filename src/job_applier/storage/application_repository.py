import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import date, datetime

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.job_application import ApplicationStatus, JobApplication
from job_applier.models.job_posting import ApplyType
from job_applier.storage.database import Database


class ApplicationRepository(ABC):
    """Onde as vagas processadas ficam guardadas."""

    @abstractmethod
    def save(self, application: JobApplication) -> JobApplication:
        """Grava a vaga; se ela já existir (mesmo job_key), atualiza mantendo status e data de criação."""

    @abstractmethod
    def exists(self, job_key: str) -> bool:
        """Se a vaga já foi processada antes."""

    @abstractmethod
    def has_company_and_title(self, company: str, title: str) -> bool:
        """Se já existe vaga com a mesma empresa e o mesmo título (ignorando maiúsculas, acentos e espaços)."""

    @abstractmethod
    def count_processed_on(self, day: date) -> int:
        """Quantas vagas tiveram CV gerado no dia (as ignoradas não contam para o limite diário)."""

    @abstractmethod
    def list_all(self) -> list[JobApplication]:
        """Todas as vagas, das mais recentes para as mais antigas."""

    @abstractmethod
    def list_ready_for_easy_apply(self, limit: int | None = None, retry_pending: bool = False) -> list[JobApplication]:
        """Vagas simplificadas com CV nunca tentadas, por aderência.

        Com retry_pending, as pendentes de pergunta e com erro entram depois das novas: só vale a pena
        repeti-las quando respostas.json ganhou respostas novas ou um erro foi corrigido.
        """

    @abstractmethod
    def list_ready_for_submission(self, retry_pending: bool = False) -> list[JobApplication]:
        """Vagas simplificadas com CV a enviar: as que passaram no ensaio, as novas e, com retry_pending, as
        pendentes de pergunta, nessa ordem e por aderência. Vagas com erro nunca entram: o erro pode ser um
        envio sem confirmação, e repetir poderia mandar a mesma candidatura duas vezes."""

    @abstractmethod
    def count_applied_on(self, day: date) -> int:
        """Quantas candidaturas foram enviadas no dia."""

    @abstractmethod
    def mark_applied(self, job_key: str, notes: str, applied_at: datetime) -> None:
        """Registra a candidatura enviada, com a data do envio."""

    @abstractmethod
    def update_status(self, job_key: str, status: ApplicationStatus, notes: str | None, updated_at: datetime) -> None:
        """Muda a situação da vaga e registra o motivo em observações."""


class SqliteApplicationRepository(ApplicationRepository):
    _COLUMNS = tuple(name for name in JobApplication.model_fields if name != "id")
    _KEPT_ON_UPDATE = frozenset({"job_key", "status", "created_at", "applied_at"})
    _TERM_COLUMNS = ("matched_terms", "missing_terms")
    _RETRIED_STATUSES = (ApplicationStatus.UNKNOWN_QUESTION_PENDING, ApplicationStatus.FAILED)
    _NO_LIMIT = -1

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, application: JobApplication) -> JobApplication:
        columns = ", ".join(self._COLUMNS)
        values = ", ".join(f":{column}" for column in self._COLUMNS)
        updates = ", ".join(
            f"{column} = excluded.{column}" for column in self._COLUMNS if column not in self._KEPT_ON_UPDATE
        )
        with self._database.connect() as connection:
            connection.execute(
                f"INSERT INTO job_applications ({columns}) VALUES ({values}) "
                f"ON CONFLICT (job_key) DO UPDATE SET {updates}",
                self._to_row(application),
            )
            row = connection.execute(
                "SELECT * FROM job_applications WHERE job_key = ?", (application.job_key,)
            ).fetchone()
        return self._from_row(row)

    def exists(self, job_key: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute("SELECT 1 FROM job_applications WHERE job_key = ?", (job_key,)).fetchone()
        return row is not None

    def has_company_and_title(self, company: str, title: str) -> bool:
        wanted = self._comparable(company, title)
        with self._database.connect() as connection:
            rows = connection.execute("SELECT company, title FROM job_applications").fetchall()
        return any(self._comparable(row["company"], row["title"]) == wanted for row in rows)

    @staticmethod
    def _comparable(company: str, title: str) -> tuple[str, str]:
        return tuple(" ".join(TextNormalizer.normalize(text).split()) for text in (company, title))

    def count_processed_on(self, day: date) -> int:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM job_applications WHERE substr(created_at, 1, 10) = ? AND status != ?",
                (day.isoformat(), ApplicationStatus.SKIPPED.value),
            ).fetchone()
        return row[0]

    def list_all(self) -> list[JobApplication]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM job_applications ORDER BY created_at DESC, id DESC").fetchall()
        return [self._from_row(row) for row in rows]

    def list_ready_for_easy_apply(self, limit: int | None = None, retry_pending: bool = False) -> list[JobApplication]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM job_applications
                WHERE apply_type = :apply_type AND resume_path IS NOT NULL
                  AND (status = :new_status OR (:retry_pending AND status IN (:first_retried, :second_retried)))
                ORDER BY status = :new_status DESC, fit_percentage DESC, id
                LIMIT :limit
                """,
                {
                    "apply_type": ApplyType.EASY_APPLY.value,
                    "new_status": ApplicationStatus.CV_GENERATED.value,
                    "first_retried": self._RETRIED_STATUSES[0].value,
                    "second_retried": self._RETRIED_STATUSES[1].value,
                    "retry_pending": retry_pending,
                    "limit": self._NO_LIMIT if limit is None else limit,
                },
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_ready_for_submission(self, retry_pending: bool = False) -> list[JobApplication]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM job_applications
                WHERE apply_type = :apply_type AND resume_path IS NOT NULL
                  AND (status IN (:rehearsed, :new_status) OR (:retry_pending AND status = :pending))
                ORDER BY status = :rehearsed DESC, status = :new_status DESC, fit_percentage DESC, id
                """,
                {
                    "apply_type": ApplyType.EASY_APPLY.value,
                    "rehearsed": ApplicationStatus.REHEARSED.value,
                    "new_status": ApplicationStatus.CV_GENERATED.value,
                    "pending": ApplicationStatus.UNKNOWN_QUESTION_PENDING.value,
                    "retry_pending": retry_pending,
                },
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count_applied_on(self, day: date) -> int:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM job_applications WHERE substr(applied_at, 1, 10) = ?", (day.isoformat(),)
            ).fetchone()
        return row[0]

    def mark_applied(self, job_key: str, notes: str, applied_at: datetime) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE job_applications SET status = ?, notes = ?, updated_at = ?, applied_at = ? WHERE job_key = ?",
                (ApplicationStatus.APPLIED.value, notes, applied_at.isoformat(), applied_at.isoformat(), job_key),
            )

    def update_status(self, job_key: str, status: ApplicationStatus, notes: str | None, updated_at: datetime) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE job_applications SET status = ?, notes = ?, updated_at = ? WHERE job_key = ?",
                (status.value, notes, updated_at.isoformat(), job_key),
            )

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

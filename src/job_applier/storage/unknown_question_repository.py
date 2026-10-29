import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.job_application import UnknownQuestion
from job_applier.storage.database import Database


class UnknownQuestionRepository(ABC):
    """Perguntas de formulário sem resposta conhecida, acumuladas para o usuário responder."""

    @abstractmethod
    def register(self, question: str, application_id: int | None, seen_at: datetime) -> None:
        """Registra a pergunta; se já existir (ignorando maiúsculas e acentos), soma uma ocorrência."""

    @abstractmethod
    def list_all(self) -> list[UnknownQuestion]:
        """Todas as perguntas, das mais frequentes para as menos frequentes."""


class SqliteUnknownQuestionRepository(UnknownQuestionRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    def register(self, question: str, application_id: int | None, seen_at: datetime) -> None:
        text = " ".join(question.split())
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO unknown_questions (
                    question_key, question, occurrences, last_application_id, first_seen_at, last_seen_at
                ) VALUES (:key, :question, 1, :application_id, :seen_at, :seen_at)
                ON CONFLICT (question_key) DO UPDATE SET
                    occurrences = occurrences + 1,
                    last_application_id = excluded.last_application_id,
                    last_seen_at = excluded.last_seen_at
                """,
                {
                    "key": TextNormalizer.normalize(text),
                    "question": text,
                    "application_id": application_id,
                    "seen_at": seen_at.isoformat(),
                },
            )

    def list_all(self) -> list[UnknownQuestion]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT question.id, question.question, question.occurrences,
                       question.first_seen_at, question.last_seen_at,
                       application.company AS last_company, application.title AS last_title
                FROM unknown_questions AS question
                LEFT JOIN job_applications AS application ON application.id = question.last_application_id
                ORDER BY question.occurrences DESC, question.last_seen_at DESC
                """
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> UnknownQuestion:
        return UnknownQuestion.model_validate(dict(row))

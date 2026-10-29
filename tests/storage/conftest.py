from datetime import datetime

import pytest

from job_applier.models.job_application import JobApplication
from job_applier.storage.application_repository import SqliteApplicationRepository
from job_applier.storage.database import Database
from job_applier.storage.unknown_question_repository import SqliteUnknownQuestionRepository

MOMENT = datetime(2026, 10, 29, 10, 30)


def application(**changes) -> JobApplication:
    defaults = {
        "job_key": "https://www.linkedin.com/jobs/view/1/",
        "company": "Empresa X",
        "title": "Dev Júnior",
        "location": "São Paulo",
        "url": "https://www.linkedin.com/jobs/view/1/",
        "locale": "pt",
        "focus": "dev",
        "is_support_role": False,
        "fit_percentage": 75,
        "matched_terms": ("Python", "Docker"),
        "missing_terms": ("Java",),
        "resume_path": "data/cvs/2026-10-29_Empresa-X_Dev-Junior.pdf",
        "created_at": MOMENT,
        "updated_at": MOMENT,
    }
    return JobApplication(**{**defaults, **changes})


@pytest.fixture
def database(tmp_path) -> Database:
    return Database(tmp_path / "data" / "job_applier.db")


@pytest.fixture
def applications(database) -> SqliteApplicationRepository:
    return SqliteApplicationRepository(database)


@pytest.fixture
def questions(database) -> SqliteUnknownQuestionRepository:
    return SqliteUnknownQuestionRepository(database)

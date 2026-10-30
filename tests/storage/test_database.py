import sqlite3

from job_applier.models.job_application import ApplicationStatus
from job_applier.storage.application_repository import SqliteApplicationRepository
from job_applier.storage.database import Database

VERSION_1_SCHEMA = """
CREATE TABLE job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job_key TEXT NOT NULL UNIQUE, company TEXT NOT NULL,
    title TEXT NOT NULL, location TEXT, url TEXT, locale TEXT NOT NULL, focus TEXT NOT NULL,
    is_support_role INTEGER NOT NULL, fit_percentage INTEGER NOT NULL, matched_terms TEXT NOT NULL,
    missing_terms TEXT NOT NULL, resume_path TEXT NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE unknown_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, question_key TEXT NOT NULL UNIQUE, question TEXT NOT NULL,
    occurrences INTEGER NOT NULL, last_application_id INTEGER REFERENCES job_applications(id),
    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
);
INSERT INTO job_applications VALUES (
    7, 'chave', 'Empresa', 'Dev', NULL, NULL, 'pt', 'dev', 0, 80, '["Python"]', '[]',
    'data/cvs/cv.pdf', 'cv_gerado', '2026-10-29T10:00:00', '2026-10-29T10:00:00'
);
"""

VERSION_2_SCHEMA = """
CREATE TABLE job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job_key TEXT NOT NULL UNIQUE, company TEXT NOT NULL,
    title TEXT NOT NULL, location TEXT, url TEXT, description TEXT, locale TEXT NOT NULL, focus TEXT NOT NULL,
    is_support_role INTEGER NOT NULL, fit_percentage INTEGER NOT NULL, matched_terms TEXT NOT NULL,
    missing_terms TEXT NOT NULL, resume_path TEXT, apply_type TEXT, applicants INTEGER, posted_on TEXT,
    status TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
INSERT INTO job_applications (
    job_key, company, title, locale, focus, is_support_role, fit_percentage, matched_terms, missing_terms,
    apply_type, status, created_at, updated_at
)
VALUES
    ('externa', 'A', 'Dev', 'pt', 'dev', 0, 80, '[]', '[]', 'site_externo', 'cv_gerado', '2026-10-29', '2026-10-29'),
    ('ignorada', 'B', 'Dev', 'pt', 'dev', 0, 80, '[]', '[]', 'site_externo', 'ignorada', '2026-10-29', '2026-10-29'),
    ('simples', 'C', 'Dev', 'pt', 'dev', 0, 80, '[]', '[]', 'candidatura_simplificada', 'cv_gerado',
     '2026-10-29', '2026-10-29');
PRAGMA user_version = 2;
"""


class TestDatabase:
    def test_new_database_is_created_at_the_latest_version(self, tmp_path):
        database = Database(tmp_path / "novo.db")

        with database.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

        assert version == 3
        assert {"job_applications", "unknown_questions", "scan_runs"} <= tables

    def test_migrates_a_version_1_database_keeping_its_data(self, tmp_path):
        path = tmp_path / "antigo.db"
        with sqlite3.connect(path) as connection:
            connection.executescript(VERSION_1_SCHEMA)

        [migrated] = SqliteApplicationRepository(Database(path)).list_all()

        assert (migrated.id, migrated.job_key, migrated.resume_path) == (7, "chave", "data/cvs/cv.pdf")
        assert migrated.notes is None and migrated.applicants is None

    def test_migration_allows_jobs_without_resume(self, tmp_path):
        path = tmp_path / "antigo.db"
        with sqlite3.connect(path) as connection:
            connection.executescript(VERSION_1_SCHEMA)
        database = Database(path)

        with database.connect() as connection:
            connection.execute("UPDATE job_applications SET resume_path = NULL WHERE id = 7")
            resume_path = connection.execute("SELECT resume_path FROM job_applications").fetchone()[0]

        assert resume_path is None

    def test_migration_marks_only_external_jobs_with_resume_as_pending(self, tmp_path):
        path = tmp_path / "antigo.db"
        with sqlite3.connect(path) as connection:
            connection.executescript(VERSION_2_SCHEMA)

        migrated = {item.job_key: item for item in SqliteApplicationRepository(Database(path)).list_all()}

        assert migrated["externa"].status is ApplicationStatus.MANUAL_APPLICATION_PENDING
        assert migrated["ignorada"].status is ApplicationStatus.SKIPPED
        assert migrated["simples"].status is ApplicationStatus.CV_GENERATED
        assert migrated["externa"].external_apply_url is None

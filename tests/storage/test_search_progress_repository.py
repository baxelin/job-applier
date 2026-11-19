from datetime import datetime

from job_applier.storage.search_progress_repository import SqliteSearchProgressRepository


class TestSqliteSearchProgressRepository:
    def test_remembers_the_last_completion_of_each_search(self, database):
        progress = SqliteSearchProgressRepository(database)

        progress.mark_completed("dev|SP", datetime(2026, 11, 18, 9, 0))
        progress.mark_completed("dev|SP", datetime(2026, 11, 19, 9, 0))

        assert progress.last_completed("dev|SP") == datetime(2026, 11, 19, 9, 0)
        assert progress.last_completed("estagio|SP") is None

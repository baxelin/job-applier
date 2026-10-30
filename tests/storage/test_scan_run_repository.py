from datetime import datetime

from job_applier.models.job_application import ScanRun, ScanStatus
from job_applier.storage.scan_run_repository import SqliteScanRunRepository


class TestSqliteScanRunRepository:
    def test_creates_then_finishes_a_run(self, database):
        runs = SqliteScanRunRepository(database)

        started = runs.save(ScanRun(started_at=datetime(2026, 10, 29, 9, 0)))
        runs.save(
            started.model_copy(
                update={
                    "finished_at": datetime(2026, 10, 29, 9, 40),
                    "status": ScanStatus.STOPPED,
                    "reason": "Captcha",
                    "jobs_seen": 5,
                    "jobs_recorded": 4,
                }
            )
        )

        [run] = runs.list_recent(10)
        assert run.id == started.id
        assert (run.status, run.reason, run.jobs_seen, run.jobs_recorded) == (ScanStatus.STOPPED, "Captcha", 5, 4)

    def test_lists_most_recent_first_up_to_the_limit(self, database):
        runs = SqliteScanRunRepository(database)
        for hour in (8, 9, 10):
            runs.save(ScanRun(started_at=datetime(2026, 10, 29, hour, 0)))

        assert [run.started_at.hour for run in runs.list_recent(2)] == [10, 9]

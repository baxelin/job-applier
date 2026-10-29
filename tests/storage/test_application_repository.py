from datetime import datetime

from job_applier.models.job_application import ApplicationStatus
from tests.storage.conftest import MOMENT, application


class TestSqliteApplicationRepository:
    def test_creates_database_file_and_saves_application(self, applications, tmp_path):
        saved = applications.save(application())

        assert (tmp_path / "data" / "job_applier.db").exists()
        assert saved.id is not None
        assert saved.model_dump(exclude={"id"}) == application().model_dump(exclude={"id"})

    def test_same_job_updates_the_existing_record(self, applications):
        first = applications.save(application())
        later = datetime(2026, 11, 2, 9, 0)

        updated = applications.save(application(fit_percentage=90, updated_at=later, created_at=later))

        assert updated.id == first.id
        assert updated.fit_percentage == 90
        assert updated.updated_at == later
        assert updated.created_at == MOMENT
        assert len(applications.list_all()) == 1

    def test_update_keeps_the_application_status(self, applications, database):
        saved = applications.save(application())
        with database.connect() as connection:
            connection.execute("UPDATE job_applications SET status = 'candidatura_enviada' WHERE id = ?", (saved.id,))

        updated = applications.save(application(fit_percentage=10))

        assert updated.status is ApplicationStatus.APPLIED

    def test_lists_most_recent_first(self, applications):
        applications.save(application(job_key="antiga", created_at=datetime(2026, 1, 1)))
        applications.save(application(job_key="nova", created_at=datetime(2026, 6, 1)))

        assert [item.job_key for item in applications.list_all()] == ["nova", "antiga"]

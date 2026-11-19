from datetime import datetime

import pytest

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

    def test_update_status_changes_status_and_notes(self, applications):
        applications.save(application())
        later = datetime(2026, 11, 2, 9, 0)

        applications.update_status(application().job_key, ApplicationStatus.REHEARSED, "Tudo certo", later)

        saved = applications.list_all()[0]
        assert (saved.status, saved.notes, saved.updated_at) == (ApplicationStatus.REHEARSED, "Tudo certo", later)
        assert saved.created_at == MOMENT


def easy_apply(job_key: str, fit: int = 50, status: ApplicationStatus = ApplicationStatus.CV_GENERATED, **changes):
    return application(
        job_key=job_key, fit_percentage=fit, status=status, apply_type="candidatura_simplificada", **changes
    )


class TestHasCompanyAndTitle:
    def test_finds_the_same_job_ignoring_case_accents_and_spaces(self, applications):
        applications.save(application(company="INDI Staffing", title="Junior .NET Developer - Remote Work"))

        assert applications.has_company_and_title("indi staffing", "Junior  .NET developer - remote work")

    def test_same_title_in_another_company_is_a_different_job(self, applications):
        applications.save(application(company="Empresa X", title="Desenvolvedor Júnior"))

        assert not applications.has_company_and_title("Empresa Y", "Desenvolvedor Júnior")


class TestListReadyForEasyApply:
    def test_lists_only_easy_apply_jobs_with_resume(self, applications):
        applications.save(easy_apply("simplificada"))
        applications.save(application(job_key="externa", apply_type="site_externo"))
        applications.save(easy_apply("sem-cv", resume_path=None))

        assert [item.job_key for item in applications.list_ready_for_easy_apply()] == ["simplificada"]

    @pytest.mark.parametrize(
        "status",
        [ApplicationStatus.REHEARSED, ApplicationStatus.APPLIED, ApplicationStatus.SKIPPED],
    )
    def test_leaves_out_jobs_that_do_not_need_a_new_attempt(self, applications, status):
        applications.save(easy_apply("vaga", status=status))

        assert applications.list_ready_for_easy_apply() == []

    def test_lists_only_new_jobs_by_default(self, applications):
        applications.save(easy_apply("pendente", fit=100, status=ApplicationStatus.UNKNOWN_QUESTION_PENDING))
        applications.save(easy_apply("erro", fit=90, status=ApplicationStatus.FAILED))
        applications.save(easy_apply("nova", fit=10))

        assert [item.job_key for item in applications.list_ready_for_easy_apply()] == ["nova"]

    def test_retries_pending_and_failed_jobs_after_the_new_ones_when_asked(self, applications):
        applications.save(easy_apply("pendente", fit=100, status=ApplicationStatus.UNKNOWN_QUESTION_PENDING))
        applications.save(easy_apply("erro", fit=90, status=ApplicationStatus.FAILED))
        applications.save(easy_apply("nova", fit=10))

        listed = applications.list_ready_for_easy_apply(retry_pending=True)

        assert [item.job_key for item in listed] == ["nova", "pendente", "erro"]

    def test_orders_by_fit_and_respects_the_limit(self, applications):
        applications.save(easy_apply("baixa", fit=20))
        applications.save(easy_apply("alta", fit=90))
        applications.save(easy_apply("media", fit=50))

        assert [item.job_key for item in applications.list_ready_for_easy_apply(2)] == ["alta", "media"]

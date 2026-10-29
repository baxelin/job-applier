from job_applier.models.job_description import JobDescription


class TestJobDescription:
    def test_key_is_the_link_when_available(self):
        job = JobDescription(company="X", title="Dev", text="...", url="https://www.linkedin.com/jobs/view/1/")

        assert job.key() == "https://www.linkedin.com/jobs/view/1/"

    def test_key_ignores_case_and_accents_without_link(self):
        first = JobDescription(company="Itaú", title="Dev Júnior", text="...")
        second = JobDescription(company="ITAU", title="dev junior", text="outra descrição")

        assert first.key() == second.key()

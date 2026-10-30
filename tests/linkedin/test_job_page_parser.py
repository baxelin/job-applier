from datetime import date

import pytest

from job_applier.linkedin.job_page_parser import JobExtractionError, JobPageParser
from job_applier.models.job_posting import ApplyType
from tests.linkedin.pages import current_job_page, job_page

TODAY = date(2026, 10, 29)


def parse(html: str):
    return JobPageParser().parse(html, "123", TODAY)


class TestCurrentLayout:
    def test_reads_title_and_company_from_stable_anchors(self):
        job = parse(current_job_page()).description

        assert (job.title, job.company) == ("Desenvolvedor Front-end Junior | Remoto", "Jungle Gaming")

    def test_reads_location_date_and_applicants_from_the_top_line_not_from_similar_jobs(self):
        posting = parse(current_job_page())

        assert posting.description.location == "Brasil"
        assert posting.posted_on == date(2026, 10, 26)
        assert posting.applicants == 100

    def test_reads_description_without_the_expand_button(self):
        description = parse(current_job_page()).description.text

        assert description.splitlines() == [
            "A Jungle Gaming cria jogos. Procuramos pessoa com React e TypeScript.",
            "Requisitos:",
            "Git",
        ]

    def test_detects_external_application_by_aria_label(self):
        assert parse(current_job_page()).apply_type is ApplyType.EXTERNAL

    def test_detects_easy_apply_by_aria_label(self):
        html = current_job_page(apply_label="Candidatura simplificada à vaga de Desenvolvedor")

        assert parse(html).apply_type is ApplyType.EASY_APPLY


class TestJobPageParser:
    def test_extracts_job_fields(self):
        posting = parse(job_page())

        job = posting.description
        assert (job.title, job.company, job.location) == ("Desenvolvedor Python Júnior", "Empresa X", "São Paulo, SP")
        assert str(job.url) == "https://www.linkedin.com/jobs/view/123/"
        assert posting.applicants == 37
        assert posting.posted_on == date(2026, 10, 27)

    def test_keeps_description_line_breaks(self):
        description = parse(job_page()).description.text

        assert description.splitlines() == ["Sobre a vaga", "Buscamos pessoa com Python e Docker.", "Git"]

    def test_detects_easy_apply(self):
        assert parse(job_page()).apply_type is ApplyType.EASY_APPLY

    def test_detects_external_application(self):
        button = '<button class="jobs-apply-button" aria-label="Candidatar-se no site da empresa">Candidatar-se</button>'

        assert parse(job_page(apply_button=button)).apply_type is ApplyType.EXTERNAL

    def test_detects_closed_job(self):
        closed = job_page(apply_button="", extra="<div>Não aceita mais candidaturas</div>")

        assert parse(closed).apply_type is ApplyType.CLOSED

    def test_unknown_apply_type_without_button(self):
        assert parse(job_page(apply_button="")).apply_type is ApplyType.UNKNOWN

    def test_reads_guest_layout(self):
        html = """
        <html><body>
          <h1 class="top-card-layout__title">Junior Developer</h1>
          <a class="topcard__org-name-link" href="/company/y">Empresa Y</a>
          <div class="topcard__flavor-row">Remote · 2 days ago · Over 100 applicants</div>
          <div class="show-more-less-html__markup">We use Python.</div>
        </body></html>
        """

        posting = parse(html)

        assert (posting.description.title, posting.description.company) == ("Junior Developer", "Empresa Y")
        assert posting.applicants == 100

    def test_reports_missing_required_fields(self):
        with pytest.raises(JobExtractionError, match="empresa, descrição"):
            parse("<html><body><h1>Só o título</h1></body></html>")

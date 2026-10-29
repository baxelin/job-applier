from datetime import date

import pytest

from job_applier.models.base import Locale
from job_applier.models.job_description import JobDescription
from job_applier.models.resume import Contact
from job_applier.resume.resume_file_namer import ResumeFileNamer

CONTACT = Contact(
    full_name="Lucas de Souza Baccelli",
    email="pessoa@example.com",
    phone="+55 11 90000-0000",
    location="São Paulo, SP",
    linkedin_url="https://www.linkedin.com/in/pessoa",
    github_url="https://github.com/pessoa",
)


class TestResumeFileNamer:
    @pytest.mark.parametrize(
        ("locale", "expected"),
        [(Locale.PT, "Curriculo_Lucas_Baccelli.pdf"), (Locale.EN, "Resume_Lucas_Baccelli.pdf")],
    )
    def test_upload_name_is_neutral(self, locale, expected):
        assert ResumeFileNamer().upload_name(CONTACT, locale) == expected

    def test_archive_name_identifies_date_company_and_job(self):
        job = JobDescription(company="Itaú Unibanco", title="Desenvolvedor(a) Python Júnior", text="...")

        name = ResumeFileNamer().archive_name(job, date(2026, 10, 29))

        assert name == "2026-10-29_Itau-Unibanco_Desenvolvedor-a-Python-Junior.pdf"

    def test_archive_name_limits_long_titles(self):
        job = JobDescription(company="Empresa", title="Desenvolvedor " * 20, text="...")

        title_part = ResumeFileNamer().archive_name(job, date(2026, 1, 1)).split("_")[2]

        assert len(title_part.removesuffix(".pdf")) <= 60

import pytest

from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.models.base import Locale
from job_applier.models.resume import Period
from job_applier.resume.html_resume_renderer import HtmlResumeRenderer
from job_applier.resume.resume_labels import ResumeLabels
from job_applier.resume.resume_tailor import ResumeTailor


def render(tailoring_resume, tailoring_glossary, resume_settings, locale: Locale) -> str:
    tailored = ResumeTailor(tailoring_resume, tailoring_glossary, resume_settings).tailor(
        JobAnalysis({"python": 1}, frozenset({Area.DEV}), locale)
    )
    return HtmlResumeRenderer().render(tailored)


class TestResumeLabels:
    @pytest.mark.parametrize(
        ("locale", "expected"), [(Locale.PT, "Abr 2025 - Jul 2026"), (Locale.EN, "Apr 2025 - Jul 2026")]
    )
    def test_formats_period(self, locale, expected):
        assert ResumeLabels(locale).period(Period(start="2025-04", end="2026-07")) == expected

    @pytest.mark.parametrize(("locale", "expected"), [(Locale.PT, "Fev 2026 - Atual"), (Locale.EN, "Feb 2026 - Present")])
    def test_formats_ongoing_period(self, locale, expected):
        assert ResumeLabels(locale).period(Period(start="2026-02")) == expected


class TestHtmlResumeRenderer:
    def test_renders_portuguese_resume_in_the_original_layout(self, tailoring_resume, tailoring_glossary, resume_settings):
        html = render(tailoring_resume, tailoring_glossary, resume_settings, Locale.PT)

        assert "PESSOA TESTE" in html
        assert "RESUMO" in html and "EXPERIÊNCIAS" in html and "INFORMAÇÕES ADICIONAIS" in html
        assert "Suporte em TI | <span class=\"company\">Empresa A</span>" in html
        assert "Automação de rotinas com Python" in html
        assert "linkedin.com/in/pessoa-teste" in html

    def test_renders_english_resume(self, tailoring_resume, tailoring_glossary, resume_settings):
        html = render(tailoring_resume, tailoring_glossary, resume_settings, Locale.EN)

        assert "SUMMARY" in html and "EXPERIENCE" in html
        assert "Automação de rotinas com Python (en)" in html
        assert "Apr 2025 - Jul 2026" in html

    def test_shows_website_only_when_defined(self, tailoring_resume, tailoring_glossary, resume_settings):
        without_website = render(tailoring_resume, tailoring_glossary, resume_settings, Locale.PT)
        resume = tailoring_resume.model_copy(
            update={
                "contact": tailoring_resume.contact.model_copy(update={"website_url": "https://pessoa.vercel.app"})
            }
        )

        with_website = render(resume, tailoring_glossary, resume_settings, Locale.PT)

        assert "Portfólio:" not in without_website
        assert "<strong>Portfólio:</strong>" in with_website and ">pessoa.vercel.app</a>" in with_website

    def test_escapes_html_from_data(self, tailoring_resume, tailoring_glossary, resume_settings):
        resume = tailoring_resume.model_copy(
            update={"contact": tailoring_resume.contact.model_copy(update={"location": "<b>SP</b>"})}
        )

        html = render(resume, tailoring_glossary, resume_settings, Locale.PT)

        assert "&lt;b&gt;SP&lt;/b&gt;" in html

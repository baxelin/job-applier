import pytest

from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.models.base import LocalizedText, Locale
from job_applier.resume.resume_tailor import ResumeTailor


@pytest.fixture
def tailor(tailoring_resume, tailoring_glossary, resume_settings) -> ResumeTailor:
    return ResumeTailor(tailoring_resume, tailoring_glossary, resume_settings)


def analysis(focus: set[Area], term_weights: dict[str, int] | None = None, locale: Locale = Locale.PT) -> JobAnalysis:
    return JobAnalysis(term_weights or {}, frozenset(focus), locale)


def bullet_texts(experience) -> list[str]:
    return [bullet.text.pt for bullet in experience.bullets]


class TestSummarySelection:
    @pytest.mark.parametrize(
        ("focus", "expected"),
        [({Area.DEV}, "dev-junior"), ({Area.DEVOPS}, "devops-junior"), ({Area.DEV, Area.DEVOPS}, "dev-devops")],
    )
    def test_picks_summary_matching_the_focus(self, tailor, focus, expected):
        assert tailor.tailor(analysis(focus)).summary.id == expected


class TestSummaryText:
    def test_summary_cites_the_skills_most_relevant_to_the_job(self, tailoring_resume, tailoring_glossary, resume_settings):
        dev_summary = tailoring_resume.summaries[0].model_copy(
            update={"text": LocalizedText(pt="Trabalho com {stack}.", en="I work with {stack}.")}
        )
        resume = tailoring_resume.model_copy(update={"summaries": [dev_summary, *tailoring_resume.summaries[1:]]})
        tailor = ResumeTailor(resume, tailoring_glossary, resume_settings)

        tailored = tailor.tailor(analysis({Area.DEV}, {"docker": 3}))

        assert tailored.summary_text == "Trabalho com Docker e Python."

    def test_summary_skips_tools_practices_and_support_skills(
        self, tailoring_resume, tailoring_glossary, resume_settings
    ):
        dev_summary = tailoring_resume.summaries[0].model_copy(
            update={"text": LocalizedText(pt="Trabalho com {stack}.", en="I work with {stack}.")}
        )
        glossary = tailoring_glossary.model_copy(
            update={
                "terms": [
                    term.model_copy(update={"category": "tool"}) if term.id == "docker" else term
                    for term in tailoring_glossary.terms
                ]
            }
        )
        resume = tailoring_resume.model_copy(update={"summaries": [dev_summary, *tailoring_resume.summaries[1:]]})

        tailored = ResumeTailor(resume, glossary, resume_settings).tailor(analysis({Area.DEV}, {"docker": 3}))

        assert tailored.summary_text == "Trabalho com Python e React."
        assert tailored.skills[0] == "Docker"


class TestBulletSelection:
    def test_orders_bullets_by_relevance_and_respects_maximum(self, tailor):
        resume = tailor.tailor(analysis({Area.DEV}, {"python": 1}))

        assert bullet_texts(resume.experiences[0]) == ["Automação de rotinas com Python"]

    def test_follows_the_job_focus(self, tailor):
        resume = tailor.tailor(analysis({Area.DEVOPS}, {"docker": 2}))

        assert bullet_texts(resume.experiences[0])[0] == "Implantação de servidores com Docker"

    def test_keeps_every_experience_with_its_minimum_of_bullets(self, tailor):
        resume = tailor.tailor(analysis({Area.DEV}))

        assert [len(item.bullets) for item in resume.experiences] == [1, 1]
        assert bullet_texts(resume.experiences[1]) == ["Atendimento ao público"]

    def test_never_shows_support_only_bullets_beyond_the_minimum(self, tailor):
        resume = tailor.tailor(analysis({Area.DEV, Area.DEVOPS}))

        assert "Atendimento a usuários" not in bullet_texts(resume.experiences[0])


class TestProjectsAndSkills:
    def test_keeps_only_the_most_relevant_projects(self, tailor):
        resume = tailor.tailor(analysis({Area.DEV}, {"python": 1}))

        assert [item.project.name for item in resume.projects] == ["api-python"]

    def test_ranks_skills_by_job_terms_and_hides_support_skills(self, tailor):
        resume = tailor.tailor(analysis({Area.DEV}, {"docker": 3}))

        assert resume.skills == ("Docker", "Python", "React")

    def test_uses_job_locale(self, tailor):
        assert tailor.tailor(analysis({Area.DEV}, locale=Locale.EN)).locale is Locale.EN

    def test_skill_names_follow_job_locale(self, tailoring_resume, tailoring_glossary, resume_settings):
        glossary = tailoring_glossary.model_copy(
            update={
                "terms": [
                    term.model_copy(update={"name_en": "Python (en)"}) if term.id == "python" else term
                    for term in tailoring_glossary.terms
                ]
            }
        )
        tailor = ResumeTailor(tailoring_resume, glossary, resume_settings)

        assert "Python (en)" in tailor.tailor(analysis({Area.DEV}, locale=Locale.EN)).skills
        assert "Python" in tailor.tailor(analysis({Area.DEV}, locale=Locale.PT)).skills

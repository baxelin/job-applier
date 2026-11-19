import pytest

from job_applier.answering.skill_experience import SkillExperience
from job_applier.models.answer_book import SkillYearsRule
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume


@pytest.fixture
def make_experience(resume_data, glossary_data):
    glossary_data["terms"] += [
        {"id": "django", "name": "Django", "category": "backend", "related_to": ["python"]},
        {"id": "spring", "name": "Spring", "category": "backend", "related_to": ["java"]},
        {"id": "java", "name": "Java", "category": "language"},
    ]

    def build(related_years: float | None = 1) -> SkillExperience:
        rule = SkillYearsRule(patterns=["anos"], default_years=0, related_years=related_years)
        return SkillExperience(Resume.model_validate(resume_data), Glossary.model_validate(glossary_data), rule)

    return build


class TestSkillExperience:
    def test_skill_of_the_resume_uses_its_years(self, make_experience):
        experience = make_experience()

        assert (experience.knows("python"), experience.years("python")) == (True, 1)

    def test_skill_derived_from_the_resume_uses_the_related_years(self, make_experience):
        experience = make_experience(related_years=0.5)

        assert (experience.knows("django"), experience.years("django")) == (True, 0.5)

    def test_skill_derived_from_something_outside_the_resume_is_unknown(self, make_experience):
        experience = make_experience()

        assert (experience.knows("spring"), experience.years("spring")) == (False, 0)

    def test_without_related_years_derived_skills_are_unknown(self, make_experience):
        experience = make_experience(related_years=None)

        assert (experience.knows("django"), experience.years("django")) == (False, 0)

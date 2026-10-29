import pytest
from pydantic import ValidationError

from job_applier.models.resume import Period, Resume


class TestPeriod:
    def test_accepts_period_without_end(self):
        assert Period(start="2024-01").end is None

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="anterior ao início"):
            Period(start="2025-01", end="2024-12")

    @pytest.mark.parametrize("value", ["2024-13", "2024-1", "jan/2024"])
    def test_rejects_invalid_year_month(self, value):
        with pytest.raises(ValidationError):
            Period(start=value)


class TestResume:
    def test_accepts_valid_data(self, resume_data):
        resume = Resume.model_validate(resume_data)

        assert resume.skill_terms() == {"python"}

    def test_requires_at_least_two_summaries(self, resume_data):
        resume_data["summaries"] = resume_data["summaries"][:1]

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

    def test_allows_at_most_four_summaries(self, resume_data):
        resume_data["summaries"] = [
            {"id": f"resumo-{index}", "tags": ["dev"], "text": {"pt": "Texto.", "en": "Text."}} for index in range(5)
        ]

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

    def test_rejects_duplicated_skills(self, resume_data):
        resume_data["skills"].append({"term": "python", "years": 2, "tags": ["dev"]})

        with pytest.raises(ValidationError, match="Skills repetidos: python"):
            Resume.model_validate(resume_data)

    def test_rejects_bullet_without_tags(self, resume_data):
        resume_data["experiences"][0]["bullets"][0]["tags"] = []

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

    @pytest.mark.parametrize("tag", ["Dev", "dev ops", "dev_ops", "-dev"])
    def test_rejects_tag_outside_slug_format(self, resume_data, tag):
        resume_data["skills"][0]["tags"] = [tag]

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

    def test_requires_english_version_of_texts(self, resume_data):
        resume_data["experiences"][0]["bullets"][0]["text"] = {"pt": "Só em português."}

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

    def test_rejects_unknown_fields(self, resume_data):
        resume_data["contact"]["nome"] = "Campo digitado errado"

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

    def test_rejects_negative_years(self, resume_data):
        resume_data["skills"][0]["years"] = -1

        with pytest.raises(ValidationError):
            Resume.model_validate(resume_data)

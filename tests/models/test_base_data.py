import pytest
from pydantic import ValidationError

from job_applier.models.base_data import BaseData


class TestBaseData:
    def test_accepts_skills_present_in_glossary(self, resume_data, glossary_data, answer_book_data, settings_data):
        base_data = BaseData.model_validate(
            {
                "resume": resume_data,
                "glossary": glossary_data,
                "answer_book": answer_book_data,
                "settings": settings_data,
            }
        )

        assert "1 skills" in base_data.describe()

    def test_rejects_skill_missing_from_glossary(self, resume_data, glossary_data, answer_book_data, settings_data):
        resume_data["skills"].append({"term": "cobol", "years": 1, "tags": ["dev"]})

        with pytest.raises(ValidationError, match="sem termo correspondente no glossário: cobol"):
            BaseData.model_validate(
                {
                    "resume": resume_data,
                    "glossary": glossary_data,
                    "answer_book": answer_book_data,
                    "settings": settings_data,
                }
            )

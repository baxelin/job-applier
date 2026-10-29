import pytest
from pydantic import ValidationError

from job_applier.models.base import Locale
from job_applier.models.glossary import Glossary


class TestGlossary:
    def test_accepts_valid_data(self, glossary_data):
        glossary = Glossary.model_validate(glossary_data)

        assert glossary.term_ids() == {"python", "docker"}

    def test_rejects_duplicated_ids(self, glossary_data):
        glossary_data["terms"].append({"id": "python", "name": "Outro", "category": "language"})

        with pytest.raises(ValidationError, match="Ids de termos repetidos: python"):
            Glossary.model_validate(glossary_data)

    def test_rejects_synonym_used_by_another_term_ignoring_case(self, glossary_data):
        glossary_data["terms"][1]["synonyms"] = ["PY"]

        with pytest.raises(ValidationError, match="Nomes/sinônimos de termos repetidos: py"):
            Glossary.model_validate(glossary_data)

    def test_display_name_uses_english_name_only_when_defined(self, glossary_data):
        glossary_data["terms"][0]["name_en"] = "Python (en)"

        names = Glossary.model_validate(glossary_data)

        assert names.display_names(Locale.EN) == {"python": "Python (en)", "docker": "Docker"}
        assert names.display_names(Locale.PT) == {"python": "Python", "docker": "Docker"}

    def test_english_name_counts_as_a_name_for_uniqueness(self, glossary_data):
        glossary_data["terms"][0]["name_en"] = "Docker"

        with pytest.raises(ValidationError, match="repetidos: docker"):
            Glossary.model_validate(glossary_data)

    def test_rejects_unknown_category(self, glossary_data):
        glossary_data["terms"][0]["category"] = "linguagem"

        with pytest.raises(ValidationError):
            Glossary.model_validate(glossary_data)

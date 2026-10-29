import pytest

from job_applier.matching.keyword_extractor import KeywordExtractor
from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.glossary import Glossary


@pytest.fixture
def extractor() -> KeywordExtractor:
    return KeywordExtractor(
        Glossary.model_validate(
            {
                "terms": [
                    {"id": "python", "name": "Python", "category": "language"},
                    {"id": "javascript", "name": "JavaScript", "category": "language", "synonyms": ["js"]},
                    {"id": "nodejs", "name": "Node.js", "category": "backend", "synonyms": ["node"]},
                    {"id": "c", "name": "C", "category": "language"},
                    {"id": "cpp", "name": "C++", "category": "language"},
                    {"id": "csharp", "name": "C#", "category": "language"},
                    {"id": "ci-cd", "name": "CI/CD", "category": "devops", "synonyms": ["integração contínua"]},
                ]
            }
        )
    )


class TestTextNormalizer:
    def test_removes_accents_and_case(self):
        assert TextNormalizer.normalize("Integração CONTÍNUA") == "integracao continua"


class TestKeywordExtractor:
    def test_counts_name_and_synonym_occurrences(self, extractor):
        found = extractor.extract("JavaScript no front e JS no back. Python é diferencial.")

        assert found == {"javascript": 2, "python": 1}

    def test_ignores_accents_and_case(self, extractor):
        assert extractor.extract("Experiência com INTEGRACAO CONTINUA") == {"ci-cd": 1}

    def test_does_not_find_short_terms_inside_longer_ones(self, extractor):
        found = extractor.extract("Experiência com C++, C# e Node.js")

        assert found == {"cpp": 1, "csharp": 1, "nodejs": 1}

    def test_does_not_find_terms_inside_words(self, extractor):
        assert extractor.extract("Pythonic, ecossistema jsx e nodes") == {}

    def test_finds_terms_next_to_punctuation(self, extractor):
        assert extractor.extract("(Python), C/C++.") == {"python": 1, "c": 1, "cpp": 1}

from job_applier.matching.language_detector import LanguageDetector
from job_applier.models.base import Locale


class TestLanguageDetector:
    def test_detects_portuguese(self):
        text = "Buscamos uma pessoa com experiência em Python para atuar no time de dados."

        assert LanguageDetector().detect(text) is Locale.PT

    def test_detects_portuguese_from_portugal(self):
        text = "Procuramos um programador com conhecimentos de Java para integrar a nossa equipa em Lisboa."

        assert LanguageDetector().detect(text) is Locale.PT

    def test_detects_english(self):
        text = "We are looking for a developer with experience in Python and you will work with our team."

        assert LanguageDetector().detect(text) is Locale.EN

    def test_prefers_portuguese_when_undecided(self):
        assert LanguageDetector().detect("Python Docker AWS") is Locale.PT

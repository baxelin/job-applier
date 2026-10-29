import re
from collections.abc import Mapping

from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.matching.keyword_extractor import KeywordExtractor
from job_applier.matching.language_detector import LanguageDetector
from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.glossary import Glossary, TermCategory
from job_applier.models.job_description import JobDescription


class JobAnalyzer:
    """Transforma a descrição de uma vaga em uma JobAnalysis.

    O foco (dev, devops ou ambos) vem das categorias dos termos encontrados, com bônus para
    palavras do título. Se as duas áreas tiverem pesos próximos, o foco é misto.
    """

    _DEV_CATEGORIES = frozenset(
        {TermCategory.LANGUAGE, TermCategory.FRONTEND, TermCategory.BACKEND, TermCategory.DATA, TermCategory.TESTING}
    )
    _DEVOPS_CATEGORIES = frozenset({TermCategory.DEVOPS, TermCategory.CLOUD})
    _DEV_TITLE_WORDS = ("desenvolvedor", "desenvolvedora", "developer", "programador", "programadora",
                        "software", "front", "back", "full", "web", "mobile")
    _DEVOPS_TITLE_WORDS = ("devops", "sre", "cloud", "infra", "platform", "plataforma", "site reliability")
    _TITLE_BONUS = 5
    _SHARED_FOCUS_RATIO = 0.5

    def __init__(
        self,
        glossary: Glossary,
        keyword_occurrence_cap: int,
        extractor: KeywordExtractor | None = None,
        language_detector: LanguageDetector | None = None,
    ) -> None:
        self._categories = {term.id: term.category for term in glossary.terms}
        self._keyword_occurrence_cap = keyword_occurrence_cap
        self._extractor = extractor or KeywordExtractor(glossary)
        self._language_detector = language_detector or LanguageDetector()

    def analyze(self, job: JobDescription) -> JobAnalysis:
        occurrences = self._extractor.extract(f"{job.title}\n{job.text}")
        weights = {term_id: min(count, self._keyword_occurrence_cap) for term_id, count in occurrences.items()}
        return JobAnalysis(
            term_weights=weights,
            focus=self._focus(job.title, weights),
            locale=self._language_detector.detect(job.text),
        )

    def _focus(self, title: str, weights: Mapping[str, int]) -> frozenset[Area]:
        dev = self._category_score(weights, self._DEV_CATEGORIES) + self._title_bonus(title, self._DEV_TITLE_WORDS)
        devops = self._category_score(weights, self._DEVOPS_CATEGORIES) + self._title_bonus(
            title, self._DEVOPS_TITLE_WORDS
        )

        if dev == devops == 0:
            return frozenset({Area.DEV})
        if min(dev, devops) >= self._SHARED_FOCUS_RATIO * max(dev, devops):
            return frozenset({Area.DEV, Area.DEVOPS})
        return frozenset({Area.DEV if dev > devops else Area.DEVOPS})

    def _category_score(self, weights: Mapping[str, int], categories: frozenset[TermCategory]) -> int:
        return sum(weight for term_id, weight in weights.items() if self._categories[term_id] in categories)

    def _title_bonus(self, title: str, words: tuple[str, ...]) -> int:
        normalized_title = TextNormalizer.normalize(title)
        has_word = any(re.search(rf"\b{re.escape(word)}", normalized_title) for word in words)
        return self._TITLE_BONUS if has_word else 0

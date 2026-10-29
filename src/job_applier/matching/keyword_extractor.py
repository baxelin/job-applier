import re
from collections import Counter

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.glossary import Glossary, Term


class KeywordExtractor:
    """Encontra no texto de uma vaga os termos do glossário, contando quantas vezes cada um aparece.

    Os limites de palavra impedem falsos positivos como "c" dentro de "c++" ou "js" dentro de "node.js".
    """

    _BEFORE_NAME = r"(?<![\w.+#])"
    _AFTER_NAME = r"(?![\w+#])"

    def __init__(self, glossary: Glossary) -> None:
        self._patterns = {term.id: self._compile(term) for term in glossary.terms}

    def extract(self, text: str) -> Counter[str]:
        normalized = TextNormalizer.normalize(text)
        occurrences = Counter[str]()
        for term_id, pattern in self._patterns.items():
            if count := len(pattern.findall(normalized)):
                occurrences[term_id] = count
        return occurrences

    @classmethod
    def _compile(cls, term: Term) -> re.Pattern[str]:
        names = sorted({TextNormalizer.normalize(name) for name in term.normalized_names()}, key=len, reverse=True)
        alternatives = "|".join(re.escape(name) for name in names)
        return re.compile(f"{cls._BEFORE_NAME}(?:{alternatives}){cls._AFTER_NAME}")

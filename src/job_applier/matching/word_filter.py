import re
from collections.abc import Sequence

from job_applier.matching.text_normalizer import TextNormalizer


class WordFilter:
    """Encontra num texto palavras proibidas como palavras inteiras, ignorando maiúsculas e acentos.

    Usado no título da vaga ("Sr." bloqueia "Desenvolvedor Sr.", mas "sr" não bloqueia "SRE")
    e no nome da empresa (blacklist).
    """

    def __init__(self, forbidden_words: Sequence[str]) -> None:
        self._patterns = [
            (word, re.compile(rf"(?<!\w){re.escape(TextNormalizer.normalize(word))}(?!\w)"))
            for word in forbidden_words
        ]

    def first_match_in(self, text: str) -> str | None:
        normalized = TextNormalizer.normalize(text)
        return next((word for word, pattern in self._patterns if pattern.search(normalized)), None)

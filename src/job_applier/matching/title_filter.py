import re
from collections.abc import Sequence

from job_applier.matching.text_normalizer import TextNormalizer


class TitleFilter:
    """Encontra no título da vaga palavras proibidas (sênior, pleno, suporte...) como palavras inteiras.

    "Sr." bloqueia "Desenvolvedor Sr.", mas "sr" não bloqueia "SRE".
    """

    def __init__(self, forbidden_words: Sequence[str]) -> None:
        self._patterns = [
            (word, re.compile(rf"(?<!\w){re.escape(TextNormalizer.normalize(word))}(?!\w)"))
            for word in forbidden_words
        ]

    def forbidden_word_in(self, title: str) -> str | None:
        normalized = TextNormalizer.normalize(title)
        return next((word for word, pattern in self._patterns if pattern.search(normalized)), None)

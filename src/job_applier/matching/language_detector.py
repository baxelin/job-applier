import re

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.base import Locale


class LanguageDetector:
    """Decide o idioma do CV pelo idioma da vaga: português (Brasil, Portugal...) ou inglês.

    Conta palavras muito comuns de cada idioma; em caso de empate, prefere português.
    """

    _PORTUGUESE_WORDS = frozenset(
        {"de", "que", "para", "com", "nao", "uma", "os", "as", "da", "do", "em", "voce", "sera",
         "experiencia", "conhecimento", "conhecimentos", "vaga", "requisitos", "atividades", "e", "ou"}
    )
    _ENGLISH_WORDS = frozenset(
        {"the", "and", "with", "you", "we", "for", "our", "will", "experience", "knowledge", "to",
         "of", "is", "are", "requirements", "responsibilities", "or", "your"}
    )

    def detect(self, text: str) -> Locale:
        words = re.findall(r"\w+", TextNormalizer.normalize(text))
        portuguese = sum(word in self._PORTUGUESE_WORDS for word in words)
        english = sum(word in self._ENGLISH_WORDS for word in words)
        return Locale.EN if english > portuguese else Locale.PT

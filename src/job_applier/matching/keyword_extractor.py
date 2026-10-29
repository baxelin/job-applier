import re
from collections import Counter

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.glossary import Glossary


class KeywordExtractor:
    """Encontra no texto de uma vaga os termos do glossário, contando quantas vezes cada um aparece.

    O texto é percorrido uma única vez, sempre preferindo o nome mais longo: "Tailwind CSS" conta
    só como Tailwind (não como CSS) e "GitHub Actions" não conta GitHub. Os limites de palavra
    impedem falsos positivos como "c" dentro de "c++" ou "js" dentro de "node.js".
    """

    _BEFORE_NAME = r"(?<![\w.+#])"
    _AFTER_NAME = r"(?![\w+#])"

    def __init__(self, glossary: Glossary) -> None:
        self._term_by_name = {
            TextNormalizer.normalize(name): term.id for term in glossary.terms for name in term.normalized_names()
        }
        alternatives = "|".join(re.escape(name) for name in sorted(self._term_by_name, key=len, reverse=True))
        self._pattern = re.compile(f"{self._BEFORE_NAME}(?:{alternatives}){self._AFTER_NAME}")

    def extract(self, text: str) -> Counter[str]:
        matches = self._pattern.finditer(TextNormalizer.normalize(text))
        return Counter(self._term_by_name[match.group(0)] for match in matches)

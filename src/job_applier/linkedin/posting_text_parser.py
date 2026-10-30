import re
from datetime import date, timedelta

from job_applier.matching.text_normalizer import TextNormalizer


class PostingTextParser:
    """Interpreta textos do anúncio, em português ou inglês: número de candidatos e data de publicação."""

    _APPLICANTS = re.compile(r"(\d[\d.,]*)\s+(?:candidat|applicant|pessoas clicaram|people clicked)")
    _POSTED_PT = re.compile(r"\bha\s+(\d+|um|uma)\s+(minuto|hora|dia|semana|mes|meses|ano)")
    _POSTED_EN = re.compile(r"\b(\d+|an?|one)\s+(minute|hour|day|week|month|year)s?\s+ago")
    _UNIT_DAYS = {
        "minuto": 0, "hora": 0, "dia": 1, "semana": 7, "mes": 30, "meses": 30, "ano": 365,
        "minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365,
    }
    _WORD_NUMBERS = {"um": 1, "uma": 1, "a": 1, "an": 1, "one": 1}

    def applicants(self, text: str) -> int | None:
        match = self._APPLICANTS.search(TextNormalizer.normalize(text))
        return int(re.sub(r"[.,]", "", match.group(1))) if match else None

    def posted_on(self, text: str, today: date) -> date | None:
        normalized = TextNormalizer.normalize(text)
        match = self._POSTED_PT.search(normalized) or self._POSTED_EN.search(normalized)
        if not match:
            return None
        amount, unit = match.groups()
        quantity = self._WORD_NUMBERS.get(amount) or int(amount)
        return today - timedelta(days=quantity * self._UNIT_DAYS[unit])

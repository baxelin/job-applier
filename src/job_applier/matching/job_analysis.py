from collections.abc import Mapping
from dataclasses import dataclass

from job_applier.matching.area import Area
from job_applier.models.base import Locale


@dataclass(frozen=True)
class JobAnalysis:
    """O que a vaga pede: peso de cada termo, área de foco, idioma e se é, na prática, uma vaga de suporte."""

    term_weights: Mapping[str, int]
    focus: frozenset[Area]
    locale: Locale
    is_support_role: bool = False

    def weight_of(self, term_id: str) -> int:
        return self.term_weights.get(term_id, 0)

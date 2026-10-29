from dataclasses import dataclass

from job_applier.matching.job_analysis import JobAnalysis
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume


@dataclass(frozen=True)
class FitScore:
    """Aderência à vaga: % do peso dos termos pedidos que o candidato tem."""

    percentage: int
    matched_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]


class FitScorer:
    """Compara os termos da vaga com as skills e as tags técnicas do currículo."""

    def __init__(self, resume: Resume, glossary: Glossary) -> None:
        self._names = {term.id: term.name for term in glossary.terms}
        self._candidate_terms = resume.skill_terms() | (resume.bullet_tags() & glossary.term_ids())

    def score(self, analysis: JobAnalysis) -> FitScore:
        ranked = sorted(analysis.term_weights, key=lambda term_id: (-analysis.weight_of(term_id), term_id))
        matched = [term_id for term_id in ranked if term_id in self._candidate_terms]
        missing = [term_id for term_id in ranked if term_id not in self._candidate_terms]

        total_weight = sum(analysis.term_weights.values())
        matched_weight = sum(analysis.weight_of(term_id) for term_id in matched)

        return FitScore(
            percentage=round(100 * matched_weight / total_weight) if total_weight else 0,
            matched_terms=tuple(self._names[term_id] for term_id in matched),
            missing_terms=tuple(self._names[term_id] for term_id in missing),
        )

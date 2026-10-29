from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.models.automation_settings import ScoringWeights
from job_applier.models.base import TaggedModel
from job_applier.models.resume import Skill


class RelevanceScorer:
    """Pontua itens do currículo (bullets, projetos, skills) para uma vaga específica.

    Soma pontos quando as tags coincidem com a área de foco ou com termos citados na vaga,
    e penaliza itens só de suporte, que não interessam para vagas de dev/devops.
    """

    def __init__(self, analysis: JobAnalysis, weights: ScoringWeights) -> None:
        self._analysis = analysis
        self._weights = weights

    def score(self, item: TaggedModel) -> float:
        tags = set(item.tags)
        area_matches = len(tags & self._analysis.focus)
        keyword_weight = sum(self._analysis.weight_of(tag) for tag in tags)
        support_only = Area.SUPPORT in tags and area_matches == 0

        return (
            self._weights.area_match * area_matches
            + self._weights.keyword_match * keyword_weight
            - (self._weights.support_penalty if support_only else 0)
        )

    def score_skill(self, skill: Skill) -> float:
        return self.score(skill) + self._weights.keyword_match * self._analysis.weight_of(skill.term)

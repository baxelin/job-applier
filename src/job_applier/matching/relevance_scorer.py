from collections.abc import Collection

from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.models.automation_settings import ScoringWeights
from job_applier.models.base import TaggedModel
from job_applier.models.resume import Project, Skill


class RelevanceScorer:
    """Pontua itens do currículo (bullets, projetos, skills) para uma vaga específica.

    Soma pontos quando as tags coincidem com a área de foco ou com termos citados na vaga,
    e penaliza itens só de suporte, que não interessam para vagas de dev/devops.
    """

    def __init__(self, analysis: JobAnalysis, weights: ScoringWeights) -> None:
        self._analysis = analysis
        self._weights = weights

    def score(self, item: TaggedModel) -> float:
        return self._score_tags(set(item.tags))

    def score_project(self, project: Project) -> float:
        """Considera as tags do projeto e as de todos os seus bullets."""
        bullet_tags = {tag for bullet in project.bullets for tag in bullet.tags}
        return self._score_tags(set(project.tags) | bullet_tags)

    def score_skill(self, skill: Skill) -> float:
        return self.score(skill) + self._weights.keyword_match * self._analysis.weight_of(skill.term)

    def _score_tags(self, tags: Collection[str]) -> float:
        area_matches = len(set(tags) & self._analysis.focus)
        keyword_weight = sum(self._analysis.weight_of(tag) for tag in tags)
        support_only = Area.SUPPORT in tags and area_matches == 0

        return (
            self._weights.area_match * area_matches
            + self._weights.keyword_match * keyword_weight
            - (self._weights.support_penalty if support_only else 0)
        )

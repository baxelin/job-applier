from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.matching.relevance_scorer import RelevanceScorer
from job_applier.models.automation_settings import ScoringWeights
from job_applier.models.base import LocalizedText, Locale
from job_applier.models.resume import Bullet, Project, Skill

WEIGHTS = ScoringWeights(area_match=3, keyword_match=2, support_penalty=5, keyword_occurrence_cap=3)
TEXT = LocalizedText(pt="Texto.", en="Text.")


def scorer(focus: set[Area], term_weights: dict[str, int] | None = None) -> RelevanceScorer:
    return RelevanceScorer(JobAnalysis(term_weights or {}, frozenset(focus), Locale.PT), WEIGHTS)


class TestRelevanceScorer:
    def test_rewards_matching_area(self):
        assert scorer({Area.DEV}).score(Bullet(text=TEXT, tags=["dev"])) == 3

    def test_rewards_terms_required_by_the_job(self):
        bullet = Bullet(text=TEXT, tags=["devops", "docker"])

        assert scorer({Area.DEV}, {"docker": 2}).score(bullet) == 4

    def test_penalizes_support_only_items(self):
        assert scorer({Area.DEV}).score(Bullet(text=TEXT, tags=["suporte"])) == -5

    def test_does_not_penalize_support_items_that_also_match_the_focus(self):
        assert scorer({Area.DEV}).score(Bullet(text=TEXT, tags=["dev", "suporte"])) == 3

    def test_project_counts_tags_from_its_bullets(self):
        project = Project(name="site", tags=["dev"], bullets=[Bullet(text=TEXT, tags=["dev", "css"])])

        assert scorer({Area.DEV}, {"css": 1}).score_project(project) == 3 + 2

    def test_skill_scores_its_own_term(self):
        skill = Skill(term="python", years=2, tags=["dev"])

        assert scorer({Area.DEV}, {"python": 3}).score_skill(skill) == 3 + 2 * 3

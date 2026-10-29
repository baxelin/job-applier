from job_applier.matching.area import Area
from job_applier.matching.fit_scorer import FitScorer
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.models.base import Locale


def analysis(term_weights: dict[str, int]) -> JobAnalysis:
    return JobAnalysis(term_weights, frozenset({Area.DEV}), Locale.PT)


class TestFitScorer:
    def test_percentage_is_weighted_by_term_importance(self, example_base_data):
        fit_scorer = FitScorer(example_base_data.resume, example_base_data.glossary)

        fit = fit_scorer.score(analysis({"python": 3, "kubernetes": 1}))

        assert fit.percentage == 75

    def test_lists_matched_and_missing_terms_by_weight(self, example_base_data):
        fit_scorer = FitScorer(example_base_data.resume, example_base_data.glossary)

        fit = fit_scorer.score(analysis({"kubernetes": 1, "go": 2, "python": 3, "react": 1}))

        assert fit.matched_terms == ("Python", "React")
        assert fit.missing_terms == ("Go", "Kubernetes")

    def test_counts_technical_tags_from_bullets(self, example_base_data):
        fit_scorer = FitScorer(example_base_data.resume, example_base_data.glossary)

        assert fit_scorer.score(analysis({"pytest": 1})).percentage == 100

    def test_zero_when_job_mentions_no_known_term(self, example_base_data):
        fit_scorer = FitScorer(example_base_data.resume, example_base_data.glossary)

        assert fit_scorer.score(analysis({})).percentage == 0

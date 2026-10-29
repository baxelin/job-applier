import pytest

from job_applier.matching.area import Area
from job_applier.matching.job_analyzer import JobAnalyzer
from job_applier.models.base import Locale
from job_applier.models.job_description import JobDescription


@pytest.fixture
def analyzer(example_base_data) -> JobAnalyzer:
    return JobAnalyzer(example_base_data.glossary, keyword_occurrence_cap=3)


def job(title: str, text: str) -> JobDescription:
    return JobDescription(company="Empresa", title=title, text=text)


class TestJobAnalyzer:
    def test_caps_repeated_terms(self, analyzer):
        analysis = analyzer.analyze(job("Vaga", "Python " * 10))

        assert analysis.weight_of("python") == 3

    def test_counts_terms_from_title(self, analyzer):
        analysis = analyzer.analyze(job("Desenvolvedor React", "Venha trabalhar conosco."))

        assert analysis.weight_of("react") == 1

    def test_focus_on_dev_for_development_job(self, analyzer):
        analysis = analyzer.analyze(job("Desenvolvedor Júnior", "Python, React, SQL e testes com pytest."))

        assert analysis.focus == {Area.DEV}

    def test_focus_on_devops_for_infrastructure_job(self, analyzer):
        analysis = analyzer.analyze(job("DevOps Júnior", "AWS, Terraform, Kubernetes, Docker e CI/CD."))

        assert analysis.focus == {Area.DEVOPS}

    def test_shared_focus_when_both_areas_weigh_similarly(self, analyzer):
        analysis = analyzer.analyze(job("Desenvolvedor", "Python, SQL, AWS, Docker, Terraform e Kubernetes."))

        assert analysis.focus == {Area.DEV, Area.DEVOPS}

    def test_defaults_to_dev_when_nothing_is_recognized(self, analyzer):
        assert analyzer.analyze(job("Analista", "Vaga genérica.")).focus == {Area.DEV}

    def test_detects_language_from_description(self, analyzer):
        analysis = analyzer.analyze(job("Junior Developer", "We are looking for you to join our team."))

        assert analysis.locale is Locale.EN

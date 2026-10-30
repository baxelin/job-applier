from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from job_applier.matching.fit_scorer import FitScore, FitScorer
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.matching.job_analyzer import JobAnalyzer
from job_applier.models.base_data import BaseData
from job_applier.models.job_description import JobDescription
from job_applier.resume.html_resume_renderer import HtmlResumeRenderer
from job_applier.resume.pdf_exporter import PdfExporter
from job_applier.resume.resume_archive import ResumeArchive
from job_applier.resume.resume_tailor import ResumeTailor


@dataclass(frozen=True)
class JobEvaluation:
    """Análise da vaga e aderência do candidato, sem gerar CV."""

    job: JobDescription
    analysis: JobAnalysis
    fit: FitScore


@dataclass(frozen=True)
class GeneratedResume:
    evaluation: JobEvaluation
    path: Path

    @property
    def job(self) -> JobDescription:
        return self.evaluation.job

    @property
    def analysis(self) -> JobAnalysis:
        return self.evaluation.analysis

    @property
    def fit(self) -> FitScore:
        return self.evaluation.fit


class ResumeGenerator:
    """Fluxo completo: analisa a vaga, adapta o CV, gera o PDF e guarda no histórico."""

    def __init__(
        self,
        base_data: BaseData,
        archive: ResumeArchive,
        renderer: HtmlResumeRenderer | None = None,
        exporter: PdfExporter | None = None,
        today: Callable[[], date] = date.today,
    ) -> None:
        resume_settings = base_data.settings.resume
        self._analyzer = JobAnalyzer(base_data.glossary, resume_settings.weights.keyword_occurrence_cap)
        self._tailor = ResumeTailor(base_data.resume, base_data.glossary, resume_settings)
        self._fit_scorer = FitScorer(base_data.resume, base_data.glossary)
        self._archive = archive
        self._renderer = renderer or HtmlResumeRenderer()
        self._exporter = exporter or PdfExporter()
        self._today = today

    def evaluate(self, job: JobDescription) -> JobEvaluation:
        analysis = self._analyzer.analyze(job)
        return JobEvaluation(job=job, analysis=analysis, fit=self._fit_scorer.score(analysis))

    def generate(self, job: JobDescription) -> GeneratedResume:
        return self.generate_for(self.evaluate(job))

    def generate_for(self, evaluation: JobEvaluation) -> GeneratedResume:
        html = self._renderer.render(self._tailor.tailor(evaluation.analysis))
        path = self._archive.save(self._exporter.export(html), evaluation.job, self._today())
        return GeneratedResume(evaluation=evaluation, path=path)

from collections.abc import Sequence

from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.matching.relevance_scorer import RelevanceScorer
from job_applier.models.automation_settings import CountRange, ResumeSettings
from job_applier.models.base import Locale
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Bullet, Resume, Summary
from job_applier.resume.tailored_resume import TailoredExperience, TailoredProject, TailoredResume


class ResumeTailor:
    """Monta o CV adaptado: escolhe o resumo, os bullets, os projetos e as skills mais relevantes.

    Todas as experiências são mantidas (o histórico é real), mas cada uma mostra só os seus
    bullets mais relevantes, respeitando o mínimo e o máximo definidos em config.json.
    """

    def __init__(self, resume: Resume, glossary: Glossary, settings: ResumeSettings) -> None:
        self._resume = resume
        self._glossary = glossary
        self._settings = settings

    def tailor(self, analysis: JobAnalysis) -> TailoredResume:
        scorer = RelevanceScorer(analysis, self._settings.weights)
        return TailoredResume(
            locale=analysis.locale,
            contact=self._resume.contact,
            summary=self._best_summary(analysis.focus),
            experiences=tuple(
                TailoredExperience(
                    experience,
                    self._select_bullets(experience.bullets, scorer, self._settings.bullets_per_experience),
                )
                for experience in self._resume.experiences
            ),
            projects=self._select_projects(scorer),
            education=tuple(self._resume.education),
            skills=self._select_skills(scorer, analysis.locale),
            languages=tuple(self._resume.languages),
            certifications=tuple(self._resume.certifications),
        )

    def _best_summary(self, focus: frozenset[Area]) -> Summary:
        def similarity(summary: Summary) -> float:
            tags = set(summary.tags)
            return len(tags & focus) / len(tags | focus)

        return max(self._resume.summaries, key=similarity)

    def _select_projects(self, scorer: RelevanceScorer) -> tuple[TailoredProject, ...]:
        ranked = sorted(self._resume.projects, key=scorer.score_project, reverse=True)
        return tuple(
            TailoredProject(project, self._select_bullets(project.bullets, scorer, self._settings.bullets_per_project))
            for project in ranked[: self._settings.max_projects]
        )

    def _select_skills(self, scorer: RelevanceScorer, locale: Locale) -> tuple[str, ...]:
        ranked = sorted(self._resume.skills, key=scorer.score_skill, reverse=True)
        relevant = [skill for skill in ranked if scorer.score_skill(skill) > 0]
        names = self._glossary.display_names(locale)
        return tuple(names[skill.term] for skill in relevant[: self._settings.max_skills])

    @staticmethod
    def _select_bullets(bullets: Sequence[Bullet], scorer: RelevanceScorer, limits: CountRange) -> tuple[Bullet, ...]:
        ranked = sorted(bullets, key=scorer.score, reverse=True)
        relevant = [bullet for bullet in ranked[: limits.maximum] if scorer.score(bullet) > 0]
        return tuple(relevant if len(relevant) >= limits.minimum else ranked[: limits.minimum])

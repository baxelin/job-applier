from collections.abc import Sequence

from job_applier.matching.area import Area
from job_applier.matching.job_analysis import JobAnalysis
from job_applier.matching.relevance_scorer import RelevanceScorer
from job_applier.models.automation_settings import CountRange, ResumeSettings
from job_applier.models.glossary import Glossary, TermCategory
from job_applier.models.resume import Bullet, Resume, Skill, Summary
from job_applier.resume.summary_composer import SummaryComposer
from job_applier.resume.tailored_resume import TailoredExperience, TailoredProject, TailoredResume


class ResumeTailor:
    """Monta o CV adaptado: escolhe o resumo (completado com as skills mais relevantes), os bullets,
    os projetos e as skills.

    Todas as experiências são mantidas (o histórico é real), mas cada uma mostra só os seus
    bullets mais relevantes, respeitando o mínimo e o máximo definidos em config.json.
    """

    _NON_STACK_CATEGORIES = frozenset({TermCategory.SUPPORT, TermCategory.TOOL, TermCategory.PRACTICE})

    def __init__(self, resume: Resume, glossary: Glossary, settings: ResumeSettings) -> None:
        self._resume = resume
        self._glossary = glossary
        self._settings = settings
        self._categories = {term.id: term.category for term in glossary.terms}
        self._summary_composer = SummaryComposer(settings.summary_skill_count)

    def tailor(self, analysis: JobAnalysis) -> TailoredResume:
        scorer = RelevanceScorer(analysis, self._settings.weights)
        summary = self._best_summary(analysis.focus)
        relevant_skills = self._rank_relevant_skills(scorer)
        names = self._glossary.display_names(analysis.locale)
        return TailoredResume(
            locale=analysis.locale,
            contact=self._resume.contact,
            summary=summary,
            summary_text=self._summary_composer.compose(
                summary, [names[skill.term] for skill in self._stack_skills(relevant_skills)], analysis.locale
            ),
            experiences=tuple(
                TailoredExperience(
                    experience,
                    self._select_bullets(experience.bullets, scorer, self._settings.bullets_per_experience),
                )
                for experience in self._resume.experiences
            ),
            projects=self._select_projects(scorer),
            education=tuple(self._resume.education),
            skills=tuple(names[skill.term] for skill in relevant_skills[: self._settings.max_skills]),
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

    def _rank_relevant_skills(self, scorer: RelevanceScorer) -> list[Skill]:
        ranked = sorted(self._resume.skills, key=scorer.score_skill, reverse=True)
        return [skill for skill in ranked if scorer.score_skill(skill) > 0]

    def _stack_skills(self, ranked_skills: Sequence[Skill]) -> list[Skill]:
        """Skills que fazem sentido citar no resumo: tecnologias, sem ferramentas, práticas ou suporte."""
        return [skill for skill in ranked_skills if self._categories[skill.term] not in self._NON_STACK_CATEGORIES]

    @staticmethod
    def _select_bullets(bullets: Sequence[Bullet], scorer: RelevanceScorer, limits: CountRange) -> tuple[Bullet, ...]:
        ranked = sorted(bullets, key=scorer.score, reverse=True)
        relevant = [bullet for bullet in ranked[: limits.maximum] if scorer.score(bullet) > 0]
        return tuple(relevant if len(relevant) >= limits.minimum else ranked[: limits.minimum])

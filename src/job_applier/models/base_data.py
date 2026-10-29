from typing import Self

from pydantic import model_validator

from job_applier.models.answer_book import AnswerBook
from job_applier.models.automation_settings import AutomationSettings
from job_applier.models.base import StrictModel
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume


class BaseData(StrictModel):
    """Conjunto dos dados base, validados também entre si."""

    resume: Resume
    glossary: Glossary
    answer_book: AnswerBook
    settings: AutomationSettings

    @model_validator(mode="after")
    def _skills_exist_in_glossary(self) -> Self:
        unknown_terms = sorted(self.resume.skill_terms() - self.glossary.term_ids())
        if unknown_terms:
            raise ValueError(f"Skills sem termo correspondente no glossário: {', '.join(unknown_terms)}")
        return self

    def describe(self) -> str:
        return (
            f"Dados base válidos: {len(self.resume.experiences)} experiências, "
            f"{len(self.resume.skills)} skills, {len(self.resume.summaries)} resumos, "
            f"{len(self.glossary.terms)} termos, {len(self.answer_book.answers)} respostas "
            f"({len(self.answer_book.unanswered())} sem resposta definida)."
        )

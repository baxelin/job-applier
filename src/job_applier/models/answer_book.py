from typing import Self

from pydantic import Field, model_validator

from job_applier.models.base import NonEmptyText, Slug, StrictModel
from job_applier.models.uniqueness import UniquenessChecker


class Answer(StrictModel):
    """Resposta pronta para perguntas de formulário que contenham algum dos padrões.

    Sem resposta definida (null), o robô não deve responder sozinho essa pergunta.
    """

    id: Slug
    patterns: list[NonEmptyText] = Field(min_length=1)
    answer: NonEmptyText | None = None


class SkillYearsRule(StrictModel):
    """Perguntas do tipo "quantos anos de experiência com X": o valor vem das skills do currículo."""

    patterns: list[NonEmptyText] = Field(min_length=1)
    default_years: int = Field(ge=0)


class AnswerBook(StrictModel):
    """Respostas conhecidas para os formulários de candidatura (respostas.json)."""

    answers: list[Answer] = Field(min_length=1)
    skill_years: SkillYearsRule

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Self:
        UniquenessChecker.ensure_unique((answer.id for answer in self.answers), "Ids de respostas")
        return self

    def unanswered(self) -> list[Answer]:
        return [answer for answer in self.answers if answer.answer is None]

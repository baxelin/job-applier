from typing import Self

from pydantic import Field, model_validator

from job_applier.models.base import LocalizedText, NonEmptyText, Slug, StrictModel
from job_applier.models.uniqueness import UniquenessChecker


class Answer(StrictModel):
    """Resposta pronta para perguntas de formulário que contenham algum dos padrões.

    Sem resposta definida (null), o robô não deve responder sozinho essa pergunta.
    """

    id: Slug
    patterns: list[NonEmptyText] = Field(min_length=1)
    answer: LocalizedText | None = None


class SkillYearsRule(StrictModel):
    """Perguntas do tipo "quantos anos de experiência com X": o valor vem das skills do currículo."""

    patterns: list[NonEmptyText] = Field(min_length=1)
    default_years: int = Field(ge=0)


class SalaryRule(StrictModel):
    """Pretensão salarial (valores CLT): usa o mínimo informado pela vaga, nunca abaixo do piso.

    Quando a vaga não informa faixa, responde o valor padrão. Para vagas PJ, os valores são
    multiplicados por contractor_multiplier, que compensa os benefícios que o PJ não recebe.
    """

    patterns: list[NonEmptyText] = Field(min_length=1)
    minimum: int = Field(gt=0)
    default: int = Field(gt=0)
    contractor_multiplier: float = Field(ge=1)

    @model_validator(mode="after")
    def _default_not_below_minimum(self) -> Self:
        if self.default < self.minimum:
            raise ValueError(f"valor padrão ({self.default}) menor que o mínimo ({self.minimum})")
        return self


class AnswerBook(StrictModel):
    """Respostas conhecidas para os formulários de candidatura (respostas.json)."""

    answers: list[Answer] = Field(min_length=1)
    skill_years: SkillYearsRule
    salary: SalaryRule

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Self:
        UniquenessChecker.ensure_unique((answer.id for answer in self.answers), "Ids de respostas")
        return self

    def unanswered(self) -> list[Answer]:
        return [answer for answer in self.answers if answer.answer is None]

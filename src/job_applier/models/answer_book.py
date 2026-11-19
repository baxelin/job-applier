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


class YearsArea(StrictModel):
    """Área de atuação sem tecnologia do glossário ("desenvolvimento de software", "APIs") e os anos declarados."""

    patterns: list[NonEmptyText] = Field(min_length=1)
    years: float = Field(ge=0)


class SkillYearsRule(StrictModel):
    """Perguntas do tipo "quantos anos de experiência com X": o valor vem das skills do currículo.

    Tecnologia fora do CV, mas derivada de uma que está nele (related_to no glossário), vale related_years;
    sem related_years, ou sem parentesco, vale default_years. Quando a pergunta não cita tecnologia do
    glossário, vale a área cujo padrão aparecer nela (vence o mais longo); sem área, fica sem resposta.
    """

    patterns: list[NonEmptyText] = Field(min_length=1)
    default_years: int = Field(ge=0)
    related_years: float | None = Field(default=None, ge=0)
    areas: list[YearsArea] = []


class ExperienceRule(StrictModel):
    """Perguntas de sim/não sobre experiência com tecnologias ("Do you have experience with SAP?").

    Responde sim quando todas as tecnologias citadas estão no CV (ou derivam dele, com related_years) e não
    quando nenhuma está; misturado ou sem tecnologia reconhecida, fica sem resposta. Vale só para campos de escolha, nunca para texto livre.
    """

    patterns: list[NonEmptyText] = Field(min_length=1)


class WorkplaceRule(StrictModel):
    """Perguntas de sim/não sobre modalidade ("Aceita trabalhar presencial em São Paulo?").

    Remoto é sempre sim. Presencial e híbrido seguem filters.on_site_cities do config.json: sim quando a
    pergunta cita uma cidade aceita ou a vaga é numa delas, não quando a vaga é em outra cidade; sem saber
    onde, fica sem resposta. Vale só para campos de escolha.
    """

    on_site_patterns: list[NonEmptyText] = Field(min_length=1)
    remote_patterns: list[NonEmptyText] = Field(min_length=1)


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
    experience: ExperienceRule | None = None
    workplace: WorkplaceRule | None = None

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Self:
        UniquenessChecker.ensure_unique((answer.id for answer in self.answers), "Ids de respostas")
        return self

    def unanswered(self) -> list[Answer]:
        return [answer for answer in self.answers if answer.answer is None]

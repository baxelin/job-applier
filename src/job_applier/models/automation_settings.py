from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from job_applier.models.base import NonEmptyText, StrictModel


class NumberRange(StrictModel):
    minimum: float = Field(ge=0)
    maximum: float = Field(ge=0)

    @model_validator(mode="after")
    def _minimum_not_above_maximum(self) -> Self:
        if self.minimum > self.maximum:
            raise ValueError(f"mínimo ({self.minimum}) maior que o máximo ({self.maximum})")
        return self


class LongPause(StrictModel):
    """Pausa longa feita a cada N candidaturas, para simular o ritmo de uma pessoa."""

    every_applications: int = Field(ge=1)
    minutes: NumberRange


class ExperienceLevel(StrEnum):
    INTERNSHIP = "internship"
    ENTRY_LEVEL = "entry_level"
    ASSOCIATE = "associate"
    MID_SENIOR = "mid_senior"
    DIRECTOR = "director"
    EXECUTIVE = "executive"


class WorkplaceType(StrEnum):
    ON_SITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"


class JobFilters(StrictModel):
    experience_levels: list[ExperienceLevel] = Field(min_length=1)
    workplace_types: list[WorkplaceType] = Field(min_length=1)
    forbidden_title_words: list[NonEmptyText] = []


class SearchQuery(StrictModel):
    """Busca de vagas. Sem modalidades próprias, vale o filtro geral (filters.workplace_types)."""

    keywords: NonEmptyText
    location: NonEmptyText
    workplace_types: list[WorkplaceType] | None = Field(default=None, min_length=1)


class CountRange(StrictModel):
    minimum: int = Field(ge=0)
    maximum: int = Field(ge=1)

    @model_validator(mode="after")
    def _minimum_not_above_maximum(self) -> Self:
        if self.minimum > self.maximum:
            raise ValueError(f"mínimo ({self.minimum}) maior que o máximo ({self.maximum})")
        return self


class ScoringWeights(StrictModel):
    """Pesos da pontuação de bullets, skills e projetos em relação à vaga."""

    area_match: float = Field(ge=0)
    keyword_match: float = Field(ge=0)
    support_penalty: float = Field(ge=0)
    keyword_occurrence_cap: int = Field(ge=1)


class ResumeSettings(StrictModel):
    """Regras de montagem do CV adaptado."""

    weights: ScoringWeights
    bullets_per_experience: CountRange
    bullets_per_project: CountRange
    max_projects: int = Field(ge=0)
    max_skills: int = Field(ge=1)
    summary_skill_count: int = Field(ge=1)


class AutomationSettings(StrictModel):
    """Configuração do robô (config.json): ritmo, limites, filtros, buscas em ordem de prioridade e CV."""

    daily_application_limit: int = Field(ge=1)
    delay_between_actions_seconds: NumberRange
    delay_between_applications_seconds: NumberRange
    long_pause: LongPause
    filters: JobFilters
    searches: list[SearchQuery] = Field(min_length=1)
    resume: ResumeSettings

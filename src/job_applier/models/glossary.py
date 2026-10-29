from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from job_applier.models.base import NonEmptyText, Slug, StrictModel
from job_applier.models.uniqueness import UniquenessChecker


class TermCategory(StrEnum):
    LANGUAGE = "language"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATA = "data"
    CLOUD = "cloud"
    DEVOPS = "devops"
    TESTING = "testing"
    TOOL = "tool"
    OPERATING_SYSTEM = "operating_system"
    PRACTICE = "practice"
    SUPPORT = "support"


class Term(StrictModel):
    """Tecnologia ou termo com as formas como pode aparecer escrito numa vaga."""

    id: Slug
    name: NonEmptyText
    category: TermCategory
    synonyms: list[NonEmptyText] = []

    def normalized_names(self) -> set[str]:
        return {name.casefold() for name in (self.name, *self.synonyms)}


class Glossary(StrictModel):
    """Glossário de termos (termos.json) usado para reconhecer tecnologias nas vagas."""

    terms: list[Term] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_and_names_are_unique(self) -> Self:
        UniquenessChecker.ensure_unique((term.id for term in self.terms), "Ids de termos")
        UniquenessChecker.ensure_unique(
            (name for term in self.terms for name in term.normalized_names()),
            "Nomes/sinônimos de termos",
        )
        return self

    def term_ids(self) -> set[str]:
        return {term.id for term in self.terms}

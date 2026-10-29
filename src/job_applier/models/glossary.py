from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from job_applier.models.base import Locale, NonEmptyText, Slug, StrictModel
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
    """Tecnologia ou termo com as formas como pode aparecer escrito numa vaga.

    name_en só é necessário quando o nome em inglês difere do nome principal (ex.: POO / OOP).
    """

    id: Slug
    name: NonEmptyText
    name_en: NonEmptyText | None = None
    category: TermCategory
    synonyms: list[NonEmptyText] = []

    def display_name(self, locale: Locale) -> str:
        return self.name_en if locale is Locale.EN and self.name_en else self.name

    def normalized_names(self) -> set[str]:
        names = (self.name, self.name_en, *self.synonyms)
        return {name.casefold() for name in names if name}


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

    def display_names(self, locale: Locale) -> dict[str, str]:
        return {term.id: term.display_name(locale) for term in self.terms}

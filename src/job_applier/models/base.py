from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    """Base dos modelos: imutável e rejeita campos desconhecidos (evita erros de digitação no JSON)."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalizedText(StrictModel):
    """Texto em português (vagas no Brasil e em Portugal) e em inglês (vagas no exterior)."""

    pt: NonEmptyText
    en: NonEmptyText


class TaggedModel(StrictModel):
    """Item do currículo classificado por tags, usadas para montar versões por tipo de vaga."""

    tags: list[Slug] = Field(min_length=1)

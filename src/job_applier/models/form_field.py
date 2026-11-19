from enum import StrEnum
from typing import Self

from job_applier.models.base import NonEmptyText, StrictModel


class FieldKind(StrEnum):
    TEXT = "texto"
    NUMBER = "numero"
    LONG_TEXT = "texto_longo"
    SELECT = "lista"
    RADIO = "opcao_unica"
    CHECKBOX = "caixa_de_selecao"
    TYPEAHEAD = "busca_com_sugestoes"


class FieldOption(StrictModel):
    """Opção de um campo de escolha; control é o value do <option> ou o id do input."""

    label: NonEmptyText
    control: NonEmptyText
    selected: bool = False


class FormField(StrictModel):
    """Campo de um formulário de candidatura como a pessoa o vê: pergunta, opções e valor atual."""

    kind: FieldKind
    question: NonEmptyText
    control: str | None = None
    required: bool = False
    value: str = ""
    options: tuple[FieldOption, ...] = ()
    max_length: int | None = None

    def selected_options(self) -> tuple[FieldOption, ...]:
        return tuple(option for option in self.options if option.selected)

    def current_answer(self) -> str:
        return ", ".join(option.label for option in self.selected_options()) or self.value

    def is_empty(self) -> bool:
        return not self.current_answer().strip()


class FieldAnswer(StrictModel):
    """Resposta escolhida para um campo: o texto digitado ou, nos campos de escolha, as opções marcadas.

    Lista e opção única têm sempre uma opção; caixas de seleção podem ter várias.
    """

    text: NonEmptyText
    options: tuple[FieldOption, ...] = ()

    @classmethod
    def choosing(cls, *options: FieldOption) -> Self:
        return cls(text=", ".join(option.label for option in options), options=options)

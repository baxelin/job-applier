import re
from collections.abc import Sequence

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.form_field import FieldOption


class OptionMatcher:
    """Encontra, entre as opções de um campo, a que corresponde a uma resposta em texto.

    Compara em três níveis, do mais ao menos exato: texto igual, sim/não (o LinkedIn mostra "Yes"/"No"
    mesmo em vagas em português) e opção contida na resposta como palavras inteiras ("Avançado" em
    "Avançado (B2)"). Na dúvida entre duas opções não escolhe nenhuma: errar uma resposta custa mais
    do que deixar a vaga pendente.
    """

    _YES = frozenset({"sim", "yes"})
    _NO = frozenset({"nao", "no"})

    def pick(self, options: Sequence[FieldOption], answers: Sequence[str]) -> FieldOption | None:
        for answer in answers:
            if option := self._pick_for(options, TextNormalizer.normalize(answer)):
                return option
        return None

    def _pick_for(self, options: Sequence[FieldOption], answer: str) -> FieldOption | None:
        normalized = {option: TextNormalizer.normalize(option.label) for option in options}
        for matches in (
            [option for option, label in normalized.items() if label == answer],
            [option for option, label in normalized.items() if self._same_yes_or_no(label, answer)],
            [option for option, label in normalized.items() if self._contains(answer, label)],
        ):
            if matches:
                return matches[0] if len(matches) == 1 else None
        return None

    def _same_yes_or_no(self, label: str, answer: str) -> bool:
        return (label in self._YES and answer in self._YES) or (label in self._NO and answer in self._NO)

    @staticmethod
    def _contains(answer: str, label: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(label)}(?!\w)", answer) is not None

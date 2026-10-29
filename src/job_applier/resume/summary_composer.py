from collections.abc import Sequence

from job_applier.models.base import Locale
from job_applier.models.resume import Summary
from job_applier.resume.resume_labels import ResumeLabels


class SummaryComposer:
    """Monta o texto final do resumo trocando o marcador {stack} pelas tecnologias mais relevantes para a vaga.

    As tecnologias vêm das skills já escolhidas para o CV (que o candidato realmente tem),
    então o resumo nunca cita algo que não está no currículo.
    """

    PLACEHOLDER = "{stack}"

    def __init__(self, skill_count: int) -> None:
        self._skill_count = skill_count

    def compose(self, summary: Summary, skills: Sequence[str], locale: Locale) -> str:
        stack = ResumeLabels(locale).enumerate(skills[: self._skill_count])
        return summary.text.in_locale(locale).replace(self.PLACEHOLDER, stack)

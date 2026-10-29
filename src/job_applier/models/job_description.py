from pydantic import HttpUrl

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.models.base import NonEmptyText, StrictModel


class JobDescription(StrictModel):
    """Vaga a partir da qual o CV é adaptado."""

    company: NonEmptyText
    title: NonEmptyText
    text: NonEmptyText
    location: NonEmptyText | None = None
    url: HttpUrl | None = None

    def key(self) -> str:
        """Identifica a vaga sem repetição: pelo link quando existe, senão por empresa e título."""
        if self.url:
            return str(self.url)
        return TextNormalizer.normalize(f"{self.company}|{self.title}")

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

from job_applier.models.base import StrictModel
from job_applier.models.job_description import JobDescription

LinkedInJobId = Annotated[str, StringConstraints(pattern=r"^\d+$")]


class ApplyType(StrEnum):
    EASY_APPLY = "candidatura_simplificada"
    EXTERNAL = "site_externo"
    CLOSED = "encerrada"
    UNKNOWN = "desconhecido"


class JobPosting(StrictModel):
    """Vaga lida do LinkedIn: a descrição usada para o CV e os dados do anúncio."""

    linkedin_id: LinkedInJobId
    description: JobDescription
    apply_type: ApplyType
    applicants: int | None = Field(default=None, ge=0)
    posted_on: date | None = None

    @staticmethod
    def url_for(linkedin_id: str) -> str:
        return f"https://www.linkedin.com/jobs/view/{linkedin_id}/"

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from job_applier.models.base import NonEmptyText, StrictModel


class ApplicationStatus(StrEnum):
    CV_GENERATED = "cv_gerado"
    APPLIED = "candidatura_enviada"
    SKIPPED = "ignorada"
    FAILED = "erro"


class JobApplication(StrictModel):
    """Registro de uma vaga processada: análise, CV gerado e situação da candidatura."""

    id: int | None = None
    job_key: NonEmptyText
    company: NonEmptyText
    title: NonEmptyText
    location: str | None = None
    url: str | None = None
    locale: NonEmptyText
    focus: NonEmptyText
    is_support_role: bool
    fit_percentage: int = Field(ge=0, le=100)
    matched_terms: tuple[str, ...] = ()
    missing_terms: tuple[str, ...] = ()
    resume_path: NonEmptyText
    status: ApplicationStatus = ApplicationStatus.CV_GENERATED
    created_at: datetime
    updated_at: datetime


class UnknownQuestion(StrictModel):
    """Pergunta de formulário que o robô não soube responder, para o usuário cadastrar em respostas.json."""

    id: int | None = None
    question: NonEmptyText
    occurrences: int = Field(ge=1)
    last_company: str | None = None
    last_title: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime

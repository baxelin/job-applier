from job_applier.models.base import NonEmptyText, StrictModel


class JobDescription(StrictModel):
    """Vaga a partir da qual o CV é adaptado."""

    company: NonEmptyText
    title: NonEmptyText
    text: NonEmptyText

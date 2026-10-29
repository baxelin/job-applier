from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, HttpUrl, StringConstraints, model_validator

from job_applier.models.base import LocalizedText, NonEmptyText, Slug, StrictModel, TaggedModel
from job_applier.models.uniqueness import UniquenessChecker

YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class Period(StrictModel):
    """Intervalo no formato AAAA-MM. Sem fim significa que ainda está em andamento."""

    start: YearMonth
    end: YearMonth | None = None

    @model_validator(mode="after")
    def _end_not_before_start(self) -> Self:
        if self.end is not None and self.end < self.start:
            raise ValueError(f"fim ({self.end}) anterior ao início ({self.start})")
        return self


class Contact(StrictModel):
    full_name: NonEmptyText
    email: Annotated[str, StringConstraints(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
    phone: NonEmptyText
    location: NonEmptyText
    linkedin_url: HttpUrl
    github_url: HttpUrl
    website_url: HttpUrl | None = None


class Summary(TaggedModel):
    id: Slug
    text: LocalizedText


class Bullet(TaggedModel):
    text: LocalizedText


class Experience(TaggedModel):
    role: LocalizedText
    company: NonEmptyText
    period: Period
    bullets: list[Bullet] = Field(min_length=1)


class Project(TaggedModel):
    name: NonEmptyText
    url: HttpUrl | None = None
    bullets: list[Bullet] = Field(min_length=1)


class Education(StrictModel):
    degree: LocalizedText
    institution: NonEmptyText
    period: Period


class Skill(TaggedModel):
    """Habilidade ligada a um termo do glossário (termos.json) pelo seu id."""

    term: Slug
    years: float = Field(ge=0)


class Language(StrictModel):
    name: LocalizedText
    level: LocalizedText


class CertificationStatus(StrEnum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


class Certification(StrictModel):
    name: NonEmptyText
    status: CertificationStatus


class Resume(StrictModel):
    """Currículo base (cv_base.json): fonte única de onde saem as versões por vaga."""

    contact: Contact
    summaries: list[Summary] = Field(min_length=2, max_length=4)
    experiences: list[Experience] = Field(min_length=1)
    projects: list[Project] = []
    education: list[Education] = []
    skills: list[Skill] = Field(min_length=1)
    languages: list[Language] = []
    certifications: list[Certification] = []

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Self:
        UniquenessChecker.ensure_unique((summary.id for summary in self.summaries), "Resumos")
        UniquenessChecker.ensure_unique((skill.term for skill in self.skills), "Skills")
        return self

    def skill_terms(self) -> set[str]:
        return {skill.term for skill in self.skills}

    def bullet_tags(self) -> set[str]:
        sections = (*self.experiences, *self.projects)
        return {tag for section in sections for bullet in section.bullets for tag in bullet.tags}

from dataclasses import dataclass

from job_applier.models.base import Locale
from job_applier.models.resume import Bullet, Certification, Contact, Education, Experience, Language, Project, Summary


@dataclass(frozen=True)
class TailoredExperience:
    experience: Experience
    bullets: tuple[Bullet, ...]


@dataclass(frozen=True)
class TailoredProject:
    project: Project
    bullets: tuple[Bullet, ...]


@dataclass(frozen=True)
class TailoredResume:
    """CV já selecionado e ordenado para uma vaga, pronto para ser renderizado."""

    locale: Locale
    contact: Contact
    summary: Summary
    summary_text: str
    experiences: tuple[TailoredExperience, ...]
    projects: tuple[TailoredProject, ...]
    education: tuple[Education, ...]
    skills: tuple[str, ...]
    languages: tuple[Language, ...]
    certifications: tuple[Certification, ...]

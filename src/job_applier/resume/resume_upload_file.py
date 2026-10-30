from dataclasses import dataclass
from pathlib import Path

from job_applier.models.base import Locale
from job_applier.models.job_application import JobApplication
from job_applier.models.resume import Contact
from job_applier.resume.resume_file_namer import ResumeFileNamer


@dataclass(frozen=True)
class ResumeUploadFile:
    """O PDF como a empresa o recebe: conteúdo do histórico com o nome neutro, que não cita a vaga."""

    name: str
    content: bytes


class ResumeUploadFileLoader:
    """Carrega do histórico (data/cvs) o CV gerado para a vaga, pronto para o upload."""

    def __init__(self, project_root: Path, contact: Contact, namer: ResumeFileNamer | None = None) -> None:
        self._project_root = project_root
        self._contact = contact
        self._namer = namer or ResumeFileNamer()

    def load(self, application: JobApplication) -> ResumeUploadFile:
        if application.resume_path is None:
            raise FileNotFoundError(f"A vaga {application.job_key} não tem CV gerado.")
        return ResumeUploadFile(
            name=self._namer.upload_name(self._contact, Locale(application.locale)),
            content=(self._project_root / application.resume_path).read_bytes(),
        )

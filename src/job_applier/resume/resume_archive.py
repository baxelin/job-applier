from datetime import date
from pathlib import Path

from job_applier.models.job_description import JobDescription
from job_applier.resume.resume_file_namer import ResumeFileNamer


class ResumeArchive:
    """Guarda cada CV gerado em data/cvs, sem sobrescrever CVs anteriores."""

    def __init__(self, directory: Path, namer: ResumeFileNamer | None = None) -> None:
        self._directory = directory
        self._namer = namer or ResumeFileNamer()

    def save(self, pdf: bytes, job: JobDescription, day: date) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._available_path(self._directory / self._namer.archive_name(job, day))
        path.write_bytes(pdf)
        return path

    @staticmethod
    def _available_path(path: Path) -> Path:
        candidate, copy_number = path, 2
        while candidate.exists():
            candidate = path.with_stem(f"{path.stem}_{copy_number}")
            copy_number += 1
        return candidate

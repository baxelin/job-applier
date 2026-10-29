import re
import unicodedata
from datetime import date

from job_applier.models.base import Locale
from job_applier.models.job_description import JobDescription
from job_applier.models.resume import Contact


class ResumeFileNamer:
    """Nomes dos arquivos de CV.

    - Arquivo enviado à empresa: neutro, sem citar a vaga (Curriculo_Nome_Sobrenome.pdf).
    - Arquivo guardado no histórico: identifica a candidatura (AAAA-MM-DD_Empresa_Vaga.pdf).
    """

    _UPLOAD_PREFIX = {Locale.PT: "Curriculo", Locale.EN: "Resume"}
    _MAX_PART_LENGTH = 60

    def upload_name(self, contact: Contact, locale: Locale) -> str:
        names = contact.full_name.split()
        return f"{self._UPLOAD_PREFIX[locale]}_{self._slug(names[0])}_{self._slug(names[-1])}.pdf"

    def archive_name(self, job: JobDescription, day: date) -> str:
        return f"{day.isoformat()}_{self._slug(job.company)}_{self._slug(job.title)}.pdf"

    @classmethod
    def _slug(cls, text: str) -> str:
        ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-")
        return slug[: cls._MAX_PART_LENGTH].rstrip("-")

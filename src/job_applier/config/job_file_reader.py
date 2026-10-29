import re
from pathlib import Path

from pydantic import ValidationError

from job_applier.config.json_model_loader import DataFileNotFoundError, InvalidDataFileError
from job_applier.models.job_description import JobDescription


class JobFileReader:
    """Lê vagas salvas em .txt, no formato:

        Empresa: Nome da empresa
        Vaga: Título da vaga
        ---
        Descrição completa copiada do LinkedIn...
    """

    _SEPARATOR = re.compile(r"^-{3,}[ \t]*$", re.MULTILINE)
    _HEADER_FIELDS = {"empresa": "company", "vaga": "title"}

    def read(self, path: Path) -> JobDescription:
        try:
            content = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as error:
            raise DataFileNotFoundError(path) from error

        parts = self._SEPARATOR.split(content, maxsplit=1)
        if len(parts) != 2:
            raise InvalidDataFileError(path, "Falta a linha '---' separando o cabeçalho da descrição da vaga.")

        header, text = parts
        try:
            return JobDescription(**self._parse_header(header), text=text.strip())
        except ValidationError as error:
            raise InvalidDataFileError(path, str(error)) from error

    def read_all(self, path: Path) -> list[JobDescription]:
        files = sorted(path.glob("*.txt")) if path.is_dir() else [path]
        return [self.read(file) for file in files]

    def _parse_header(self, header: str) -> dict[str, str]:
        fields = {}
        for line in header.splitlines():
            key, separator, value = line.partition(":")
            field = self._HEADER_FIELDS.get(key.strip().casefold())
            if separator and field:
                fields[field] = value.strip()
        return fields

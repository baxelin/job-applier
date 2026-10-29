from pathlib import Path

from pydantic import BaseModel, ValidationError


class DataFileError(Exception):
    """Erro ao carregar os dados base; a mensagem é pensada para o usuário final."""


class DataFileNotFoundError(DataFileError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Arquivo não encontrado: {path}")


class InvalidDataFileError(DataFileError):
    def __init__(self, path: Path, details: str) -> None:
        super().__init__(f"Arquivo inválido: {path}\n{details}")


class InconsistentDataError(DataFileError):
    def __init__(self, details: str) -> None:
        super().__init__(f"Os dados base não estão consistentes entre si:\n{details}")


class JsonModelLoader:
    """Lê um arquivo JSON e o valida contra um modelo Pydantic."""

    def load[ModelT: BaseModel](self, path: Path, model: type[ModelT]) -> ModelT:
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise DataFileNotFoundError(path) from error

        try:
            return model.model_validate_json(content)
        except ValidationError as error:
            raise InvalidDataFileError(path, str(error)) from error

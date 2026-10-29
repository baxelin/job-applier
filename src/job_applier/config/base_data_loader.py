from dataclasses import dataclass
from pathlib import Path
from typing import Self

from pydantic import ValidationError

from job_applier.config.json_model_loader import InconsistentDataError, JsonModelLoader
from job_applier.models.answer_book import AnswerBook
from job_applier.models.automation_settings import AutomationSettings
from job_applier.models.base_data import BaseData
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume


@dataclass(frozen=True)
class BaseDataPaths:
    resume: Path
    answer_book: Path
    glossary: Path
    settings: Path

    @classmethod
    def from_project_root(cls, root: Path) -> Self:
        return cls(
            resume=root / "personal" / "cv_base.json",
            answer_book=root / "personal" / "respostas.json",
            glossary=root / "config" / "termos.json",
            settings=root / "config" / "config.json",
        )


class BaseDataLoader:
    """Carrega e valida os quatro arquivos de dados base."""

    def __init__(self, paths: BaseDataPaths, json_loader: JsonModelLoader | None = None) -> None:
        self._paths = paths
        self._json_loader = json_loader or JsonModelLoader()

    def load(self) -> BaseData:
        resume = self._json_loader.load(self._paths.resume, Resume)
        answer_book = self._json_loader.load(self._paths.answer_book, AnswerBook)
        glossary = self._json_loader.load(self._paths.glossary, Glossary)
        settings = self._json_loader.load(self._paths.settings, AutomationSettings)

        try:
            return BaseData(resume=resume, glossary=glossary, answer_book=answer_book, settings=settings)
        except ValidationError as error:
            raise InconsistentDataError(str(error)) from error

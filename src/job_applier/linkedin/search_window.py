import math
from collections.abc import Callable
from datetime import datetime

from job_applier.models.automation_settings import SearchQuery
from job_applier.storage.search_progress_repository import SearchProgressRepository


class SearchWindow:
    """Até quantas horas atrás cada busca pede vagas: desde a última vez que foi percorrida inteira.

    Rodando todo dia, as primeiras páginas de uma busca de 30 dias ficam cheias de vagas já vistas e as
    novas ficam para trás. Pedindo só o que foi publicado desde a última busca completa (com folga), quase
    tudo o que aparece é novo. Uma busca nunca completada usa a janela máxima (filters.posted_within_hours).
    """

    def __init__(
        self,
        maximum_hours: int | None,
        margin_hours: int,
        progress: SearchProgressRepository | None,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._maximum_hours = maximum_hours
        self._margin_hours = margin_hours
        self._progress = progress
        self._now = now

    def hours_for(self, search: SearchQuery) -> int | None:
        last = self._progress.last_completed(search.key()) if self._progress else None
        if last is None:
            return self._maximum_hours
        hours = math.ceil((self._now() - last).total_seconds() / 3600) + self._margin_hours
        return min(hours, self._maximum_hours) if self._maximum_hours else hours

    def mark_completed(self, search: SearchQuery, started_at: datetime) -> None:
        if self._progress:
            self._progress.mark_completed(search.key(), started_at)

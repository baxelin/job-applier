from collections.abc import Callable
from datetime import date

from job_applier.reporting.daily_report_text import DailyReportText
from job_applier.reporting.daily_summary import DailySummaryBuilder


class DailyReportCommand:
    """Mostra o resumo de um dia (padrão: hoje) no terminal."""

    def __init__(
        self,
        builder: DailySummaryBuilder,
        text: DailyReportText | None = None,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._builder = builder
        self._text = text or DailyReportText()
        self._today = today

    def run(self, day: date | None = None) -> int:
        print(self._text.render(self._builder.build(day or self._today())))
        return 0

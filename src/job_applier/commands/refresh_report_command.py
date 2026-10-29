import sys

from job_applier.storage.application_tracker import ApplicationTracker
from job_applier.storage.excel_report_writer import SpreadsheetLockedError


class RefreshReportCommand:
    """Recria a planilha de acompanhamento a partir do banco.

    Se a planilha estiver aberta no Excel, apenas avisa: os dados já estão no banco
    e a próxima execução tenta de novo.
    """

    def __init__(self, tracker: ApplicationTracker) -> None:
        self._tracker = tracker

    def run(self) -> int:
        try:
            self._tracker.refresh_report()
        except SpreadsheetLockedError as error:
            print(f"Aviso: {error}", file=sys.stderr)
            return 0
        print("Planilha atualizada: data/candidaturas.xlsx")
        return 0

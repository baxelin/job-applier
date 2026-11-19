from job_applier.models.job_application import ScanStatus


class StopRun(Exception):
    """Encerra a execução inteira (varredura, ensaio ou envio), com o motivo e a situação final registrados."""

    def __init__(self, reason: str, status: ScanStatus = ScanStatus.STOPPED) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status

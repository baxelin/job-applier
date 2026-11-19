import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path


class ExecutionLog:
    """Mostra o andamento no terminal e grava o mesmo texto em data/logs/AAAA-MM-DD.log.

    O arquivo permite acompanhar uma execução de fora do terminal (por exemplo, aberto no VS Code) e
    ver se o programa está trabalhando, em pausa ou parado. Cada configuração substitui a anterior,
    para não duplicar linhas quando o programa é chamado mais de uma vez no mesmo processo.
    """

    _FORMAT = "%(asctime)s %(message)s"
    _DATE_FORMAT = "%d/%m %H:%M:%S"
    _QUIET_LOGGERS = ("weasyprint", "fontTools")

    def __init__(self, logs_dir: Path, today: Callable[[], date] = date.today) -> None:
        self._logs_dir = logs_dir
        self._today = today
        self._handlers: list[logging.Handler] = []

    def configure(self) -> Path:
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        path = self._logs_dir / f"{self._today():%Y-%m-%d}.log"
        root = logging.getLogger()
        self.close()
        formatter = logging.Formatter(self._FORMAT, self._DATE_FORMAT)
        self._handlers = [logging.StreamHandler(), logging.FileHandler(path, encoding="utf-8")]
        for handler in self._handlers:
            handler.setFormatter(formatter)
            root.addHandler(handler)
        root.setLevel(logging.INFO)
        for name in self._QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
        return path

    def close(self) -> None:
        root = logging.getLogger()
        for handler in self._handlers:
            root.removeHandler(handler)
            handler.close()
        self._handlers = []

import signal
from types import FrameType, TracebackType
from typing import Self


class TerminationRequested(BaseException):
    """O sistema pediu para o programa encerrar (SIGTERM, enviado pelo `docker stop`).

    Herda de BaseException, como o KeyboardInterrupt, para atravessar os `except Exception` da busca e do
    envio e chegar a quem registra a execução.
    """


class TerminationSignal:
    """Enquanto ativo, transforma o SIGTERM em TerminationRequested.

    No container o Python é o processo 1, e o processo 1 ignora o SIGTERM quando não há tratador: o
    `docker stop` esperava o prazo acabar e matava o programa sem registrar o fim da execução.
    """

    def __init__(self) -> None:
        self._previous: signal.Handlers | None = None

    def __enter__(self) -> Self:
        self._previous = signal.signal(signal.SIGTERM, self._request_termination)
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        signal.signal(signal.SIGTERM, self._previous)

    @staticmethod
    def _request_termination(signum: int, frame: FrameType | None) -> None:
        raise TerminationRequested("Encerramento pedido pelo sistema (SIGTERM).")

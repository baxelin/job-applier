import logging
import math
import random
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from job_applier.models.automation_settings import AutomationSettings, NumberRange

logger = logging.getLogger(__name__)


class Pacer:
    """Controla o ritmo da navegação: atrasos aleatórios entre ações e vagas e pausas longas periódicas.

    As esperas entre vagas e as pausas longas aparecem no log, com a hora de retomada; durante a pausa
    longa, um aviso a cada minuto mostra que o programa não travou.
    """

    _HEARTBEAT_SECONDS = 60

    def __init__(
        self,
        settings: AutomationSettings,
        sleep: Callable[[float], None] = time.sleep,
        uniform: Callable[[float, float], float] = random.uniform,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._uniform = uniform
        self._now = now

    def between_actions(self) -> None:
        self._wait(self._settings.delay_between_actions_seconds)

    def after_job(self, jobs_processed: int) -> None:
        interval = self._settings.delay_between_applications_seconds
        seconds = self._uniform(interval.minimum, interval.maximum)
        logger.info("Próxima vaga em %.0f s.", seconds)
        self._sleep(seconds)
        long_pause = self._settings.long_pause
        if long_pause and jobs_processed % long_pause.every_applications == 0:
            minutes = self._uniform(long_pause.minutes.minimum, long_pause.minutes.maximum)
            self._long_pause(minutes * 60, jobs_processed)

    def _long_pause(self, seconds: float, jobs_processed: int) -> None:
        resume_at = f"{self._now() + timedelta(seconds=seconds):%H:%M}"
        logger.info("Pausa longa de %.0f minutos após %d vagas; retoma às %s.", seconds / 60, jobs_processed, resume_at)
        remaining = seconds
        while remaining > 0:
            step = min(self._HEARTBEAT_SECONDS, remaining)
            self._sleep(step)
            remaining -= step
            if remaining > 0:
                logger.info("Em pausa: faltam %d min (retoma às %s).", math.ceil(remaining / 60), resume_at)

    def _wait(self, interval: NumberRange) -> None:
        self._sleep(self._uniform(interval.minimum, interval.maximum))

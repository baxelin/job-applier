import logging
import random
import time
from collections.abc import Callable

from job_applier.models.automation_settings import AutomationSettings, NumberRange

logger = logging.getLogger(__name__)


class Pacer:
    """Controla o ritmo da navegação: atrasos aleatórios entre ações e vagas e pausas longas periódicas."""

    def __init__(
        self,
        settings: AutomationSettings,
        sleep: Callable[[float], None] = time.sleep,
        uniform: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._uniform = uniform

    def between_actions(self) -> None:
        self._wait(self._settings.delay_between_actions_seconds)

    def after_job(self, jobs_processed: int) -> None:
        self._wait(self._settings.delay_between_applications_seconds)
        long_pause = self._settings.long_pause
        if jobs_processed % long_pause.every_applications == 0:
            minutes = self._uniform(long_pause.minutes.minimum, long_pause.minutes.maximum)
            logger.info("Pausa longa de %.0f minutos após %d vagas.", minutes, jobs_processed)
            self._sleep(minutes * 60)

    def _wait(self, interval: NumberRange) -> None:
        self._sleep(self._uniform(interval.minimum, interval.maximum))

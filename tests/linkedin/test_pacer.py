import logging
from datetime import datetime

from job_applier.linkedin.pacer import Pacer
from job_applier.models.automation_settings import AutomationSettings


class RecordingSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def pacer(settings_data, sleep) -> Pacer:
    return Pacer(
        AutomationSettings.model_validate(settings_data),
        sleep=sleep,
        uniform=lambda low, high: high,
        now=lambda: datetime(2026, 11, 19, 10, 20),
    )


class TestPacer:
    def test_waits_between_actions_within_the_configured_range(self, settings_data):
        sleep = RecordingSleep()

        pacer(settings_data, sleep).between_actions()

        assert sleep.calls == [3]

    def test_waits_after_each_job(self, settings_data):
        sleep = RecordingSleep()

        pacer(settings_data, sleep).after_job(jobs_processed=1)

        assert sleep.calls == [60]

    def test_takes_long_pause_every_n_jobs(self, settings_data):
        sleep = RecordingSleep()

        pacer(settings_data, sleep).after_job(jobs_processed=5)

        assert sleep.calls == [60] + [60] * 10

    def test_long_pause_tells_when_it_resumes_and_how_much_is_left(self, settings_data, caplog):
        caplog.set_level(logging.INFO)

        pacer(settings_data, RecordingSleep()).after_job(jobs_processed=5)

        assert "retoma às 10:30" in caplog.text
        assert "faltam 9 min" in caplog.text
        assert "faltam 1 min" in caplog.text

    def test_long_pause_is_optional(self, settings_data):
        del settings_data["long_pause"]
        sleep = RecordingSleep()

        pacer(settings_data, sleep).after_job(jobs_processed=5)

        assert sleep.calls == [60]

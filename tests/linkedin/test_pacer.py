from job_applier.linkedin.pacer import Pacer
from job_applier.models.automation_settings import AutomationSettings


class RecordingSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def pacer(settings_data, sleep) -> Pacer:
    return Pacer(AutomationSettings.model_validate(settings_data), sleep=sleep, uniform=lambda low, high: high)


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

        assert sleep.calls == [60, 10 * 60]

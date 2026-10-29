import pytest
from pydantic import ValidationError

from job_applier.models.automation_settings import AutomationSettings, NumberRange


class TestNumberRange:
    def test_accepts_equal_limits(self):
        assert NumberRange(minimum=5, maximum=5).maximum == 5

    def test_rejects_minimum_above_maximum(self):
        with pytest.raises(ValidationError, match="maior que o máximo"):
            NumberRange(minimum=10, maximum=5)


class TestAutomationSettings:
    def test_accepts_valid_data(self, settings_data):
        settings = AutomationSettings.model_validate(settings_data)

        assert settings.daily_application_limit == 10

    def test_rejects_zero_daily_limit(self, settings_data):
        settings_data["daily_application_limit"] = 0

        with pytest.raises(ValidationError):
            AutomationSettings.model_validate(settings_data)

    def test_rejects_unknown_experience_level(self, settings_data):
        settings_data["filters"]["experience_levels"] = ["junior"]

        with pytest.raises(ValidationError):
            AutomationSettings.model_validate(settings_data)

    def test_requires_at_least_one_search(self, settings_data):
        settings_data["searches"] = []

        with pytest.raises(ValidationError):
            AutomationSettings.model_validate(settings_data)

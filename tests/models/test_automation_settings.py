import pytest
from pydantic import ValidationError

from job_applier.models.automation_settings import AutomationSettings, NumberRange, WorkplaceType


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

    def test_search_without_own_workplace_types_uses_global_filter(self, settings_data):
        settings = AutomationSettings.model_validate(settings_data)

        assert settings.searches[0].workplace_types is None

    def test_search_can_restrict_workplace_types(self, settings_data):
        settings_data["searches"].append(
            {"keywords": "Junior Developer", "location": "Worldwide", "workplace_types": ["remote"]}
        )

        settings = AutomationSettings.model_validate(settings_data)

        assert settings.searches[1].workplace_types == [WorkplaceType.REMOTE]

    def test_rejects_search_with_empty_workplace_types(self, settings_data):
        settings_data["searches"][0]["workplace_types"] = []

        with pytest.raises(ValidationError):
            AutomationSettings.model_validate(settings_data)

    def test_requires_at_least_one_search(self, settings_data):
        settings_data["searches"] = []

        with pytest.raises(ValidationError):
            AutomationSettings.model_validate(settings_data)

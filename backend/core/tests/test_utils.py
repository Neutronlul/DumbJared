from typing import TYPE_CHECKING

import pytest
from django.core.exceptions import ImproperlyConfigured

from core.utils.configuration_guard import require_settings

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper


class TestConfigurationGuard:
    class TestRequireSettings:
        @pytest.mark.parametrize(
            "value",
            [
                pytest.param("", id="empty string"),
                pytest.param(None, id="None"),
                pytest.param([], id="empty list"),
                pytest.param({}, id="empty dict"),
                pytest.param((), id="empty tuple"),
                pytest.param(0, id="zero"),
                pytest.param(False, id="False"),
            ],
        )
        def test_missing_setting(
            self,
            value: object,
            settings: SettingsWrapper,
        ) -> None:
            settings.TEST_SETTING = value

            with pytest.raises(
                ImproperlyConfigured,
                match=(
                    "Missing required environment configuration for testing: "
                    "TEST_SETTING"
                ),
            ):
                require_settings("TEST_SETTING", reason="testing")

        def test_missing_setting_multiple(self, settings: SettingsWrapper) -> None:
            settings.TEST_SETTING = ""
            settings.ANOTHER_SETTING = None

            with pytest.raises(
                ImproperlyConfigured,
                match=(
                    "Missing required environment configuration for testing: "
                    "TEST_SETTING, ANOTHER_SETTING"
                ),
            ):
                require_settings("TEST_SETTING", "ANOTHER_SETTING", reason="testing")

        @pytest.mark.parametrize(
            "value",
            [
                pytest.param("non-empty string", id="non-empty string"),
                pytest.param([1, 2, 3], id="list of ints"),
                pytest.param(["a", "b", "c"], id="list of strings"),
                pytest.param({"key": "value"}, id="dict with values"),
                pytest.param((1, 2), id="tuple with values"),
                pytest.param(42, id="positive integer"),
                pytest.param(True, id="True"),
                pytest.param(3.14, id="float"),
                pytest.param({"nested": {"key": "value"}}, id="nested dict"),
                pytest.param([[], []], id="list of empty lists"),
                pytest.param("a" * 1000, id="long string"),
                pytest.param(-1, id="negative integer"),
            ],
        )
        def test_valid_setting(self, value: object, settings: SettingsWrapper) -> None:
            settings.TEST_SETTING = value

            require_settings("TEST_SETTING", reason="testing")

        def test_valid_settings_multiple(self, settings: SettingsWrapper) -> None:
            settings.TEST_SETTING = "valid"
            settings.ANOTHER_SETTING = [1, 2, 3]

            require_settings("TEST_SETTING", "ANOTHER_SETTING", reason="testing")

        def test_some_valid_some_missing(self, settings: SettingsWrapper) -> None:
            settings.TEST_SETTING = "valid"
            settings.ANOTHER_SETTING = ""

            with pytest.raises(
                ImproperlyConfigured,
                match=(
                    "Missing required environment configuration for testing: "
                    "ANOTHER_SETTING"
                ),
            ):
                require_settings("TEST_SETTING", "ANOTHER_SETTING", reason="testing")

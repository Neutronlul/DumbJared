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
                "",
                None,
                [],
                {},
                (),
                0,
                False,  # This might be a problem in the future for boolean settings
            ],
            ids=[
                "empty string",
                "None",
                "empty list",
                "empty dict",
                "empty tuple",
                "zero",
                "False",
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
                "non-empty string",
                [1, 2, 3],
                ["a", "b", "c"],
                {"key": "value"},
                (1, 2),
                42,
                True,
                3.14,
                {"nested": {"key": "value"}},
                [[], []],
                "a" * 1000,
                -1,
            ],
            ids=[
                "non-empty string",
                "list of ints",
                "list of strings",
                "dict with values",
                "tuple with values",
                "positive integer",
                "True",
                "float",
                "nested dict",
                "list of empty lists",
                "long string",
                "negative integer",
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

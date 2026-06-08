from typing import TYPE_CHECKING

import pytest
from django.core.management import call_command
from django.db import DatabaseError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


MIGRATION_EXECUTOR_PATH = "core.management.commands.db_isready.MigrationExecutor"


class TestDbIsReady:
    def test_exit_0(
        self,
        mocker: MockerFixture,
    ) -> None:
        mock_executor = mocker.patch(MIGRATION_EXECUTOR_PATH)
        mock_executor.return_value.loader.graph.leaf_nodes.return_value = []
        mock_executor.return_value.migration_plan.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            call_command("db_isready")

        assert exc_info.value.code == 0

    def test_exit_1(
        self,
        mocker: MockerFixture,
    ) -> None:
        mock_executor = mocker.patch(MIGRATION_EXECUTOR_PATH)
        mock_executor.return_value.loader.graph.leaf_nodes.return_value = []
        mock_executor.return_value.migration_plan.return_value = [
            ("api", "0001_initial"),
        ]

        with pytest.raises(SystemExit) as exc_info:
            call_command("db_isready")

        assert exc_info.value.code == 1

    def test_exit_2(
        self,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            MIGRATION_EXECUTOR_PATH,
            side_effect=DatabaseError("Connection refused"),
        )

        with pytest.raises(SystemExit) as exc_info:
            call_command("db_isready")

        assert exc_info.value.code == 2  # noqa: PLR2004

    def test_exit_3(
        self,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            MIGRATION_EXECUTOR_PATH,
            side_effect=RuntimeError("Something exploded"),
        )

        with pytest.raises(SystemExit) as exc_info:
            call_command("db_isready")

        assert exc_info.value.code == 3  # noqa: PLR2004


class TestSeedData:
    pass

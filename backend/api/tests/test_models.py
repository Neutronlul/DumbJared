from typing import TYPE_CHECKING, Any

import pytest
from django.db.utils import DataError, IntegrityError
from model_bakery import baker

from api.exceptions import TeamHasNoNamesError

if TYPE_CHECKING:
    from collections.abc import Callable

    from api.models import Quizmaster, Team
    from api.models import TimeStampedModel as Model

pytestmark = pytest.mark.django_db

TEST_TEAM_ID = 1234


def model_fixtures(recipe_name: str) -> Callable[[type[Any]], type[Any]]:
    """Add model fixtures to a test class."""

    def decorator(cls: type[Any]) -> type[Any]:
        @pytest.fixture
        def instance(_self: object) -> Model:
            return baker.make_recipe(recipe_name)

        @pytest.fixture
        def make_instance(_self: object) -> Callable[..., Model]:
            def _make(**kwargs: object) -> Model:
                return baker.make_recipe(recipe_name, **kwargs)

            return _make

        cls.instance = instance
        cls.make_instance = make_instance

        return cls

    return decorator


@model_fixtures("api.tests.quizmaster")
class TestQuizmaster:
    def test_creation(self, instance: Quizmaster) -> None:
        assert instance.pk is not None
        assert instance.name == "John Doe"

    def test_name_must_not_be_blank(
        self,
        make_instance: Callable[..., Quizmaster],
    ) -> None:
        with pytest.raises(IntegrityError):
            make_instance(name="")

    def test_unique_names(self, make_instance: Callable[..., Quizmaster]) -> None:
        make_instance()
        with pytest.raises(IntegrityError):
            make_instance()

    def test_name_max_length(self, make_instance: Callable[..., Quizmaster]) -> None:
        with pytest.raises(DataError):
            make_instance(name="A" * 101)

    def test_string_representation(self, instance: Quizmaster) -> None:
        assert str(instance) == instance.name == "John Doe"


@model_fixtures("api.tests.team")
class TestTeam:
    def test_non_guest_creation(self, make_instance: Callable[..., Team]) -> None:
        team = make_instance(
            team_id=TEST_TEAM_ID,
            names__name="Test Team",
            names__guest=False,
        )
        assert team.team_id == TEST_TEAM_ID
        assert team.names.first().name == "Test Team"
        assert team.names.first().team == team
        assert team.names.first().guest is False

    def test_guest_creation(self, make_instance: Callable[..., Team]) -> None:
        team = make_instance(team_id=None, names__name="Guest Team", names__guest=True)
        assert team.team_id is None
        assert team.names.first().name == "Guest Team"
        assert team.names.first().team == team
        assert team.names.first().guest is True

    def test_non_guest_string_representation(
        self,
        make_instance: Callable[..., Team],
    ) -> None:
        team = make_instance(
            team_id=TEST_TEAM_ID,
            names__name="Test Team",
            names__guest=False,
        )
        assert str(team) == f"{TEST_TEAM_ID} | Test Team"

    def test_guest_string_representation(
        self,
        make_instance: Callable[..., Team],
    ) -> None:
        team = make_instance(team_id=None, names__name="Guest Team", names__guest=True)
        assert str(team) == "Guest | Guest Team"

    def test_string_representation_truncation(
        self,
        make_instance: Callable[..., Team],
    ) -> None:
        long_name = "A" * 300
        team = make_instance(names__name=long_name, names__guest=False)
        expected_truncated_name = long_name[:97] + "..."
        assert str(team) == f"1 | {expected_truncated_name}"

    def test_must_have_name(self, make_instance: Callable[..., Team]) -> None:
        with pytest.raises(TeamHasNoNamesError):
            str(make_instance())

    def test_unique_team_id(self, make_instance: Callable[..., Team]) -> None:
        make_instance(team_id=TEST_TEAM_ID)
        with pytest.raises(IntegrityError):
            make_instance(team_id=TEST_TEAM_ID)

    def test_team_id_must_be_positive(self, make_instance: Callable[..., Team]) -> None:
        with pytest.raises(IntegrityError):
            make_instance(team_id=-1)

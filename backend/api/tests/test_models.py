from django.db.utils import IntegrityError, DataError

from model_bakery import baker

import pytest


pytestmark = pytest.mark.django_db


def model_fixtures(recipe_name: str):
    """Decorator to add model fixtures to a test class."""

    def decorator(cls):
        @pytest.fixture
        def instance(self):
            return baker.make_recipe(recipe_name)

        @pytest.fixture
        def make_instance(self):
            def _make(**kwargs):
                return baker.make_recipe(recipe_name, **kwargs)

            return _make

        cls.instance = instance
        cls.make_instance = make_instance

        return cls

    return decorator


@model_fixtures("api.tests.quizmaster")
class TestQuizmaster:
    def test_creation(self, instance):
        assert instance.id is not None
        assert instance.name == "John Doe"

    def test_name_must_not_be_blank(self, make_instance):
        with pytest.raises(IntegrityError):
            make_instance(name="")

    def test_unique_names(self, make_instance):
        make_instance()
        with pytest.raises(IntegrityError):
            make_instance()

    def test_name_max_length(self, make_instance):
        with pytest.raises(DataError):
            make_instance(name="A" * 101)

    def test_string_representation(self, instance):
        assert str(instance) == instance.name == "John Doe"


@model_fixtures("api.tests.team")
class TestTeam:
    def test_non_guest_creation(self, make_instance):
        team = make_instance(team_id=1234, names__name="Test Team", names__guest=False)
        assert team.team_id == 1234
        assert team.names.first().name == "Test Team"
        assert team.names.first().team == team
        assert team.names.first().guest is False

    def test_guest_creation(self, make_instance):
        team = make_instance(team_id=None, names__name="Guest Team", names__guest=True)
        assert team.team_id is None
        assert team.names.first().name == "Guest Team"
        assert team.names.first().team == team
        assert team.names.first().guest is True

    def test_non_guest_string_representation(self, make_instance):
        team = make_instance(team_id=5678, names__name="Test Team", names__guest=False)
        assert str(team) == "5678 | Test Team"

    def test_guest_string_representation(self, make_instance):
        team = make_instance(team_id=None, names__name="Guest Team", names__guest=True)
        assert str(team) == "Guest | Guest Team"

    def test_string_representation_truncation(self, make_instance):
        long_name = "A" * 300
        team = make_instance(names__name=long_name, names__guest=False)
        expected_truncated_name = long_name[:97] + "..."
        assert str(team) == f"1 | {expected_truncated_name}"

    def test_must_have_name(self, make_instance):
        with pytest.raises(ValueError):
            str(make_instance())

    def test_unique_team_id(self, make_instance):
        make_instance(team_id=4321)
        with pytest.raises(IntegrityError):
            make_instance(team_id=4321)

    def test_team_id_must_be_positive(self, make_instance):
        with pytest.raises(IntegrityError):
            make_instance(team_id=-1)


# @model_fixtures("api.tests.teamname")
# class TestTeamName:
#     def test_creation(self, instance):
#         assert instance.id is not None
#         assert instance.name == "Team Alpha"
#         assert instance.guest is False


# class VenueTestModel(TestCase):
#     def setUp(self):
#         self.venue = baker.make("Venue", name="Test Venue", url="http://testvenue.com")

#     def test_venue_creation(self):
#         self.assertEqual(self.venue.name, "Test Venue")
#         self.assertEqual(self.venue.url, "http://testvenue.com")

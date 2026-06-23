import pytest
from django.db.utils import DataError, IntegrityError
from model_bakery import baker

from api.exceptions import TeamHasNoNamesError
from api.models import Quizmaster, Team

pytestmark = pytest.mark.django_db


TEST_TEAM_ID = 1234


class TestQuizmaster:
    def test_creation(self) -> None:
        qm = baker.make_recipe("api.tests.quizmaster")
        assert qm.pk is not None
        assert qm.name is not None

    def test_name_must_not_be_blank(self) -> None:
        with pytest.raises(IntegrityError):
            baker.make(Quizmaster, name="")

    def test_name_must_be_unique(self) -> None:
        baker.make(Quizmaster, name="Keef Girgo")
        with pytest.raises(IntegrityError):
            baker.make(Quizmaster, name="Keef Girgo")

    def test_name_max_length(self) -> None:
        with pytest.raises(DataError):
            baker.make(Quizmaster, name="A" * 101)

    def test_string_representation(self) -> None:
        qm = baker.make(Quizmaster, name="Test Quizmaster")
        assert str(qm) == qm.name


class TestTeam:
    def test_non_guest_creation(self) -> None:
        team = baker.make(
            Team,
            team_id=TEST_TEAM_ID,
            names__name="Test Team",
            names__guest=False,
        )
        assert team.team_id == TEST_TEAM_ID

        name = team.names.first()
        assert name is not None
        assert name.name == "Test Team"
        assert name.team == team
        assert name.guest is False

    def test_guest_creation(self) -> None:
        team = baker.make(
            Team,
            team_id=None,
            names__name="Guest Team",
            names__guest=True,
        )
        assert team.team_id is None

        name = team.names.first()
        assert name is not None
        assert name.name == "Guest Team"
        assert name.team == team
        assert name.guest is True

    def test_non_guest_string_representation(self) -> None:
        team = baker.make(
            Team,
            team_id=TEST_TEAM_ID,
            names__name="Test Team",
            names__guest=False,
        )
        assert str(team) == f"{TEST_TEAM_ID} | Test Team"

    def test_guest_string_representation(self) -> None:
        team = baker.make(
            Team,
            team_id=None,
            names__name="Guest Team",
            names__guest=True,
        )
        assert str(team) == "Guest | Guest Team"

    def test_string_representation_truncation(self) -> None:
        long_name = "A" * 300
        team = baker.make(Team, team_id=1, names__name=long_name, names__guest=False)
        expected_truncated_name = long_name[:99] + "…"
        assert str(team) == f"1 | {expected_truncated_name}"

    def test_must_have_name(self) -> None:
        with pytest.raises(TeamHasNoNamesError):
            str(baker.make(Team))

    def test_unique_team_id(self) -> None:
        baker.make(Team, team_id=TEST_TEAM_ID)
        with pytest.raises(IntegrityError):
            baker.make(Team, team_id=TEST_TEAM_ID)

    def test_team_id_must_be_positive(self) -> None:
        with pytest.raises(IntegrityError):
            baker.make(Team, team_id=-1)


class TestEvent:
    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("123456", id="six digits"),
            pytest.param("", id="blank"),
        ],
    )
    def test_valid_join_code(self, code: str) -> None:
        baker.make_recipe("api.tests.event", join_code=code)

    @pytest.mark.parametrize(
        ("code", "exception"),
        [
            pytest.param("1234567", DataError, id="too long"),
            pytest.param("12345", IntegrityError, id="too short"),
            pytest.param("ABCDEF", IntegrityError, id="non-numeric"),
            pytest.param("      ", IntegrityError, id="whitespace"),
            pytest.param("١٢٣٤٥٦", IntegrityError, id="arabic digits"),
        ],
    )
    def test_invalid_join_code(
        self,
        code: str,
        exception: type[DataError | IntegrityError],
    ) -> None:
        with pytest.raises(exception):
            baker.make_recipe("api.tests.event", join_code=code)

    def test_join_code_allows_duplicates(self) -> None:
        code = "123456"
        event1 = baker.make_recipe("api.tests.event", join_code=code)
        event2 = baker.make_recipe("api.tests.event", join_code=code)
        assert event1.join_code == event2.join_code == code

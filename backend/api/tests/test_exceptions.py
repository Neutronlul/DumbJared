from api.exceptions import TeamHasNoNamesError


class TestTeamHasNoNamesError:
    def test_message(self) -> None:
        exc = TeamHasNoNamesError()
        assert str(exc) == "Team has no associated names"

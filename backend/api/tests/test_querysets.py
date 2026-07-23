import pytest
from model_bakery import baker

from api.models import Event, Game, GameType, Member, Quizmaster, Team, Theme, Venue

pytestmark = pytest.mark.django_db


class TestMemberQuerySet:
    class TestWithAttendanceCount:
        def test_member_with_no_attendances_has_zero_count(self) -> None:
            member = baker.make(Member)

            result = Member.objects.with_attendance_count().get(pk=member.pk)

            assert result.attendance_count == 0

    class TestWithAverageScore:
        def test_member_with_no_scores_has_none_average(self) -> None:
            member = baker.make(Member)

            result = Member.objects.with_average_score().get(pk=member.pk)

            assert result.average_score is None

    class TestWithFirstAttendedDate:
        def test_member_with_no_attendances_has_none_first_attended_date(self) -> None:
            member = baker.make(Member)

            result = Member.objects.with_first_attended_date().get(pk=member.pk)

            assert result.first_attended_date is None

    class TestWithLastAttendedDate:
        def test_member_with_no_attendances_has_none_last_attended_date(self) -> None:
            member = baker.make(Member)

            result = Member.objects.with_last_attended_date().get(pk=member.pk)

            assert result.last_attended_date is None


class TestTeamQuerySet:
    class TestWithEventParticipationsCount:
        def test_team_with_no_event_participations_has_zero_count(self) -> None:
            team = baker.make(Team)

            result = Team.objects.with_event_participations_count().get(
                pk=team.pk,
            )

            assert result.event_participations_count == 0

    class TestWithLastSeenDate:
        def test_team_with_no_event_participations_has_none_last_seen_date(
            self,
        ) -> None:
            team = baker.make(Team)

            result = Team.objects.with_last_seen_date().get(pk=team.pk)

            assert result.last_seen_date is None


class TestEventQuerySet:
    class TestWithTeamParticipationsCount:
        def test_event_with_no_team_participations_has_zero_count(self) -> None:
            event = baker.make_recipe("api.tests.event")

            result = Event.objects.with_team_participations_count().get(
                pk=event.pk,
            )

            assert result.team_participations_count == 0


class TestGameQuerySet:
    class TestWithEventCount:
        def test_game_with_no_events_has_zero_count(self) -> None:
            game = baker.make_recipe("api.tests.game")

            result = Game.objects.with_event_count().get(pk=game.pk)

            assert result.event_count == 0


class TestGameTypeQuerySet:
    class TestWithOfficialGamesCount:
        def test_game_type_with_no_official_games_has_zero_count(self) -> None:
            game_type = baker.make(GameType)

            result = GameType.objects.with_official_games_count().get(
                pk=game_type.pk,
            )

            assert result.official_games_count == 0


class TestQuizmasterQuerySet:
    class TestWithEventsOfficiatedCount:
        def test_quizmaster_with_no_events_officiated_has_zero_count(self) -> None:
            quizmaster = baker.make(Quizmaster)

            result = Quizmaster.objects.with_events_officiated_count().get(
                pk=quizmaster.pk,
            )

            assert result.events_officiated_count == 0


class TestThemeQuerySet:
    class TestWithEventCount:
        def test_theme_with_no_events_has_zero_count(self) -> None:
            theme = baker.make(Theme)

            result = Theme.objects.with_event_count().get(pk=theme.pk)

            assert result.event_count == 0

    class TestWithLastUsedDate:
        def test_theme_with_no_events_has_none_last_used_date(self) -> None:
            theme = baker.make(Theme)

            result = Theme.objects.with_last_used_date().get(pk=theme.pk)

            assert result.last_used_date is None


class TestVenueQuerySet:
    class TestWithOfficialGameCount:
        def test_venue_with_no_official_games_has_zero_count(self) -> None:
            venue = baker.make_recipe("api.tests.venue")

            result = Venue.objects.with_official_game_count().get(pk=venue.pk)

            assert result.official_game_count == 0

    class TestWithCustomGameCount:
        def test_venue_with_no_custom_games_has_zero_count(self) -> None:
            venue = baker.make_recipe("api.tests.venue")

            result = Venue.objects.with_custom_game_count().get(pk=venue.pk)

            assert result.custom_game_count == 0

    class TestWithEventCount:
        def test_venue_with_no_events_has_zero_count(self) -> None:
            venue = baker.make_recipe("api.tests.venue")

            result = Venue.objects.with_event_count().get(pk=venue.pk)

            assert result.event_count == 0

    class TestWithQuizmasterCount:
        def test_venue_with_no_quizmasters_has_zero_count(self) -> None:
            venue = baker.make_recipe("api.tests.venue")

            result = Venue.objects.with_quizmaster_count().get(pk=venue.pk)

            assert result.quizmaster_count == 0

    class TestWithTeamCount:
        def test_venue_with_no_teams_has_zero_count(self) -> None:
            venue = baker.make_recipe("api.tests.venue")

            result = Venue.objects.with_team_count().get(pk=venue.pk)

            assert result.team_count == 0

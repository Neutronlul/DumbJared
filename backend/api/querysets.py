from django.db.models import Avg, Count, Max, Min, Q, QuerySet


class MemberQuerySet(QuerySet):
    def with_attendance_count(self) -> MemberQuerySet:
        return self.annotate(
            attendance_count=Count("event_attendances", distinct=True),
        )

    def with_average_score(self) -> MemberQuerySet:
        return self.annotate(
            average_score=Avg(
                "event_attendances__team_event_participation__score",
            ),
        )

    def with_first_attended_date(self) -> MemberQuerySet:
        return self.annotate(
            first_attended_date=Min(
                "event_attendances__team_event_participation__event__date",
            ),
        )

    def with_last_attended_date(self) -> MemberQuerySet:
        return self.annotate(
            last_attended_date=Max(
                "event_attendances__team_event_participation__event__date",
            ),
        )


class TeamQuerySet(QuerySet):
    def with_event_participations_count(self) -> TeamQuerySet:
        return self.annotate(
            event_participations_count=Count("event_participations"),
        )

    def with_last_seen_date(self) -> TeamQuerySet:
        return self.annotate(
            last_seen_date=Max("event_participations__event__date"),
        )


class EventQuerySet(QuerySet):
    def with_team_participations_count(self) -> EventQuerySet:
        return self.annotate(
            team_participations_count=Count("team_participations"),
        )


class GameQuerySet(QuerySet):
    def with_event_count(self) -> GameQuerySet:
        return self.annotate(
            event_count=Count("events"),
        )


class GameTypeQuerySet(QuerySet):
    def with_official_games_count(self) -> GameTypeQuerySet:
        return self.annotate(
            official_games_count=Count("games", filter=Q(games__day__isnull=False)),
        )


class QuizmasterQuerySet(QuerySet):
    def with_events_officiated_count(self) -> QuizmasterQuerySet:
        return self.annotate(
            events_officiated_count=Count("events", distinct=True),
        )


class ThemeQuerySet(QuerySet):
    def with_event_count(self) -> ThemeQuerySet:
        return self.annotate(
            event_count=Count("events"),
        )

    def with_last_used_date(self) -> ThemeQuerySet:
        return self.annotate(
            last_used_date=Max("events__date"),
        )


class VenueQuerySet(QuerySet):
    def with_official_game_count(self) -> VenueQuerySet:
        return self.annotate(
            official_game_count=Count(
                "games",
                filter=Q(games__day__isnull=False),
                distinct=True,
            ),
        )

    def with_custom_game_count(self) -> VenueQuerySet:
        return self.annotate(
            custom_game_count=Count(
                "games",
                filter=Q(games__day__isnull=True),
                distinct=True,
            ),
        )

    def with_event_count(self) -> VenueQuerySet:
        return self.annotate(
            event_count=Count("games__events", distinct=True),
        )

    def with_quizmaster_count(self) -> VenueQuerySet:
        return self.annotate(
            quizmaster_count=Count("games__events__quizmaster", distinct=True),
        )

    def with_team_count(self) -> VenueQuerySet:
        return self.annotate(
            team_count=Count("games__events__team_participations__team", distinct=True),
        )

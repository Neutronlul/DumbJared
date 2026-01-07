from calendar import day_name

from django.core.validators import MinLengthValidator
from django.db import models

from typing import TYPE_CHECKING


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Quizmaster(TimeStampedModel):
    name = models.CharField(
        max_length=100, unique=True, validators=[MinLengthValidator(1)]
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="quizmaster_name_not_blank",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Team(TimeStampedModel):
    team_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-event_participations__event__date"]

    if TYPE_CHECKING:
        names: "models.QuerySet[TeamName]"

    def __str__(self):
        _account = str(self.team_id) if self.team_id is not None else "Guest"
        if latest_name := self.names.first():
            latest_name = latest_name.name
            _name = f"{latest_name[:97]}..." if len(latest_name) > 100 else latest_name
        else:
            raise ValueError("Team has no associated names.")
        return f"{_account} | {_name}"


class TeamName(TimeStampedModel):
    name = models.CharField(
        max_length=300,  # Blame MeatOrgy
        validators=[MinLengthValidator(1)],
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="names")
    guest = models.BooleanField(editable=False)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["name", "team"],
                name="unique_team_name",
            ),
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(guest=True),
                name="unique_guest_team_name",
            ),
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(guest=True),
                name="guest_team_single_name",
            ),
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="team_name_not_blank",
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Member(TimeStampedModel):
    name = models.CharField(
        max_length=100, unique=True, validators=[MinLengthValidator(1)]
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="member_name_not_blank",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


# TODO: Maybe add is_booth field?
class Table(TimeStampedModel):
    table_id = models.PositiveSmallIntegerField(
        unique=True
    )  # TODO: Maybe change to CharField for ids like "R1", "L2", etc.
    name = models.CharField(max_length=100, null=True, blank=True, unique=True)
    is_upstairs = models.BooleanField(default=False)

    def __str__(self):
        return self.name if self.name else str(self.table_id)


class Theme(TimeStampedModel):
    name = models.CharField(
        max_length=50, unique=True, validators=[MinLengthValidator(1)]
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="theme_name_not_blank",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Round(TimeStampedModel):
    number = models.PositiveSmallIntegerField("Round number", unique=True)
    name = models.CharField(
        "Round name", max_length=100, unique=True, validators=[MinLengthValidator(1)]
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(number__gte=1, number__lte=7),
                name="round_number_1_to_7",
            ),
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="round_name_not_blank",
            ),
        ]
        ordering = ["number"]

    def __str__(self):
        return f"Round {self.number}: {self.name}"


class Glossary(TimeStampedModel):
    acronym = models.CharField(
        max_length=20, unique=True, validators=[MinLengthValidator(1)]
    )
    definition = models.TextField(validators=[MinLengthValidator(1)])

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Glossary Entry"
        verbose_name_plural = "Glossary Entries"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(acronym=""),
                name="acronym_not_blank",
            ),
            models.CheckConstraint(
                condition=~models.Q(definition=""),
                name="definition_not_blank",
            ),
        ]
        ordering = ["acronym"]

    def __str__(self):
        return (
            f"{self.acronym} | {self.definition[:97]}..."
            if len(self.definition) > 100
            else f"{self.acronym} | {self.definition}"
        )


class Venue(TimeStampedModel):
    name = models.CharField(
        max_length=100,
        unique=True,  # TODO: Should this really be unique?
        validators=[MinLengthValidator(1)],
    )
    url = models.URLField(max_length=200, unique=True)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="venue_name_not_blank",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class GameType(TimeStampedModel):
    name = models.CharField(
        max_length=200, unique=True, validators=[MinLengthValidator(1)]
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="game_type_name_not_blank",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Game(TimeStampedModel):
    game_type = models.ForeignKey(
        GameType, on_delete=models.CASCADE, related_name="games"
    )
    day = models.PositiveSmallIntegerField(
        choices=[(i, day_name[i]) for i in range(7)],  # 0=Monday, 6=Sunday
        null=True,
        blank=True,
    )
    time = models.TimeField(
        null=True,
        blank=True,
    )
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="games")

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["game_type", "day", "time", "venue"],
                condition=models.Q(day__isnull=False),
                name="unique_official_game",
            ),
            models.UniqueConstraint(
                fields=["game_type", "venue"],
                condition=models.Q(day__isnull=True),
                name="unique_unofficial_game",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(day__isnull=True) | models.Q(day__gte=0, day__lte=6)
                ),
                name="day_range_0_to_6",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(day__isnull=True, time__isnull=True)
                    | models.Q(day__isnull=False, time__isnull=False)
                ),
                name="day_time_both_null_or_notnull",
            ),
        ]

    def __str__(self):
        return f"{self.venue.name} | {self.game_type.name}" + (
            f", {day_name[self.day]}s at {self.time}" if self.day is not None else ""
        )


class Event(TimeStampedModel):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="events",
    )
    date = models.DateField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    quizmaster = models.ForeignKey(
        Quizmaster,
        on_delete=models.CASCADE,
        related_name="events",
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["game", "date"],
                name="unique_game_date_event",
            )
        ]
        ordering = ["-date"]

    def __str__(self):
        base = f"{self.game.game_type.name} - {self.game.venue.name} - {self.date} - {self.quizmaster.name}"
        return f"{base} - {self.theme.name}" if self.theme else base


class TeamEventParticipation(TimeStampedModel):
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="event_participations"
    )
    team_name = models.ForeignKey(
        TeamName, on_delete=models.CASCADE, related_name="event_participations"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="team_participations"
    )
    score = models.SmallIntegerField()
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_participations",
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["team", "event"], name="unique_team_event_participation"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    score__gte=-1,
                    score__lte=112,  # It should be 111 but whatever
                ),
                name="valid_score",
            ),
        ]
        ordering = ["-event__date", "-score"]

    def __str__(self):
        base = f"{self.team_name} - {self.event.date} - {self.score} points"  # TODO: Maybe change this to allow for multiple times
        return f"{base} at {self.table.name}" if self.table else base


class MemberAttendance(TimeStampedModel):
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="event_attendances"
    )
    team_event_participation = models.ForeignKey(
        TeamEventParticipation,
        on_delete=models.CASCADE,
        related_name="member_attendances",
    )
    notes = models.TextField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["member", "team_event_participation"],
                name="unique_member_team_event_participation_attendance",
            )
        ]
        ordering = ["team_event_participation__event__date", "member__name"]

    def __str__(self):
        return f"{self.team_event_participation.event.date} - {self.member.name}"  # type: ignore TODO: Check date vs time


class Vote(TimeStampedModel):
    RIGHT = "R"
    WRONG = "W"
    ABSTAINED = "A"
    VOTING_CHOICES = (
        (RIGHT, "Right"),
        (WRONG, "Wrong"),
        (ABSTAINED, "Abstained"),
    )
    member_attendance = models.ForeignKey(
        MemberAttendance, on_delete=models.CASCADE, related_name="votes"
    )
    vote = models.CharField(max_length=1, choices=VOTING_CHOICES, default=ABSTAINED)
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="votes")
    is_double_or_nothing = models.BooleanField("Double or nothing vote", default=False)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["member_attendance", "round"], name="unique_vote"
            )
        ]

    def __str__(self):
        return f"{self.event.date} - {self.member.name} - {self.get_vote_display()}"  # type: ignore TODO: Check date vs time

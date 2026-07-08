from calendar import day_name
from typing import TYPE_CHECKING

from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils.text import Truncator

from api.querysets import MemberQuerySet
from core.constants import HEX_24_REGEX, JOIN_CODE_REGEX, MAX_TEAM_SCORE, MIN_TEAM_SCORE
from core.models import TimeStampedModel
from core.validators import validate_not_empty_string
from scraper.models import GeocodedAddress

from .exceptions import TeamHasNoNamesError

if TYPE_CHECKING:
    from datetime import date


class Quizmaster(TimeStampedModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[validate_not_empty_string],
    )

    if TYPE_CHECKING:
        event_officiated_count: int

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="quizmaster_name_not_blank",
            ),
        )
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Team(TimeStampedModel):
    team_id = models.PositiveIntegerField(
        verbose_name="Team ID",
        null=True,
        blank=True,
        unique=True,
    )

    if TYPE_CHECKING:
        names: models.QuerySet[TeamName]

        latest_name: str
        venue_url: str
        event_participations_count: int
        last_seen_date: date

    def __str__(self) -> str:
        _account = str(self.team_id) if self.team_id is not None else "Guest"
        if latest_name := self.names.first():
            _name = Truncator(latest_name.name).chars(100)
        else:
            raise TeamHasNoNamesError
        return f"{_account} | {_name}"


class TeamName(TimeStampedModel):
    team = models.ForeignKey(
        to=Team,
        on_delete=models.CASCADE,
        related_name="names",
    )

    name = models.CharField(
        max_length=300,  # Blame MeatOrgy
        validators=[validate_not_empty_string],
    )

    guest = models.BooleanField(editable=False)

    class Meta(TimeStampedModel.Meta):
        constraints = (
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
        )
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Member(TimeStampedModel):
    objects = MemberQuerySet.as_manager()

    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[validate_not_empty_string],
    )

    if TYPE_CHECKING:
        events_attended_count: int
        first_attended_date: date
        last_attended_date: date

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="member_name_not_blank",
            ),
        )
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Table(TimeStampedModel):
    table_id = models.CharField(
        verbose_name="Table ID",
        max_length=10,
        unique=True,
    )
    name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
    )
    is_upstairs = models.BooleanField(default=False)

    if TYPE_CHECKING:
        seatings_count: int

    def __str__(self) -> str:
        return self.name or str(self.table_id)


class Theme(TimeStampedModel):
    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[validate_not_empty_string],
    )

    if TYPE_CHECKING:
        event_count: int
        last_used: date | None

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="theme_name_not_blank",
            ),
        )
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class RoundType(TimeStampedModel):
    name = models.CharField(
        verbose_name="Round name",
        max_length=100,
        validators=[validate_not_empty_string],
    )
    number = models.PositiveSmallIntegerField(
        verbose_name="Round number",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(8),  # This is to account for tiebreaker rounds
        ],
        help_text="The round's order number in the game, 1-indexed",
    )
    double_or_nothing = models.BooleanField(
        default=True,
        help_text="Whether or not this round allows for double or nothing",
    )

    if TYPE_CHECKING:
        votes_held_count: int

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=models.Q(number__gte=1, number__lte=8),
                name="round_number_1_to_8",
            ),
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="round_name_not_blank",
            ),
            models.UniqueConstraint(
                fields=["number", "double_or_nothing"],
                name="unique_round_number_double_or_nothing",
            ),
        )
        ordering = ("number", "double_or_nothing")

    def __str__(self) -> str:
        return f"Round {self.number}: {self.name}"


class Glossary(TimeStampedModel):
    acronym = models.CharField(
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(1)],
    )
    definition = models.TextField(validators=[MinLengthValidator(1)])

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Glossary Entry"
        verbose_name_plural = "Glossary Entries"
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(acronym=""),
                name="acronym_not_blank",
            ),
            models.CheckConstraint(
                condition=~models.Q(definition=""),
                name="definition_not_blank",
            ),
        )
        ordering = ("acronym",)

    def __str__(self) -> str:
        return f"{self.acronym} | {Truncator(self.definition).chars(100)}"


class Venue(TimeStampedModel):
    address = models.ForeignKey(
        to=GeocodedAddress,
        on_delete=models.CASCADE,
        related_name="venues",
    )

    name = models.CharField(
        max_length=100,
        unique=True,  # This is for unique lookup of Games by str rep
        validators=[validate_not_empty_string],
    )
    url = models.URLField(
        max_length=200,
        unique=True,
        verbose_name="URL",
    )

    last_scraped_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    if TYPE_CHECKING:
        official_game_count: int
        custom_game_count: int
        event_count: int
        quizmaster_count: int
        team_count: int

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="venue_name_not_blank",
            ),
        )
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class GameType(TimeStampedModel):
    name = models.CharField(
        max_length=200,
        unique=True,
        validators=[validate_not_empty_string],
    )

    if TYPE_CHECKING:
        official_games_count: int

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="game_type_name_not_blank",
            ),
        )
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Game(TimeStampedModel):
    game_type = models.ForeignKey(
        to=GameType,
        on_delete=models.CASCADE,
        related_name="games",
    )
    venue = models.ForeignKey(
        to=Venue,
        on_delete=models.CASCADE,
        related_name="games",
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

    if TYPE_CHECKING:
        event_count: int

    class Meta(TimeStampedModel.Meta):
        constraints = (
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
        )
        ordering = ("venue__name", "game_type__name", "day", "time")

    def __str__(self) -> str:
        return f"{self.venue.name} | {self.game_type.name}" + (
            f", {day_name[self.day]}s at {self.time}" if self.day is not None else ""
        )


class Event(TimeStampedModel):
    game = models.ForeignKey(
        to=Game,
        on_delete=models.CASCADE,
        related_name="events",
    )
    quizmaster = models.ForeignKey(
        to=Quizmaster,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="events",
    )
    theme = models.ForeignKey(
        to=Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    date = models.DateField(db_index=True)
    end_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of when the event ended, generated by the autoscraper",
    )
    description = models.TextField(blank=True, default="")

    join_code = models.CharField(
        max_length=6,
        blank=True,
        validators=[
            RegexValidator(
                regex=JOIN_CODE_REGEX,
                message="Join code must be exactly 6 digits",
            ),
        ],
        default="",
        # db_index=True, Add this if we need to query by join_code
        help_text="User-facing 6-digit code used to join live games",
    )
    slug = models.CharField(
        max_length=24,
        blank=True,
        validators=[
            RegexValidator(
                regex=HEX_24_REGEX,
                message="Slug must be exactly 24 lowercase hex characters",
            ),
        ],
        default="",
        # db_index=True, Add this if we need to query by slug
        help_text="URL slug for the event, theoretically unique",
    )

    if TYPE_CHECKING:
        team_participations_count: int

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["game", "date"],
                name="unique_game_date_event",
            ),
            models.CheckConstraint(
                condition=models.Q(join_code__regex=JOIN_CODE_REGEX)
                | models.Q(join_code=""),
                name="join_code_six_digits_or_blank",
            ),
            models.CheckConstraint(
                condition=models.Q(slug__regex=HEX_24_REGEX) | models.Q(slug=""),
                name="slug_twenty_four_hex",
            ),
        )
        ordering = ("-date",)

    def __str__(self) -> str:
        base = (
            f"{self.game.game_type.name} - {self.game.venue.name} - "
            f"{self.date} - "
            f"{self.quizmaster.name if self.quizmaster else 'No Quizmaster'}"
        )
        return f"{base} - {self.theme.name}" if self.theme else base


class Round(TimeStampedModel):
    round_type = models.ForeignKey(
        to=RoundType,
        on_delete=models.CASCADE,
        related_name="rounds",
    )

    title = models.CharField(max_length=100)
    subtitle = models.CharField(  # Is this ever actually used?
        max_length=150,
        blank=True,
        default="",
    )
    instructions = models.TextField(blank=True, default="")

    external_id = models.PositiveIntegerField(
        unique=True,
        verbose_name="External round ID",
    )

    class Meta(TimeStampedModel.Meta):
        # Add index on event and round_type?
        ordering = ("external_id",)

    def __str__(self) -> str:
        return f"{self.title} - {self.round_type.name} | {self.external_id}"


class EventRound(TimeStampedModel):
    event = models.ForeignKey(
        to=Event,
        on_delete=models.CASCADE,
        related_name="event_rounds",
    )
    round = models.ForeignKey(
        to=Round,
        on_delete=models.CASCADE,
        related_name="event_rounds",
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["event", "round"],
                name="unique_event_round",
            ),
        )

    def __str__(self) -> str:
        return f"{self.event} | {self.round.title}"


class Question(TimeStampedModel):
    round = models.ForeignKey(
        to=Round,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    text = models.TextField(blank=True, default="")
    image = models.URLField(
        max_length=200,
        blank=True,
        default="",
    )
    answer_count = models.PositiveSmallIntegerField(
        verbose_name="Number of answers",
        choices=[(i, str(i)) for i in range(1, 11)],
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="The number of answers required by the question",
    )

    external_id = models.PositiveIntegerField(unique=True)

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=(
                    (~models.Q(text="") & models.Q(image=""))
                    | (models.Q(text="") & ~models.Q(image=""))
                ),
                name="question_text_xor_image",
            ),
            models.CheckConstraint(
                condition=models.Q(answer_count__gte=1, answer_count__lte=10),
                name="question_answer_count_range",
            ),
        )
        ordering = ("-external_id",)

    def __str__(self) -> str:
        return f"{self.round} | {Truncator(self.text or self.image).chars(100)}"


class TeamEventParticipation(TimeStampedModel):
    event = models.ForeignKey(
        to=Event,
        on_delete=models.CASCADE,
        related_name="team_participations",
    )
    team = models.ForeignKey(
        to=Team,
        on_delete=models.CASCADE,
        related_name="event_participations",
    )
    team_name = models.ForeignKey(
        to=TeamName,
        on_delete=models.CASCADE,
        related_name="event_participations",
    )
    table = models.ForeignKey(
        to=Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_participations",
    )

    score = models.SmallIntegerField(
        # Null here allows for a participation to be attached
        # to the placeholder event
        null=True,
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["team", "event"],
                name="unique_team_event_participation",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    score__gte=MIN_TEAM_SCORE,
                    score__lte=MAX_TEAM_SCORE,
                )
                | models.Q(score__isnull=True),
                name="valid_score",
            ),
        )
        ordering = ("-event__date", "-score")

    def __str__(self) -> str:
        base = f"{self.team_name} - {self.event.date} - {self.score} points"
        return f"{base} at {self.table.name}" if self.table else base


class TeamRoundSubmission(TimeStampedModel):
    team_event_participation = models.ForeignKey(
        to=TeamEventParticipation,
        on_delete=models.CASCADE,
        related_name="round_submissions",
    )
    event_round = models.ForeignKey(
        to=EventRound,
        on_delete=models.CASCADE,
        related_name="team_submissions",
    )

    double_or_nothing = models.BooleanField(
        default=False,
        help_text="Whether or not the team chose to double for this round",
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["team_event_participation", "event_round"],
                name="unique_team_event_participation_round_submission",
            ),
        )
        ordering = (
            "-team_event_participation__event__date",
            "-event_round__round__round_type__number",
        )

    def __str__(self) -> str:
        return f"{self.team_event_participation.team} - {self.event_round}"


class Answer(TimeStampedModel):
    team_round_submission = models.ForeignKey(
        to=TeamRoundSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        to=Question,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    text = models.TextField(blank=True, default="")
    correct = models.BooleanField(
        null=True,
        blank=True,
        default=None,
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["team_round_submission", "question"],
                name="unique_team_round_submission_question_answer",
            ),
        )
        ordering = (
            "-team_round_submission__team_event_participation__event__date",
            "question__external_id",
        )

    def __str__(self) -> str:
        status = (
            "Correct"
            if self.correct
            else "Incorrect"
            if self.correct is False
            else "Ungraded"
        )
        return (
            f"{self.team_round_submission.team_event_participation.team} - "
            f"{self.question} [{status}]: {Truncator(self.text).chars(50)}"
        )


class MemberAttendance(TimeStampedModel):
    team_event_participation = models.ForeignKey(
        to=TeamEventParticipation,
        on_delete=models.CASCADE,
        related_name="member_attendances",
    )
    member = models.ForeignKey(
        to=Member,
        on_delete=models.CASCADE,
        related_name="event_attendances",
    )

    notes = models.TextField(blank=True, default="")
    acquired_seating = models.BooleanField(default=False)

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["member", "team_event_participation"],
                name="unique_member_team_event_participation_attendance",
            ),
        )
        ordering = (
            "-team_event_participation__event__date",
            "member__name",
        )

    def __str__(self) -> str:
        return (
            f"{self.member.name} - {self.team_event_participation.team} - "
            f"{self.team_event_participation.event.date}"
        )


class Vote(TimeStampedModel):
    class VoteChoices(models.TextChoices):
        RIGHT = "R", "Right"
        WRONG = "W", "Wrong"
        ABSTAINED = "A", "Abstained"

    round_type = models.ForeignKey(
        to=RoundType,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    member_attendance = models.ForeignKey(
        to=MemberAttendance,
        on_delete=models.CASCADE,
        related_name="votes",
    )

    vote = models.CharField(
        max_length=1,
        choices=VoteChoices,
        default=VoteChoices.ABSTAINED,
    )
    is_double_or_nothing = models.BooleanField(
        verbose_name="Double or nothing vote",
        default=False,
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=["member_attendance", "round_type"],
                name="unique_vote",
            ),
        )

    def __str__(self) -> str:
        return (
            f"{self.member_attendance.team_event_participation.event.date} - "
            f"{self.member_attendance.member.name} - "
            f"{self.get_vote_display()}"  # type: ignore TODO: Check date vs time
        )

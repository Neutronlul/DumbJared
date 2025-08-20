from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Quizmaster(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Team(TimeStampedModel):
    name = models.CharField(max_length=300, unique=True)  # Blame MeatOrgy
    team_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.name


class Member(TimeStampedModel):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")

    def __str__(self):
        return self.name

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["name", "team"], name="unique_team_member")
        ]


# TODO: Maybe add is_booth field?
class Table(TimeStampedModel):
    table_id = models.PositiveIntegerField(
        unique=True
    )  # TODO: Maybe change to CharField for ids like "R1", "L2", etc.
    name = models.CharField(max_length=100, null=True, blank=True, unique=True)
    is_upstairs = models.BooleanField(default=False)

    def __str__(self):
        return self.name if self.name else str(self.table_id)


class Theme(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Round(TimeStampedModel):
    number = models.PositiveIntegerField("Round number", unique=True)
    name = models.CharField("Round name", max_length=100, unique=True)

    def __str__(self):
        return f"Round {self.number}: {self.name}"


class Glossary(TimeStampedModel):
    acronym = models.CharField(max_length=20, unique=True)
    definition = models.TextField()

    def __str__(self):
        return (
            f"{self.acronym} | {self.definition[:97]}..."
            if len(self.definition) > 100
            else f"{self.acronym} | {self.definition}"
        )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Glossary Entry"
        verbose_name_plural = "Glossary Entries"


# Maybe get rid of this and make it a key selection in Event?
class EventType(TimeStampedModel):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


# TODO: Add more fields such as location, url, etc
class Venue(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class Event(TimeStampedModel):
    venue = models.ForeignKey(
        Venue, on_delete=models.CASCADE, related_name="events_at_venue"
    )
    game_type = models.ForeignKey(
        EventType,
        on_delete=models.CASCADE,
        related_name="events_of_type",
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    quizmaster = models.ForeignKey(
        Quizmaster,
        on_delete=models.CASCADE,
        related_name="events_as_quizmaster",
    )
    quizmaster_table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events_as_quizmaster_table",
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events_with_theme",
    )

    def __str__(self):
        base = f"{self.venue.name} - {self.start_datetime.date()} - {self.quizmaster.name}"  # TODO: Add the new fields to the string representation
        return f"{base} - {self.theme.name}" if self.theme else base

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "game_type", "start_datetime"],
                name="unique_venue_type_datetime_event",
            )
        ]


class Vote(TimeStampedModel):
    RIGHT = "R"
    WRONG = "W"
    ABSTAINED = "A"
    VOTING_CHOICES = (
        (RIGHT, "Right"),
        (WRONG, "Wrong"),
        (ABSTAINED, "Abstained"),
    )
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="votes")
    vote = models.CharField(max_length=1, choices=VOTING_CHOICES, default=ABSTAINED)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="votes_in_event"
    )
    round = models.ForeignKey(
        Round, on_delete=models.CASCADE, related_name="votes_in_round"
    )
    is_double_or_nothing = models.BooleanField("Double or nothing vote", default=False)

    def __str__(self):
        return f"{self.event.start_datetime.date()} - {self.member.name} - {self.get_vote_display()}"  # type: ignore TODO: Check date vs time

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["member", "event", "round"], name="unique_vote"
            )
        ]


class TeamEventParticipation(TimeStampedModel):
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="event_participations"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="teams_participating"
    )
    score = models.IntegerField()
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_participations_at_table",
    )

    def __str__(self):
        base = f"{self.team.name} - {self.event.start_datetime.date()} - {self.score} points"  # TODO: Maybe change this to allow for multiple times
        return f"{base} at {self.table.name}" if self.table else base

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["team", "event"], name="unique_team_event_participation"
            )
        ]


# TODO: Change to allow members to belong to multiple teams?
class MemberAttendance(TimeStampedModel):
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="event_attendances"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="member_attendances"
    )
    notes = models.TextField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["member", "event"], name="unique_member_event_attendance"
            )
        ]

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
    name = models.CharField(max_length=100, unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")

    def __str__(self):
        return self.name


class Table(TimeStampedModel):
    table_id = models.PositiveIntegerField(unique=True)
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


class Event(TimeStampedModel):
    date = models.DateField(unique=True)
    quizmaster = models.ForeignKey(
        Quizmaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    quizmaster_table = models.ForeignKey(
        Table, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    theme = models.ForeignKey(
        Theme, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )

    def __str__(self):
        base = f"{self.date} - {self.quizmaster.name if self.quizmaster else "Unknown Quizmaster"}"
        return f"{base} - {self.theme.name}" if self.theme else base

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["date", "quizmaster"], name="unique_event")
        ]


class Vote(TimeStampedModel):
    RIGHT = "R"
    WRONG = "W"
    ABSTAINED = "A"
    VOTING_CHOICES = {
        (RIGHT, "Right"),
        (WRONG, "Wrong"),
        (ABSTAINED, "Abstained"),
    }
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="votes")
    vote = models.CharField(max_length=1, choices=VOTING_CHOICES, default=ABSTAINED)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="votes")
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="votes")
    is_double_or_nothing = models.BooleanField("Double or nothing vote", default=False)

    def __str__(self):
        return f"{self.event.date} - {self.member.name} - {self.get_vote_display()}"  # type: ignore

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
        Event, on_delete=models.CASCADE, related_name="team_participations"
    )
    score = models.IntegerField()
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_event_participations",
    )

    def __str__(self):
        base = f"{self.team.name} - {self.event.date} - {self.score} points"
        return f"{base} at {self.table.name}" if self.table else base

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["team", "event"], name="unique_team_event")
        ]


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
                fields=["member", "event"], name="unique_member_event"
            )
        ]

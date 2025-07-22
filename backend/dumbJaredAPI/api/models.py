from django.db import models


class Quizmaster(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=300, unique=True)  # Blame MeatOrgy
    team_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    name = models.CharField(max_length=100, unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")

    def __str__(self):
        return self.name


class Table(models.Model):
    table_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100, null=True, blank=True, unique=True)

    def __str__(self):
        return self.name if self.name else str(self.table_id)


class Theme(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Event(models.Model):
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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["date", "quizmaster"], name="unique_event")
        ]


class TeamEventParticipation(models.Model):
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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "event"], name="unique_team_event")
        ]


class MemberAttendance(models.Model):
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="event_attendances"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="member_attendances"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["member", "event"], name="unique_member_event"
            )
        ]

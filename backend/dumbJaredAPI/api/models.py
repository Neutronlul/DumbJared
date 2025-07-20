from django.db import models


class Quizmaster(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=300, unique=True)  # Blame MeatOrgy
    team_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    name = models.CharField(max_length=100, unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")

    def __str__(self):
        return self.name


class Event(models.Model):
    date = models.DateField()
    quizmaster = models.ForeignKey(
        Quizmaster, on_delete=models.SET_NULL, related_name="events"
    )

    def __str__(self):
        return f"{self.date} - {self.quizmaster.name}"


class TeamEventParticipation(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    score = models.IntegerField()

    class Meta:
        unique_together = ("team", "event")


class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("member", "event")

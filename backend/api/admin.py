from django.contrib import admin

from . import models

# Register your models here.

for model in [
    models.Quizmaster,
    models.Team,
    models.Member,
    models.Table,
    models.Theme,
    models.Round,
    models.Glossary,
    models.EventType,
    models.Venue,
    models.Event,
    models.Vote,
    models.TeamEventParticipation,
    models.MemberAttendance,
]:
    admin.site.register(model)

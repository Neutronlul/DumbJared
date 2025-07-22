from django.contrib import admin
from . import models

# Register your models here.

for model in [
    models.Quizmaster,
    models.Team,
    models.Member,
    models.Table,
    models.Theme,
    models.Event,
    models.TeamEventParticipation,
    models.MemberAttendance,
]:
    admin.site.register(model)

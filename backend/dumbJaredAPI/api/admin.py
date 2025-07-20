from django.contrib import admin
from .models import (
    Quizmaster,
    Team,
    Member,
    Event,
    TeamEventParticipation,
    MemberAttendance,
)

# Register your models here.

admin.site.register(Quizmaster)
admin.site.register(Team)
admin.site.register(Member)
admin.site.register(Event)
admin.site.register(TeamEventParticipation)
admin.site.register(MemberAttendance)

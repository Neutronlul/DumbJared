from django.shortcuts import render
from rest_framework import viewsets
from api.models import Team, Glossary, Member, MemberAttendance, TeamEventParticipation
from api.serializers import TeamSerializer, GlossarySerializer, MemberSerializer
from django.db.models import (
    Avg,
    Count,
    Max,
    ExpressionWrapper,
    IntegerField,
    Value,
    FloatField,
    Window,
    F,
    Q,
    Subquery,
    OuterRef,
)
from django.db.models.functions import Rank
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from django.views.generic import FormView
from unfold.views import UnfoldModelAdminViewMixin
from django.contrib import messages

from api.forms import BatchAttendanceForm


class BatchAttendanceView(UnfoldModelAdminViewMixin, FormView):
    title = "Batch Attendance"
    permission_required = "api.add_memberattendance"
    form_class = BatchAttendanceForm
    template_name = "admin/create_batch_attendance.html"
    success_url = "/admin/api/memberattendance/"  # TODO: This is lazy, fix it

    def form_valid(self, form):
        event = form.cleaned_data["event"]
        team = form.cleaned_data["team"]
        table = form.cleaned_data["table"]
        members = form.cleaned_data["members"]

        tep = TeamEventParticipation.objects.create(
            team=team,
            team_name=team.names.first(),  # If guest, this is permananent. If Official, this will be overwritten by the scraper.
            event=event,
            score=None,
            table=table,
        )

        # Create MemberAttendance records for each selected member
        for member in members:
            MemberAttendance.objects.create(
                member=member,
                team_event_participation=tep,
            )

        messages.success(
            self.request, f"Successfully created attendance for {len(members)} members."
        )

        return super().form_valid(form)


# Create your views here.
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer


class GlossaryViewSet(viewsets.ModelViewSet):
    queryset = Glossary.objects.all()
    serializer_class = GlossarySerializer

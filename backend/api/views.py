from django.shortcuts import render
from rest_framework import viewsets
from api.models import (
    Team,
    Vote,
    Glossary,
    Member,
    MemberAttendance,
    TeamEventParticipation,
)
from api.serializers import TeamSerializer, GlossarySerializer
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
from django.db import transaction

from api.forms import BatchAttendanceForm, CreateWrongdoingsForm


class BatchAttendanceView(UnfoldModelAdminViewMixin, FormView):
    title = "Batch Attendance"
    permission_required = "api.add_memberattendance"
    form_class = BatchAttendanceForm
    template_name = "admin/create_batch_attendance.html"
    success_url = "/admin/api/memberattendance/"  # TODO: This is lazy, fix it

    @transaction.atomic
    def form_valid(self, form):
        event = form.cleaned_data["event"]
        team = form.cleaned_data["team"]
        table = form.cleaned_data["table"]
        members = form.cleaned_data["members"]

        tep = TeamEventParticipation.objects.create(
            team=team,
            team_name=team.names.first(),  # If guest, this is permanent. If Official, this will be overwritten by the scraper.
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


class CreateWrongdoingsView(UnfoldModelAdminViewMixin, FormView):
    title = "Create Wrongdoings"
    permission_required = "api.add_vote"
    form_class = CreateWrongdoingsForm
    template_name = "admin/create_batch_attendance.html"
    success_url = "/admin/api/vote/"  # TODO: This is lazy, fix it

    @transaction.atomic
    def form_valid(self, form):
        tep = form.cleaned_data["team_event_participation"]
        round = form.cleaned_data["round"]
        don = form.cleaned_data["don"]
        right_members = form.cleaned_data["right"]
        wrong_members = form.cleaned_data["wrong"]
        abstain_members = form.cleaned_data["abstain"]

        for member in right_members:
            Vote.objects.create(
                member_attendance=MemberAttendance.objects.get(
                    member=member,
                    team_event_participation=tep,
                ),
                vote=Vote.VoteChoices.RIGHT,
                round=round,
                is_double_or_nothing=don,
            )

        for member in wrong_members:
            Vote.objects.create(
                member_attendance=MemberAttendance.objects.get(
                    member=member,
                    team_event_participation=tep,
                ),
                vote=Vote.VoteChoices.WRONG,
                round=round,
                is_double_or_nothing=don,
            )

        for member in abstain_members:
            Vote.objects.create(
                member_attendance=MemberAttendance.objects.get(
                    member=member,
                    team_event_participation=tep,
                ),
                vote=Vote.VoteChoices.ABSTAINED,
                round=round,
                is_double_or_nothing=don,
            )

        messages.success(
            self.request,
            f"Successfully created wrongdoing for {len(right_members) + len(wrong_members) + len(abstain_members)} members.",
        )

        return super().form_valid(form)


# Create your views here.
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer


class GlossaryViewSet(viewsets.ModelViewSet):
    queryset = Glossary.objects.all()
    serializer_class = GlossarySerializer

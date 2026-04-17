from typing import TYPE_CHECKING, override

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, QuerySet
from django.urls import reverse_lazy
from django.views.generic import FormView
from rest_framework import viewsets
from unfold.views import BaseAutocompleteView, UnfoldModelAdminViewMixin

from api.forms import BatchAttendanceForm, CreateWrongdoingsForm
from api.models import (
    Glossary,
    MemberAttendance,
    Team,
    TeamEventParticipation,
    Vote,
)
from api.serializers import GlossarySerializer, TeamSerializer

if TYPE_CHECKING:
    from django.forms import BaseForm
    from django.http import HttpResponse


class BatchAttendanceView(UnfoldModelAdminViewMixin, FormView):
    title = "Batch Attendance"
    permission_required = "api.add_memberattendance"
    form_class = BatchAttendanceForm
    template_name = "admin/create_batch_attendance.html"
    success_url = reverse_lazy("admin:api_memberattendance_changelist")

    @override
    @transaction.atomic
    def form_valid(self, form: BaseForm) -> HttpResponse:
        event = form.cleaned_data["event"]
        team = form.cleaned_data["team"]
        table = form.cleaned_data["table"]
        members = form.cleaned_data["members"]

        tep = TeamEventParticipation.objects.create(
            team=team,
            # If guest, this is permanent. If Official,
            # this will be overwritten by the scraper.
            team_name=team.names.first(),
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
            self.request,
            f"Successfully created attendance for {len(members)} members.",
        )

        return super().form_valid(form)


class CreateWrongdoingsView(UnfoldModelAdminViewMixin, FormView):
    title = "Create Wrongdoings"
    permission_required = "api.add_vote"
    form_class = CreateWrongdoingsForm
    template_name = "admin/create_batch_attendance.html"
    success_url = reverse_lazy("admin:api_vote_changelist")

    @override
    @transaction.atomic
    def form_valid(self, form: BaseForm) -> HttpResponse:
        tep = form.cleaned_data["team_event_participation"]
        vote_round = form.cleaned_data["round"]
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
                round=vote_round,
                is_double_or_nothing=don,
            )

        for member in wrong_members:
            Vote.objects.create(
                member_attendance=MemberAttendance.objects.get(
                    member=member,
                    team_event_participation=tep,
                ),
                vote=Vote.VoteChoices.WRONG,
                round=vote_round,
                is_double_or_nothing=don,
            )

        for member in abstain_members:
            Vote.objects.create(
                member_attendance=MemberAttendance.objects.get(
                    member=member,
                    team_event_participation=tep,
                ),
                vote=Vote.VoteChoices.ABSTAINED,
                round=vote_round,
                is_double_or_nothing=don,
            )

        num_total_members = (
            len(right_members) + len(wrong_members) + len(abstain_members)
        )
        messages.success(
            self.request,
            f"Successfully created wrongdoing for {num_total_members} members.",
        )

        return super().form_valid(form)


# Create your views here.
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer


class GlossaryViewSet(viewsets.ModelViewSet):
    queryset = Glossary.objects.all()
    serializer_class = GlossarySerializer


class BatchAttendanceAutocompleteView(BaseAutocompleteView):
    model = Team

    @override
    def get_queryset(self) -> QuerySet[Team]:
        # Search query is available in the request.GET object under the key "term"
        term = self.request.GET.get("term")

        # Additional filters and permissions checks here
        qs = super().get_queryset()

        # No search provided, return all results
        if term == "":
            return qs

        # Search query provided, filter results
        return qs.filter(
            Q(team_id__icontains=term) | Q(names__name__icontains=term),
        ).distinct()

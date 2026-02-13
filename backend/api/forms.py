from api.models import Event, Round, Table, Team, Member, TeamEventParticipation
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from django import forms
from django.db.models import Count
from unfold.layout import Submit
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultiple,
    UnfoldAdminSelectWidget,
    UnfoldBooleanSwitchWidget,
)
from django.forms import ValidationError


class BatchAttendanceForm(forms.Form):
    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        widget=UnfoldAdminSelectWidget,
    )
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        widget=UnfoldAdminSelectWidget,
    )
    table = forms.ModelChoiceField(
        queryset=Table.objects.all(),
        widget=UnfoldAdminSelectWidget,
        required=False,
    )
    members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        widget=UnfoldAdminCheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if latest_event := Event.objects.order_by("-date").first():
            self.fields["event"].initial = latest_event

        if team_with_most_member_attendances := (
            Team.objects.annotate(
                attendance_count=Count("event_participations__member_attendances")
            )
            .order_by("-attendance_count")
            .first()
        ):
            self.fields["team"].initial = team_with_most_member_attendances

        # TODO: default the table to the existing record in case of updating an existing attendance record

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Select Event, Team, and Table",
                "event",
                "team",
                "table",
            ),
            Fieldset(
                "Select Members",
                "members",
            ),
        )
        self.helper.add_input(Submit("submit", "Create Attendances"))


class CreateWrongdoingsForm(forms.Form):
    team_event_participation = forms.ModelChoiceField(
        queryset=TeamEventParticipation.objects.filter(
            member_attendances__isnull=False
        ).distinct(),
        widget=UnfoldAdminSelectWidget,
    )
    round = forms.ModelChoiceField(
        queryset=Round.objects.all(),
        widget=UnfoldAdminSelectWidget,
    )
    don = forms.BooleanField(
        widget=UnfoldBooleanSwitchWidget,
        label="Double or nothing?",
        required=False,
    )
    right = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        widget=UnfoldAdminCheckboxSelectMultiple,
    )
    wrong = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        widget=UnfoldAdminCheckboxSelectMultiple,
    )
    abstain = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        widget=UnfoldAdminCheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            latest_tep := TeamEventParticipation.objects.filter(
                member_attendances__isnull=False
            )
            .order_by("-event__date")
            .first()
        ):
            self.fields["team_event_participation"].initial = latest_tep

        self.fields["round"].initial = Round.objects.order_by("number").first()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Meta",
                "team_event_participation",
                "round",
                "don",
            ),
            Fieldset(
                "Votes",
                "right",
                "wrong",
                "abstain",
            ),
        )
        self.helper.add_input(Submit("submit", "Create Wrongdoings"))

    def clean(self):
        cleaned_data = super().clean()
        right = set(cleaned_data.get("right", []))
        wrong = set(cleaned_data.get("wrong", []))
        abstain = set(cleaned_data.get("abstain", []))

        # Find duplicates
        duplicates = (right & wrong) | (right & abstain) | (wrong & abstain)

        if duplicates:
            members = ", ".join(str(m) for m in duplicates)
            raise ValidationError(
                f"Members cannot appear in multiple vote categories: {members}"
            )

        # TODO: Add validation for members acctually attending

        return cleaned_data

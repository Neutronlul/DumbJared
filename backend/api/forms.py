from api.models import Event, Table, Team, Member
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from django import forms
from django.db.models import Count
from unfold.layout import Submit
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultiple,
    UnfoldAdminSelectWidget,
)


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

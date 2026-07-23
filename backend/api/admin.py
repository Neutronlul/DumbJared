from datetime import date, timedelta
from typing import TYPE_CHECKING, override
from urllib.parse import urlparse

from django.apps import apps
from django.contrib import admin
from django.db.models import Count, OuterRef, QuerySet, Subquery
from django.db.models import Model as DjangoModel
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import URLPattern, path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import action, display

from api import models
from api.forms import BatchAttendanceForm
from api.views import (
    BatchAttendanceAutocompleteView,
    BatchAttendanceView,
    CreateWrongdoingsView,
)
from scraper.services.scraper_service import ScraperService
from scraper.tasks import populate_slug
from scraper.utils.timezone import geocode_address

if TYPE_CHECKING:
    from django.forms import BaseModelFormSet, Form, ModelForm


def _format_admin_link(
    obj: DjangoModel | None,
    display_attr: str = "name",
) -> str | None:
    if obj is None:
        return None

    return format_html(
        '<a href="{}">{}</a>',
        reverse(f"admin:api_{obj._meta.model_name}_change", args=[obj.pk]),  # noqa: SLF001
        getattr(obj, display_attr),
    )


@admin.register(models.Event)
class EventAdmin(ModelAdmin):
    class IsThemedFilter(admin.SimpleListFilter):
        title = "Themed"
        parameter_name = "themed"

        @override
        def lookups(
            self,
            request: HttpRequest,
            model_admin: ModelAdmin,
        ) -> list[tuple[str, str]]:
            return [
                ("yes", "Yes"),
                ("no", "No"),
            ]

        @override
        def queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[models.Event],
        ) -> QuerySet[models.Event]:
            if self.value() == "yes":
                return queryset.filter(theme__isnull=False)
            if self.value() == "no":
                return queryset.filter(theme__isnull=True)
            return queryset

    list_display = (
        "venue",
        "game_name",
        "date",
        "team_count",
        "quizmaster_link",
        "theme_link",
        "join_code",
    )
    list_display_links = ("venue", "game_name", "date")

    list_filter = (
        ("game__venue", RelatedDropdownFilter),
        ("game__game_type", RelatedDropdownFilter),
        ("quizmaster", RelatedDropdownFilter),
        IsThemedFilter,
    )
    list_filter_submit = True

    readonly_fields = ("end_datetime", "slug")

    search_fields = (
        "game__venue__name",
        "game__game_type__name",
        "quizmaster__name",
        "theme__name",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Event]:
        qs = super().get_queryset(request)
        return qs.select_related(
            "game__venue",
            "game__game_type",
            "quizmaster",
            "theme",
        ).with_team_participations_count()

    # In the future, if codes are added via the frontend or
    # something, this should be moved to the model-level
    @override
    def save_model(
        self,
        request: HttpRequest,
        obj: DjangoModel,
        form: Form,
        change: bool,
    ) -> None:
        super().save_model(request, obj, form, change)

        # Type narrow first
        if not isinstance(obj, models.Event):
            return

        # If the event has already ended, the join code probably won't work
        if obj.end_datetime or obj.date < timezone.localdate():
            return

        if (obj.join_code and not obj.slug and not change) or (
            "join_code" in form.changed_data and obj.join_code
        ):
            populate_slug.delay(obj.pk, obj.join_code)
            self.message_user(
                request,
                f"Fetching game slug for join code {obj.join_code}...",
                level="info",
            )

    @display(description="Venue", ordering="game__venue__name")
    def venue(self, obj: models.Event) -> str:
        return obj.game.venue.name

    @display(description="Game", ordering="game__game_type__name")
    def game_name(self, obj: models.Event) -> str:
        return obj.game.game_type.name

    @display(description="Teams", ordering="team_participations_count")
    def team_count(self, obj: models.Event) -> int:
        return obj.team_participations_count

    @display(description="Quizmaster", ordering="quizmaster__name")
    def quizmaster_link(self, obj: models.Event) -> str | None:
        return _format_admin_link(obj.quizmaster)

    @display(description="Theme", ordering="theme__name")
    def theme_link(self, obj: models.Event) -> str | None:
        return _format_admin_link(obj.theme)


@admin.register(models.Game)
class GameAdmin(ModelAdmin):
    list_display = ("game_type", "venue", "day", "time", "event_count")
    list_display_links = ("game_type",)

    list_filter = (
        ("game_type", RelatedDropdownFilter),
        ("venue", RelatedDropdownFilter),
        "day",
    )
    list_filter_submit = True

    search_fields = ("venue__name", "game_type__name")

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Game]:
        qs = super().get_queryset(request)
        return qs.with_event_count()

    @display(description="Number of events", ordering="event_count")
    def event_count(self, obj: models.Game) -> int:
        return obj.event_count


@admin.register(models.GameType)
class GameTypeAdmin(ModelAdmin):
    class IsOfficialFilter(admin.SimpleListFilter):
        title = "Official"
        parameter_name = "is_official"

        @override
        def lookups(
            self,
            request: HttpRequest,
            model_admin: ModelAdmin,
        ) -> list[tuple[str, str]]:
            return [
                ("yes", "Yes"),
                ("no", "No"),
            ]

        @override
        def queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[models.GameType],
        ) -> QuerySet[models.GameType]:
            if self.value() == "yes":
                return queryset.filter(games__day__isnull=False).distinct()
            if self.value() == "no":
                return queryset.exclude(games__day__isnull=False).distinct()
            return queryset

    list_display = ("name", "is_official")

    list_filter = (IsOfficialFilter,)

    search_fields = ("name",)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        return qs.with_official_games_count()

    @display(description="Official", ordering="official_games_count", boolean=True)
    def is_official(self, obj: models.GameType) -> bool:
        return obj.official_games_count > 0


@admin.register(models.Glossary)
class GlossaryAdmin(ModelAdmin):
    list_display = ("acronym", "definition")
    list_display_links = list_display

    search_fields = ("acronym", "definition")


@admin.register(models.Member)
class MemberAdmin(ModelAdmin):
    class MemberTeamFilter(admin.SimpleListFilter):
        title = "Team"
        parameter_name = "team"

        @override
        def lookups(
            self,
            request: HttpRequest,
            model_admin: ModelAdmin,
        ) -> list[tuple[int, str]]:
            teams = models.Team.objects.filter(
                event_participations__member_attendances__isnull=False,
            ).distinct()
            return [(team.pk, str(team)) for team in teams]

        @override
        def queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[models.Member],
        ) -> QuerySet[models.Member]:
            if self.value():
                return queryset.filter(
                    event_attendances__team_event_participation__team_id=self.value(),
                )
            return queryset

    list_display = (
        "name",
        "events_attended",
        "first_attended",
        "last_attended",
    )

    list_filter = (MemberTeamFilter,)
    list_filter_submit = True

    search_fields = ("name",)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Member]:
        qs = super().get_queryset(request)
        return (
            qs.with_attendance_count()
            .with_first_attended_date()
            .with_last_attended_date()
        )

    @display(description="Events attended", ordering="attendance_count")
    def events_attended(self, obj: models.Member) -> int:
        return obj.attendance_count

    @display(description="First attended", ordering="first_attended_date")
    def first_attended(self, obj: models.Member) -> date | None:
        return obj.first_attended_date

    @display(description="Last attended", ordering="last_attended_date")
    def last_attended(self, obj: models.Member) -> date | None:
        return obj.last_attended_date


@admin.register(models.MemberAttendance)
class MemberAttendanceAdmin(ModelAdmin):
    @override
    def get_urls(self) -> list[URLPattern]:
        urls = super().get_urls()

        custom_view = self.admin_site.admin_view(
            BatchAttendanceView.as_view(model_admin=self),
        )
        custom_urls = [
            path(
                "create-batch-attendance",
                custom_view,
                name="api_memberattendance_create_batch_attendance",
            ),
        ]
        return urls + custom_urls

    def create_batch_attendance_view(self, request: HttpRequest) -> HttpResponse:
        form = BatchAttendanceForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            pass
        return render(
            request,
            "admin/api/memberattendance/create_batch_attendance.html",
            {"form": form},
        )

    class MemberAttendanceTeamFilter(admin.SimpleListFilter):
        title = "Team"
        parameter_name = "team"

        @override
        def lookups(
            self,
            request: HttpRequest,
            model_admin: ModelAdmin,
        ) -> list[tuple[int, str]]:
            teams = models.Team.objects.filter(
                event_participations__member_attendances__isnull=False,
            ).distinct()
            return [(team.pk, str(team)) for team in teams]

        @override
        def queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[models.MemberAttendance],
        ) -> QuerySet[models.MemberAttendance]:
            if self.value():
                return queryset.filter(team_event_participation__team_id=self.value())
            return queryset

    actions_list = ("create_batch_attendance",)

    list_display = (
        "member_name",
        "team_name",
        "date",
        "acquired_seating",
    )
    list_display_links = ("member_name",)

    list_filter = (
        ("member", RelatedDropdownFilter),
        MemberAttendanceTeamFilter,
        ("team_event_participation__event__game__venue", RelatedDropdownFilter),
        ("acquired_seating", BooleanRadioFilter),
    )
    list_filter_submit = True

    list_select_related = (
        "member",
        "team_event_participation__team_name",
        "team_event_participation__event",
    )

    search_fields = (
        "member__name",
        "team_event_participation__team_name__name",
    )

    @display(description="Member", ordering="member__name")
    def member_name(self, obj: models.MemberAttendance) -> str:
        return obj.member.name

    @display(description="Team", ordering="team_event_participation__team_name__name")
    def team_name(self, obj: models.MemberAttendance) -> str:
        return obj.team_event_participation.team_name.name

    @display(description="Date", ordering="team_event_participation__event__date")
    def date(self, obj: models.MemberAttendance) -> date:
        return obj.team_event_participation.event.date

    @action(
        description="Create batch attendance",
        url_path="create-batch-attendance",
    )  # ty:ignore[call-non-callable]
    def create_batch_attendance(self, _request: HttpRequest) -> HttpResponseRedirect:
        return HttpResponseRedirect(
            reverse("admin:api_memberattendance_create_batch_attendance"),
        )


@admin.register(models.Quizmaster)
class QuizmasterAdmin(ModelAdmin):
    list_display = ("name", "event_count")
    list_display_links = ("name",)

    list_filter = (("events__game__venue", RelatedDropdownFilter),)
    list_filter_submit = True

    search_fields = ("name",)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Quizmaster]:
        qs = super().get_queryset(request)
        return qs.with_events_officiated_count()

    @display(description="Events officiated", ordering="events_officiated_count")
    def event_count(self, obj: models.Quizmaster) -> int:
        return obj.events_officiated_count


@admin.register(models.RoundType)
class RoundTypeAdmin(ModelAdmin):
    list_display = ("name", "number", "double_or_nothing", "vote_count")
    list_display_links = ("name", "number")

    search_fields = ("name", "number")

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.RoundType]:
        qs = super().get_queryset(request)
        return qs.annotate(
            votes_held_count=Count(
                "votes__member_attendance__team_event_participation__event",
                distinct=True,
            ),
        )

    @display(description="Number of votes held", ordering="votes_held_count")
    def vote_count(self, obj: models.RoundType) -> int:
        return obj.votes_held_count


@admin.register(models.Table)
class TableAdmin(ModelAdmin):
    list_display = ("table_id", "name", "is_upstairs", "times_sat_at")
    list_display_links = ("table_id", "name")

    list_filter = (
        ("team_participations__event__game__venue", RelatedDropdownFilter),
        ("is_upstairs", BooleanRadioFilter),
    )
    list_filter_submit = True

    search_fields = ("table_id", "name")

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Table]:
        qs = super().get_queryset(request)
        return qs.annotate(seatings_count=Count("team_participations", distinct=True))

    @display(description="Times sat at", ordering="seatings_count")
    def times_sat_at(self, obj: models.Table) -> int:
        return obj.seatings_count


@admin.register(models.TeamEventParticipation)
class TeamEventParticipationAdmin(ModelAdmin):
    class MemberAttendanceInline(TabularInline):
        model = apps.get_model("api", "MemberAttendance")
        extra = 0
        fields = ("member", "acquired_seating")
        readonly_fields = ()
        autocomplete_fields = ("member",)

    inlines = (MemberAttendanceInline,)

    list_display = ("team", "event", "score", "table")
    list_display_links = list_display

    list_select_related = ("team_name", "team", "event", "table")

    list_filter = (
        ("team", AutocompleteSelectFilter),
        ("event__game__venue", RelatedDropdownFilter),
    )
    list_filter_submit = True

    search_fields = ("team_name__name", "team__team_id")


@admin.register(models.Team)
class TeamAdmin(ModelAdmin):
    class IsGuestFilter(admin.SimpleListFilter):
        title = "Guest"
        parameter_name = "is_guest"

        @override
        def lookups(
            self,
            request: HttpRequest,
            model_admin: ModelAdmin,
        ) -> list[tuple[str, str]]:
            return [
                ("yes", "Yes"),
                ("no", "No"),
            ]

        @override
        def queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[models.Team],
        ) -> QuerySet[models.Team]:
            if self.value() == "yes":
                return queryset.filter(team_id__isnull=True)
            if self.value() == "no":
                return queryset.filter(team_id__isnull=False)
            return queryset

    class TeamNameInline(TabularInline):
        model = models.TeamName
        extra = 0

    inlines = (TeamNameInline,)

    list_display = (
        "latest_name",
        "team_id_link",
        "attendance_count",
        "last_seen",
    )

    list_filter = (
        ("event_participations__event__game__venue", RelatedDropdownFilter),
        IsGuestFilter,
    )
    list_filter_submit = True

    search_fields = ("team_id",)

    custom_urls = (
        (
            "batch-attendance-autocomplete",
            "batch_attendance_autocomplete",
            BatchAttendanceAutocompleteView.as_view(),
        ),
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Team]:
        qs = super().get_queryset(request)
        return (
            qs.annotate(
                latest_name=Coalesce(
                    Subquery(
                        models.TeamEventParticipation.objects.filter(
                            team_id=OuterRef("pk"),
                        )
                        .order_by("-event__date")
                        .values("team_name__name")[:1],
                    ),
                    Subquery(
                        models.TeamName.objects.filter(team_id=OuterRef("pk"))
                        .order_by("-created_at")
                        .values("name")[:1],
                    ),
                ),
                venue_url=Subquery(
                    models.TeamEventParticipation.objects.filter(team_id=OuterRef("pk"))
                    .order_by("-event__date")
                    .values("event__game__venue__url")[:1],
                ),
            )
            .with_event_participations_count()
            .with_last_seen_date()
            .order_by("latest_name")
        )

    @override
    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QuerySet[models.Team],
        search_term: str,
    ) -> tuple[QuerySet[models.Team], bool]:
        if not search_term:
            return queryset, False

        # Get PKs that match by team_id
        team_id_pks = queryset.filter(team_id__icontains=search_term).values_list(
            "pk",
            flat=True,
        )

        # Get PKs that match by name
        name_pks = (
            models.TeamName.objects.filter(name__icontains=search_term)
            .values_list("team__pk", flat=True)
            .distinct()
        )

        # Combine PKs and filter the base queryset (preserves annotations/ordering)
        all_pks = set(team_id_pks) | set(name_pks)
        return queryset.filter(pk__in=all_pks), False

    @override
    def save_formset(
        self,
        request: HttpRequest,
        form: ModelForm,
        formset: BaseModelFormSet,
        change: bool,
    ) -> None:
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            obj.delete()

        for instance in instances:
            instance.guest = instance.team.team_id is None
            instance.save()

        formset.save_m2m()

    @display(description="Name", ordering="latest_name")
    def latest_name(self, obj: models.Team) -> str:
        return obj.latest_name

    @display(description="Team ID", ordering="team_id")
    def team_id_link(self, obj: models.Team) -> str | None:
        if obj.team_id is None:
            return None

        venue_url = obj.venue_url
        if venue_url is None:
            return str(obj.team_id)

        url_netloc = urlparse(venue_url).netloc
        return format_html(
            '<a href="https://{}/teams/{}" target="_blank">{}</a>',
            url_netloc,
            obj.team_id,
            obj.team_id,
        )

    @display(description="Attendances", ordering="event_participations_count")
    def attendance_count(self, obj: models.Team) -> int:
        return obj.event_participations_count

    @display(description="Last seen", ordering="last_seen_date")
    def last_seen(self, obj: models.Team) -> date | None:
        return obj.last_seen_date


@admin.register(models.TeamName)
class TeamNameAdmin(ModelAdmin):
    list_display = ("name", "team", "guest")

    list_select_related = ("team",)

    list_filter = (
        ("team", AutocompleteSelectFilter),
        ("guest", BooleanRadioFilter),
    )
    list_filter_submit = True

    search_fields = ("name", "team__team_id")


@admin.register(models.Theme)
class ThemeAdmin(ModelAdmin):
    list_display = (
        "name",
        "last_used",
        "event_count",
    )

    list_filter = (("events__game__venue", RelatedDropdownFilter),)
    list_filter_submit = True

    search_fields = ("name",)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Theme]:
        qs = super().get_queryset(request)
        return qs.with_event_count().with_last_used_date()

    @display(description="Last used", ordering="last_used_date")
    def last_used(self, obj: models.Theme) -> date | None:
        return obj.last_used_date

    @display(description="Number of events with theme", ordering="event_count")
    def event_count(self, obj: models.Theme) -> int:
        return obj.event_count


@admin.register(models.Venue)
class VenueAdmin(ModelAdmin):
    actions = ("scrape", "scrape_full")

    list_display = (
        "name",
        "url_link",
        "last_scraped_at_styled",
        "game_count_official",
        "game_count_custom",
        "event_count",
        "quizmaster_count",
        "team_count",
    )
    list_display_links = ("name",)

    list_filter = (
        ("games__game_type", RelatedDropdownFilter),
        ("games__events__quizmaster", RelatedDropdownFilter),
        ("games__events__team_participations__team", AutocompleteSelectFilter),
    )
    list_filter_submit = True

    readonly_fields = ("name", "address")

    search_fields = ("name", "url")

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Venue]:
        qs = super().get_queryset(request)
        return (
            qs.with_official_game_count()
            .with_custom_game_count()
            .with_event_count()
            .with_quizmaster_count()
            .with_team_count()
        )

    @override
    def save_model(
        self,
        request: HttpRequest,
        obj: DjangoModel,
        form: Form,
        change: bool,
    ) -> None:
        self._save_failed = False
        if not change and isinstance(obj, models.Venue):
            try:
                venue_data = ScraperService().scrape_venue(source_url=obj.url)
            except Exception as e:  # noqa: BLE001
                msg = f"Failed to fetch venue data: {e}"
                self.message_user(
                    request,
                    message=msg,
                    level="error",
                )
                self._save_failed = True
                return

            obj.name = venue_data.name
            obj.address = geocode_address(venue_data.address)

        super().save_model(request, obj, form, change)

    @override
    def response_add(
        self,
        request: HttpRequest,
        obj: DjangoModel,
        post_url_continue: str | None = None,
    ) -> HttpResponse:
        if self._save_failed:
            self._save_failed = False
            return HttpResponseRedirect(request.path)
        return super().response_add(request, obj, post_url_continue)

    @display(description="URL")
    def url_link(self, obj: models.Venue) -> str:
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)

    @display(
        description="Last scraped at",
        ordering="last_scraped_at",
        label={
            "within_hour": "success",
            "within_day": "info",
            "within_week": "warning",
            "old": "danger",
        },
    )
    def last_scraped_at_styled(self, obj: models.Venue) -> tuple[str, date | None]:
        last_scraped_at = obj.last_scraped_at

        if last_scraped_at is None:
            return "", None

        age = timezone.now() - last_scraped_at

        if age <= timedelta(hours=1):
            return "within_hour", last_scraped_at

        if age <= timedelta(days=1):
            return "within_day", last_scraped_at

        if age <= timedelta(weeks=1):
            return "within_week", last_scraped_at

        return "old", last_scraped_at

    @display(description="Official games", ordering="official_game_count")
    def game_count_official(self, obj: models.Venue) -> int:
        return obj.official_game_count

    @display(description="Custom games", ordering="custom_game_count")
    def game_count_custom(self, obj: models.Venue) -> int:
        return obj.custom_game_count

    @display(description="Events held", ordering="event_count")
    def event_count(self, obj: models.Venue) -> int:
        return obj.event_count

    @display(description="Quizmasters", ordering="quizmaster_count")
    def quizmaster_count(self, obj: models.Venue) -> int:
        return obj.quizmaster_count

    @display(description="Teams", ordering="team_count")
    def team_count(self, obj: models.Venue) -> int:
        return obj.team_count

    def _scrape_venue(
        self,
        request: HttpRequest,
        venue: models.Venue,
        end_date: str | None,
    ) -> None:
        try:
            service = ScraperService()

            data = service.scrape_data(
                source_url=str(venue.url),
                end_date=end_date,
            )

            service.push_to_db(data=data)

            msg = (
                "Successfully "
                f"{'scraped data' if end_date is None else 'performed full scrape'} "
                f"for {venue.name}"
            )
            self.message_user(
                request,
                message=msg,
                level="success",
            )
        except Exception as e:  # noqa: BLE001
            msg = (
                "Error "
                f"{'scraping' if end_date is None else 'performing full scrape for'} "
                f"{venue.name}: {e!s}"
            )
            self.message_user(
                request,
                message=msg,
                level="error",
            )

    @action(description="Scrape new data for selected venues")  # ty:ignore[call-non-callable]
    def scrape(self, request: HttpRequest, queryset: QuerySet[models.Venue]) -> None:
        for venue in queryset:
            self._scrape_venue(request=request, venue=venue, end_date=None)

    @action(description="Force full re-scrape for selected venues")  # ty:ignore[call-non-callable]
    def scrape_full(
        self,
        request: HttpRequest,
        queryset: QuerySet[models.Venue],
    ) -> None:
        for venue in queryset:
            self._scrape_venue(request=request, venue=venue, end_date="1970-01-01")


@admin.register(models.Vote)
class VoteAdmin(ModelAdmin):
    @override
    def get_urls(self) -> list[URLPattern]:
        urls = super().get_urls()

        custom_view = self.admin_site.admin_view(
            CreateWrongdoingsView.as_view(model_admin=self),
        )
        custom_urls = [
            path(
                "create-wrongdoings",
                custom_view,
                name="api_vote_create_wrongdoings",
            ),
        ]
        return urls + custom_urls

    actions_list = ("create_wrongdoings",)

    list_display = (
        "member_name",
        "vote_colored",
        "double_or_nothing",
        "round_type",
        "date",
    )
    list_display_links = (
        "member_name",
        "vote_colored",
        "double_or_nothing",
    )

    list_filter = (
        ("member_attendance__member", RelatedDropdownFilter),
        "vote",
        "is_double_or_nothing",
        "round_type",
    )
    list_filter_submit = True

    list_select_related = (
        "member_attendance__team_event_participation__event",
        "member_attendance__member",
        "round_type",
    )

    search_fields = ("member_attendance__member__name",)

    @display(description="Member", ordering="member_attendance__member__name")
    def member_name(self, obj: models.Vote) -> str:
        return obj.member_attendance.member.name

    @display(
        description="Vote",
        ordering="vote",
        label={
            models.Vote.VoteChoices.RIGHT: "success",
            models.Vote.VoteChoices.WRONG: "danger",
            models.Vote.VoteChoices.ABSTAINED: "info",
        },
    )
    def vote_colored(self, obj: models.Vote) -> tuple[str, str]:
        vote_enum = models.Vote.VoteChoices(obj.vote)
        return str(vote_enum.value), vote_enum.label

    @display(
        description="Double or nothing?",
        ordering="is_double_or_nothing",
        boolean=True,
    )
    def double_or_nothing(self, obj: models.Vote) -> bool:
        return obj.is_double_or_nothing

    @display(
        description="Date",
        ordering="member_attendance__team_event_participation__event__date",
    )
    def date(self, obj: models.Vote) -> date:
        return obj.member_attendance.team_event_participation.event.date

    @action(description="Create wrongdoings", url_path="create-wrongdoings")  # ty:ignore[call-non-callable]
    def create_wrongdoings(self, _request: HttpRequest) -> HttpResponseRedirect:
        return HttpResponseRedirect(reverse("admin:api_vote_create_wrongdoings"))


@admin.register(models.Round)
class RoundAdmin(ModelAdmin):
    pass


@admin.register(models.Question)
class QuestionAdmin(ModelAdmin):
    pass


@admin.register(models.TeamRoundSubmission)
class TeamRoundSubmissionAdmin(ModelAdmin):
    pass


@admin.register(models.Answer)
class AnswerAdmin(ModelAdmin):
    pass

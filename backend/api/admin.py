from api import models
from datetime import date, timedelta
from django.apps import apps
from django.contrib import admin
from django.db.models import Count, Q, QuerySet, OuterRef, Subquery, Max, Min
from django.db.models.functions import Coalesce
from django.forms import BaseModelFormSet, ModelForm
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from scraper.services.scraper_service import ScraperService
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    RelatedDropdownFilter,
    BooleanRadioFilter,
    AutocompleteSelectFilter,
)
from unfold.decorators import action, display
from urllib.parse import urlparse


@admin.register(models.Event)
class EventAdmin(ModelAdmin):
    class IsThemedFilter(admin.SimpleListFilter):
        title = "Themed"
        parameter_name = "themed"

        def lookups(
            self, request: HttpRequest, model_admin: ModelAdmin
        ) -> list[tuple[str, str]]:
            return [
                ("yes", "Yes"),
                ("no", "No"),
            ]

        def queryset(
            self, request: HttpRequest, queryset: QuerySet[models.Event]
        ) -> QuerySet[models.Event]:
            if self.value() == "yes":
                return queryset.filter(theme__isnull=False)
            if self.value() == "no":
                return queryset.filter(theme__isnull=True)
            return queryset

    list_display = ["venue", "game_name", "date", "team_count", "quizmaster", "theme"]
    list_display_links = list_display

    list_filter = [
        ("game__venue", RelatedDropdownFilter),
        ("game__game_type", RelatedDropdownFilter),
        ("quizmaster", RelatedDropdownFilter),
        IsThemedFilter,
    ]
    list_filter_submit = True

    search_fields = [
        "game__venue__name",
        "game__game_type__name",
        "quizmaster__name",
        "theme__name",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Event]:
        qs = super().get_queryset(request)
        return qs.select_related(
            "game__venue",
            "game__game_type",
            "quizmaster",
            "theme",
        ).annotate(team_participations_count=Count("team_participations"))

    @display(description="Venue", ordering="game__venue__name")
    def venue(self, obj: models.Event) -> str:
        return obj.game.venue.name

    @display(description="Game", ordering="game__game_type__name")
    def game_name(self, obj: models.Event) -> str:
        return obj.game.game_type.name

    @display(description="Teams", ordering="team_participations_count")
    def team_count(self, obj: models.Event) -> int:
        return getattr(obj, "team_participations_count")


@admin.register(models.Game)
class GameAdmin(ModelAdmin):
    list_display = ["game_type", "venue", "day", "time", "event_count"]
    list_display_links = ["game_type"]

    list_filter = [
        ("game_type", RelatedDropdownFilter),
        ("venue", RelatedDropdownFilter),
        "day",
    ]
    list_filter_submit = True

    search_fields = ["venue__name", "game_type__name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Game]:
        qs = super().get_queryset(request)
        return qs.annotate(event_count=Count("events"))

    @display(description="Number of events", ordering="event_count")
    def event_count(self, obj: models.Game) -> int:
        return getattr(obj, "event_count")


@admin.register(models.GameType)
class GameTypeAdmin(ModelAdmin):
    class IsOfficialFilter(admin.SimpleListFilter):
        title = "Official"
        parameter_name = "is_official"

        def lookups(
            self, request: HttpRequest, model_admin: ModelAdmin
        ) -> list[tuple[str, str]]:
            return [
                ("yes", "Yes"),
                ("no", "No"),
            ]

        def queryset(
            self, request: HttpRequest, queryset: QuerySet[models.GameType]
        ) -> QuerySet[models.GameType]:
            if self.value() == "yes":
                return queryset.filter(games__day__isnull=False).distinct()
            if self.value() == "no":
                return queryset.exclude(games__day__isnull=False).distinct()
            return queryset

    list_display = ["name", "is_official"]

    list_filter = [IsOfficialFilter]

    search_fields = ["name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        return qs.annotate(
            official_games_count=Count("games", filter=Q(games__day__isnull=False))
        )

    @display(description="Official", ordering="official_games_count", boolean=True)
    def is_official(self, obj: models.GameType) -> bool:
        return getattr(obj, "official_games_count") > 0


@admin.register(models.Glossary)
class GlossaryAdmin(ModelAdmin):
    # TODO: Truncate the definition display in list view
    list_display = ["acronym", "definition"]
    list_display_links = list_display

    search_fields = ["acronym", "definition"]


@admin.register(models.Member)
class MemberAdmin(ModelAdmin):
    class MemberTeamFilter(admin.SimpleListFilter):
        title = "Team"
        parameter_name = "team"

        def lookups(
            self, request: HttpRequest, model_admin: ModelAdmin
        ) -> list[tuple[int, str]]:
            teams = models.Team.objects.filter(
                event_participations__member_attendances__isnull=False
            ).distinct()
            return [(team.pk, str(team)) for team in teams]

        def queryset(
            self, request: HttpRequest, queryset: QuerySet[models.Member]
        ) -> QuerySet[models.Member]:
            if self.value():
                return queryset.filter(
                    event_attendances__team_event_participation__team_id=self.value()
                )
            return queryset

    list_display = ["name", "events_attended", "first_attended", "last_attended"]

    list_filter = [
        MemberTeamFilter,
    ]
    list_filter_submit = True

    search_fields = ["name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Member]:
        qs = super().get_queryset(request)
        return qs.annotate(
            events_attended_count=Count("event_attendances", distinct=True),
            first_attended_date=Min(
                "event_attendances__team_event_participation__event__date"
            ),
            last_attended_date=Max(
                "event_attendances__team_event_participation__event__date"
            ),
        )

    @display(description="Events Attended", ordering="events_attended_count")
    def events_attended(self, obj: models.Member) -> int:
        return getattr(obj, "events_attended_count")

    @display(description="First Attended", ordering="first_attended_date")
    def first_attended(self, obj: models.Member) -> date | None:
        return getattr(obj, "first_attended_date")

    @display(description="Last Attended", ordering="last_attended_date")
    def last_attended(self, obj: models.Member) -> date | None:
        return getattr(obj, "last_attended_date")


@admin.register(models.MemberAttendance)
class MemberAttendanceAdmin(ModelAdmin):
    class MemberAttendanceTeamFilter(admin.SimpleListFilter):
        title = "Team"
        parameter_name = "team"

        def lookups(
            self, request: HttpRequest, model_admin: ModelAdmin
        ) -> list[tuple[int, str]]:
            teams = models.Team.objects.filter(
                event_participations__member_attendances__isnull=False
            ).distinct()
            return [(team.pk, str(team)) for team in teams]

        def queryset(
            self, request: HttpRequest, queryset: QuerySet[models.MemberAttendance]
        ) -> QuerySet[models.MemberAttendance]:
            if self.value():
                return queryset.filter(team_event_participation__team_id=self.value())
            return queryset

    list_display = [
        "member_name",
        "team_name",
        "date",
        "acquired_seating",
    ]
    list_display_links = ["member_name"]

    list_filter = [
        ("member", RelatedDropdownFilter),
        MemberAttendanceTeamFilter,
        ("team_event_participation__event__game__venue", RelatedDropdownFilter),
        ("acquired_seating", BooleanRadioFilter),
    ]
    list_filter_submit = True

    list_select_related = [
        "member",
        "team_event_participation__team_name",
        "team_event_participation__event",
    ]

    search_fields = [
        "member__name",
        "team_event_participation__team_name__name",
    ]

    @display(description="Member", ordering="member__name")
    def member_name(self, obj: models.MemberAttendance) -> str:
        return obj.member.name

    @display(description="Team", ordering="team_event_participation__team_name__name")
    def team_name(self, obj: models.MemberAttendance) -> str:
        return obj.team_event_participation.team_name.name

    @display(description="Date", ordering="team_event_participation__event__date")
    def date(self, obj: models.MemberAttendance) -> date:
        return obj.team_event_participation.event.date


@admin.register(models.Quizmaster)
class QuizmasterAdmin(ModelAdmin):
    list_display = ["name", "event_count"]
    list_display_links = ["name"]

    list_filter = [("events__game__venue", RelatedDropdownFilter)]
    list_filter_submit = True

    search_fields = ["name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Quizmaster]:
        qs = super().get_queryset(request)
        return qs.annotate(event_officiated_count=Count("events", distinct=True))

    @display(description="Events officiated", ordering="event_officiated_count")
    def event_count(self, obj: models.Quizmaster) -> int:
        return getattr(obj, "event_officiated_count")


@admin.register(models.Round)
class RoundAdmin(ModelAdmin):
    list_display = ["name", "number", "vote_count"]
    list_display_links = ["name", "number"]

    search_fields = ["name", "number"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Round]:
        qs = super().get_queryset(request)
        return qs.annotate(
            votes_held_count=Count(
                "votes__member_attendance__team_event_participation__event",
                distinct=True,
            )
        )

    @display(description="Number of votes held", ordering="votes_held_count")
    def vote_count(self, obj: models.Round) -> int:
        return getattr(obj, "votes_held_count")


@admin.register(models.Table)
class TableAdmin(ModelAdmin):
    list_display = ["table_id", "name", "is_upstairs", "times_sat_at"]
    list_display_links = ["table_id", "name"]

    list_filter = [
        ("team_participations__event__game__venue", RelatedDropdownFilter),
        ("is_upstairs", BooleanRadioFilter),
    ]
    list_filter_submit = True

    search_fields = ["table_id", "name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Table]:
        qs = super().get_queryset(request)
        return qs.annotate(seatings_count=Count("team_participations", distinct=True))

    @display(description="Times sat at", ordering="seatings_count")
    def times_sat_at(self, obj: models.Table) -> int:
        return getattr(obj, "seatings_count")


@admin.register(models.TeamEventParticipation)
class TeamEventParticipationAdmin(ModelAdmin):
    class MemberAttendanceInline(TabularInline):
        model = apps.get_model("api", "MemberAttendance")
        extra = 0
        fields = ["member", "acquired_seating"]
        readonly_fields = []
        autocomplete_fields = ["member"]

    inlines = [MemberAttendanceInline]

    list_display = ["team_name", "team__team_id", "event", "score", "table"]
    list_display_links = list_display

    list_select_related = ["team_name", "team", "event", "table"]

    list_filter = [("team", AutocompleteSelectFilter)]
    list_filter_submit = True

    search_fields = ["team_name__name", "team__team_id"]


@admin.register(models.Team)
class TeamAdmin(ModelAdmin):
    class IsGuestFilter(admin.SimpleListFilter):
        title = "Guest"
        parameter_name = "is_guest"

        def lookups(
            self, request: HttpRequest, model_admin: ModelAdmin
        ) -> list[tuple[str, str]]:
            return [
                ("yes", "Yes"),
                ("no", "No"),
            ]

        def queryset(
            self, request: HttpRequest, queryset: QuerySet[models.Team]
        ) -> QuerySet[models.Team]:
            if self.value() == "yes":
                return queryset.filter(team_id__isnull=True)
            if self.value() == "no":
                return queryset.filter(team_id__isnull=False)
            return queryset

    class TeamNameInline(TabularInline):
        model = models.TeamName
        extra = 0

    inlines = [TeamNameInline]

    list_display = ["latest_name", "team_id_link", "attendance_count", "last_seen"]

    list_filter = [
        ("event_participations__event__game__venue", RelatedDropdownFilter),
        IsGuestFilter,
    ]
    list_filter_submit = True

    search_fields = ["team_id"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Team]:
        qs = super().get_queryset(request)
        return qs.annotate(
            latest_name=Coalesce(
                Subquery(
                    models.TeamEventParticipation.objects.filter(team_id=OuterRef("pk"))
                    .order_by("-event__date")
                    .values("team_name__name")[:1]
                ),
                Subquery(
                    models.TeamName.objects.filter(team_id=OuterRef("pk"))
                    .order_by("-created_at")
                    .values("name")[:1]
                ),
            ),
            venue_url=Subquery(
                models.TeamEventParticipation.objects.filter(team_id=OuterRef("pk"))
                .order_by("-event__date")
                .values("event__game__venue__url")[:1]
            ),
            event_participations_count=Count("event_participations"),
            last_seen_date=Max("event_participations__event__date"),
        ).order_by("latest_name")

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet[models.Team], search_term: str
    ) -> tuple[QuerySet[models.Team], bool]:
        if not search_term:
            return queryset, False

        # Get PKs that match by team_id
        team_id_pks = queryset.filter(team_id__icontains=search_term).values_list(
            "pk", flat=True
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
        return getattr(obj, "latest_name")

    @display(description="Team ID", ordering="team_id")
    def team_id_link(self, obj: models.Team) -> str | None:
        if obj.team_id is None:
            return None

        venue_url = getattr(obj, "venue_url")
        if venue_url is None:
            return str(obj.team_id)
        else:
            url_netloc = urlparse(venue_url).netloc
            return format_html(
                '<a href="https://{}/teams/{}" target="_blank">{}</a>',
                url_netloc,
                obj.team_id,
                obj.team_id,
            )

    @display(description="Attendances", ordering="event_participations_count")
    def attendance_count(self, obj: models.Team) -> int:
        return getattr(obj, "event_participations_count")

    @display(description="Last seen", ordering="last_seen_date")
    def last_seen(self, obj: models.Team) -> date | None:
        return getattr(obj, "last_seen_date")


@admin.register(models.TeamName)
class TeamNameAdmin(ModelAdmin):
    list_display = ["name", "team", "guest"]

    list_select_related = ["team"]

    list_filter = [("team", AutocompleteSelectFilter), ("guest", BooleanRadioFilter)]
    list_filter_submit = True

    search_fields = ["name", "team__team_id"]


@admin.register(models.Theme)
class ThemeAdmin(ModelAdmin):
    list_display = ["name", "event_count"]

    list_filter = [("events__game__venue", RelatedDropdownFilter)]
    list_filter_submit = True

    search_fields = ["name"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Theme]:
        qs = super().get_queryset(request)
        return qs.annotate(event_count=Count("events"))

    @display(description="Number of events with theme", ordering="event_count")
    def event_count(self, obj: models.Theme) -> int:
        return getattr(obj, "event_count")


@admin.register(models.Venue)
class VenueAdmin(ModelAdmin):
    actions = ["scrape", "scrape_full"]

    list_display = [
        "name",
        "url_link",
        "last_scraped_at_styled",
        "game_count_official",
        "game_count_custom",
        "event_count",
        "quizmaster_count",
        "team_count",
    ]
    list_display_links = [
        "name",
    ]

    list_filter = [
        ("games__game_type", RelatedDropdownFilter),
        ("games__events__quizmaster", RelatedDropdownFilter),
        ("games__events__team_participations__team", AutocompleteSelectFilter),
    ]
    list_filter_submit = True

    search_fields = ["name", "url"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[models.Venue]:
        qs = super().get_queryset(request)
        return qs.annotate(
            official_game_count=Count(
                "games", filter=Q(games__day__isnull=False), distinct=True
            ),
            custom_game_count=Count(
                "games", filter=Q(games__day__isnull=True), distinct=True
            ),
            event_count=Count("games__events", distinct=True),
            quizmaster_count=Count("games__events__quizmaster", distinct=True),
            team_count=Count("games__events__team_participations__team", distinct=True),
        )

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
        last_scraped_at = getattr(obj, "last_scraped_at")

        if last_scraped_at is None:
            return "", None

        age = timezone.now() - last_scraped_at

        if age <= timedelta(hours=1):
            return "within_hour", last_scraped_at
        elif age <= timedelta(days=1):
            return "within_day", last_scraped_at
        elif age <= timedelta(weeks=1):
            return "within_week", last_scraped_at
        else:
            return "old", last_scraped_at

    @display(description="Official games", ordering="official_game_count")
    def game_count_official(self, obj: models.Venue) -> int:
        return getattr(obj, "official_game_count")

    @display(description="Custom games", ordering="custom_game_count")
    def game_count_custom(self, obj: models.Venue) -> int:
        return getattr(obj, "custom_game_count")

    @display(description="Events held", ordering="event_count")
    def event_count(self, obj: models.Venue) -> int:
        return getattr(obj, "event_count")

    @display(description="Quizmasters", ordering="quizmaster_count")
    def quizmaster_count(self, obj: models.Venue) -> int:
        return getattr(obj, "quizmaster_count")

    @display(description="Teams", ordering="team_count")
    def team_count(self, obj: models.Venue) -> int:
        return getattr(obj, "team_count")

    def _scrape_venue(
        self, request: HttpRequest, venue: models.Venue, end_date: str | None
    ) -> None:
        try:
            service = ScraperService()

            data = service.scrape_data(source_url=venue.url, end_date=end_date)

            service.push_to_db(data)

            self.message_user(
                request,
                message=f"Successfully {'scraped data' if end_date is None else 'performed full scrape'} for {venue.name}",
                level="success",
            )
        except Exception as e:
            self.message_user(
                request,
                message=f"Error {'scraping' if end_date is None else 'performing full scrape for'} {venue.name}: {str(e)}",
                level="error",
            )

    @action(description="Scrape new data for selected venues")
    def scrape(self, request: HttpRequest, queryset: QuerySet[models.Venue]) -> None:
        for venue in queryset:
            self._scrape_venue(request=request, venue=venue, end_date=None)

    @action(description="Force full re-scrape for selected venues")
    def scrape_full(
        self, request: HttpRequest, queryset: QuerySet[models.Venue]
    ) -> None:
        for venue in queryset:
            self._scrape_venue(request=request, venue=venue, end_date="1970-01-01")


@admin.register(models.Vote)
class VoteAdmin(ModelAdmin):
    list_display = [
        "member_name",
        "vote_colored",
        "double_or_nothing",
        "round",
        "date",
    ]
    list_display_links = [
        "member_name",
        "vote_colored",
        "double_or_nothing",
    ]

    list_filter = [
        ("member_attendance__member", RelatedDropdownFilter),
        "vote",
        "is_double_or_nothing",
        "round",
    ]
    list_filter_submit = True

    list_select_related = [
        "member_attendance__team_event_participation__event",
        "member_attendance__member",
        "round",
    ]

    search_fields = [
        "member_attendance__member__name",
    ]

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
        return vote_enum.value, vote_enum.label

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

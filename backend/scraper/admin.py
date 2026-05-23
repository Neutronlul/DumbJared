from typing import TYPE_CHECKING, override

from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseRedirect
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from scraper import models
from scraper.exceptions import (
    EmailNotRoutedError,
    ScraperLoginError,
    ScraperPostError,
    ScraperUnexpectedResponseError,
)
from scraper.tasks import authenticate_account, update_account_data, update_token
from scraper.utils.accounts import AccountManager

if TYPE_CHECKING:
    from django.db.models import Model as DjangoModel
    from django.db.models import QuerySet
    from django.forms import Form
    from django.http import HttpRequest


@admin.register(models.ScraperAccount)
class ScraperAccountAdmin(ModelAdmin):
    class IsAuthenticatedFilter(admin.SimpleListFilter):
        title = "Authenticated"
        parameter_name = "is_authenticated"

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
            queryset: QuerySet[models.ScraperAccount],
        ) -> QuerySet[models.ScraperAccount]:
            value = self.value()

            if value == "yes":
                return queryset.exclude(token="")
            if value == "no":
                return queryset.filter(token="")

            return queryset

    actions = ("refresh_data", "authenticate")

    list_display = ("name", "email", "player_id", "is_authenticated")
    list_display_links = ("name", "email", "player_id")

    list_filter = (IsAuthenticatedFilter,)

    readonly_fields = ("player_id", "token")

    search_fields = ("name", "email", "player_id")

    @override
    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: DjangoModel | None = None,
    ) -> tuple[str, ...]:
        # Only expose the email field on creation
        if obj is not None:
            return ("email", *self.readonly_fields)

        return self.readonly_fields

    @override
    def save_model(
        self,
        request: HttpRequest,
        obj: DjangoModel,
        form: Form,
        change: bool,
    ) -> None:
        self._save_failed = False

        # Type narrow first
        if not isinstance(obj, models.ScraperAccount):
            super().save_model(request, obj, form, change)
            return

        # The only field that can be changed after creation is the name
        if change and "name" in form.changed_data:
            ac = AccountManager()

            if obj.token:
                # While this technically updates the name on the AccountManager
                # instance, it bypasses the setter method so we still need to "manually"
                # update the name on the remote.
                ac.jwt = obj.token

                # This is done synchronously because it should be fast (single API call)
                # and failure should be immediately visible in the admin interface
                try:
                    ac.name = obj.name
                except (ScraperPostError, ScraperUnexpectedResponseError) as e:
                    self.message_user(
                        request,
                        f"Failed to update name on remote: {e}",
                        level="error",
                    )
                    self._save_failed = True
                    return  # Without saving

                # This should almost never be necessary but whatever
                obj.player_id = ac.player_id

                # This is less important, and can be done asynchronously
                # because "old" tokens still work.
                update_token.delay(account_pk=obj.pk, current_token=obj.token)

            else:
                # This is unlikely to work because it would require an unset token and a
                # routed address, but it doesn't hurt to try.
                # For that reason, even though this could block the request cycle for
                # a while, I'm doing it synchronously.

                ac.email = obj.email

                try:
                    ac.login()
                except EmailNotRoutedError:
                    self.message_user(
                        request,
                        (
                            "Name updated locally, but email is not routed to worker, "
                            "so unable to authenticate and update name on remote."
                        ),
                        level="warning",
                    )
                    super().save_model(request, obj, form, change)
                    return

                except (
                    ScraperLoginError,
                    ScraperPostError,
                    ScraperUnexpectedResponseError,
                    TimeoutError,
                    ImproperlyConfigured,
                ) as e:
                    self.message_user(
                        request,
                        f"Unable to change name: {e}",
                        level="error",
                    )
                    self._save_failed = True
                    return  # Without saving

                try:
                    ac.name = obj.name
                except (ScraperPostError, ScraperUnexpectedResponseError) as e:
                    self.message_user(
                        request,
                        f"Failed to update name on remote: {e}",
                        level="error",
                    )
                    self._save_failed = True
                    return  # Without saving

                # I figure there's a good chance that if this branch is
                # reached, the ID won't be set
                obj.player_id = ac.player_id

                # Finally, update the token in the background. Importantly, we can't use
                # the token from the AccountManager instance here because updating the
                # name almost definitely invalidated it.
                update_token.delay(account_pk=obj.pk, current_token=ac.jwt)

        super().save_model(request, obj, form, change)

        # On creation, populate the player ID and token fields
        if not change:
            authenticate_account.delay(
                account_pk=obj.pk,
                email=obj.email,
                name=obj.name,
            )

    @override
    def response_change(
        self,
        request: HttpRequest,
        obj: DjangoModel,
    ) -> HttpResponse:
        # If _save_failed is set by save_model, we want to suppress the
        # normal Django admin success message that would be shown after a
        # successful save. Redirecting back to the same page without calling
        # the superclass response_change effectively squashes that message.
        if self._save_failed:
            self._save_failed = False
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @display(description="Authenticated", ordering="token", boolean=True)
    def is_authenticated(self, obj: models.ScraperAccount) -> bool:
        return obj.token != ""

    @action(description="Refresh data for selected accounts")  # ty:ignore[call-non-callable]
    def refresh_data(
        self,
        request: HttpRequest,
        queryset: QuerySet[models.ScraperAccount],
    ) -> None:
        self.message_user(
            request,
            f"Queueing refresh of data for {queryset.count()} accounts.",
        )
        for account_pk in queryset.values_list("pk", flat=True):
            update_account_data.delay(account_pk=account_pk)

    @action(description="Authenticate selected accounts")  # ty:ignore[call-non-callable]
    def authenticate(
        self,
        request: HttpRequest,
        queryset: QuerySet[models.ScraperAccount],
    ) -> None:
        valid_accounts = queryset.filter(token="")
        valid_count = valid_accounts.count()
        total_count = queryset.count()

        if valid_count > 0:
            self.message_user(
                request,
                f"Queueing authentication for {valid_count} accounts.",
            )
        else:
            self.message_user(
                request,
                "All selected accounts are already authenticated.",
                level="warning",
            )
            return

        if total_count != valid_count:
            self.message_user(
                request,
                "Some selected accounts are already authenticated and will be skipped.",
                level="warning",
            )

        for pk, email, name in valid_accounts.values_list(
            "pk",
            "email",
            "name",
        ):
            authenticate_account.delay(
                account_pk=pk,
                email=email,
                name=name,
            )

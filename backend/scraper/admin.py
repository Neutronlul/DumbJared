from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from scraper import models


@admin.register(models.ScraperAccount)
class ScraperAccountAdmin(ModelAdmin):
    list_display = ("name", "email", "is_authenticated")
    list_display_links = ("name", "email")

    readonly_fields = ("token", "player_id")

    search_fields = ("name", "email")

    @display(description="Authenticated", ordering="token", boolean=True)
    def is_authenticated(self, obj: models.ScraperAccount) -> bool:
        return obj.token != ""

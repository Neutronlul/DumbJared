from django.contrib import admin
from unfold.admin import ModelAdmin

from scraper import models


@admin.register(models.ScraperAccount)
class ScraperAccountAdmin(ModelAdmin):
    list_display = ("name", "email", "player_id")

    readonly_fields = ("token", "player_id")

    search_fields = ("name", "email")

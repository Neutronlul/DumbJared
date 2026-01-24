from django.contrib import admin
from django.apps import apps
from unfold.admin import ModelAdmin
from api import models

# Get all models from the current app
app_models = apps.get_app_config("api").get_models()

for model in app_models:
    admin.site.register(model, ModelAdmin)


# @admin.action(description="Scrape data for selected venues")
# def scrape(modeladmin, request, queryset):
#     for venue in queryset:
#         from scraper.services.scraper_service import ScraperService

#         service = ScraperService()
#         try:
#             data = service.scrape_data(
#                 source_url=venue.url,
#                 end_date=None,
#             )
#             service.push_to_db(data)
#             modeladmin.message_user(
#                 request, f"Successfully scraped and updated data for {venue.name}."
#             )
#         except Exception as e:
#             modeladmin.message_user(
#                 request,
#                 f"Failed to scrape data for {venue.name}: {str(e)}",
#                 level="error",
#             )


# class VenueAdmin(admin.ModelAdmin):
#     actions = [scrape]


# admin.site.unregister(models.Venue)
# admin.site.register(models.Venue, VenueAdmin)


# # admin.py
# class TeamNameInline(admin.TabularInline):
#     model = models.TeamName
#     extra = 1
#     fields = ["name", "team"]


# admin.site.unregister(models.Team)


# @admin.register(models.Team)
# class TeamAdmin(admin.ModelAdmin):
#     inlines = [TeamNameInline]
#     list_display = ["team_id", "__str__", "created_at"]

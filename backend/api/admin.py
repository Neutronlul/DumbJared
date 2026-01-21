from django.contrib import admin
from django.apps import apps
from unfold.admin import ModelAdmin

# Get all models from the current app
app_models = apps.get_app_config("api").get_models()

for model in app_models:
    admin.site.register(model, ModelAdmin)

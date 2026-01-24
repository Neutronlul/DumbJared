from api.models import Event
from django.utils import timezone
from model_bakery import baker
from scraper.tasks import generate_placeholder_event, auto_scrape, reenable_scraping
import pytest


pytestmark = pytest.mark.django_db


class TestGeneratePlaceholderEvent:
    def test_placeholder_event_created(self):
        game = baker.make("api.Game")

        today = timezone.localdate()
        generate_placeholder_event(game_pk=game.pk)

        assert Event.objects.filter(
            game=game,
            date=today,
            end_datetime__isnull=True,
            description__isnull=True,
            quizmaster__isnull=True,
            theme__isnull=True,
        ).exists()


class TestAutoScrape:
    pass


class TestReenableScraping:
    pass

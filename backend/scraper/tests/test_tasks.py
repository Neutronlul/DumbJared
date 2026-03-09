from api.models import Event
from django.utils import timezone
from model_bakery import baker
from scraper.tasks import generate_placeholder_event, reenable_scraping
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
    def test_orphaned_placeholder_deleted_and_task_reenabled(self, mocker):
        today = timezone.localdate()

        mocker.patch("django.utils.timezone.localdate", return_value=today)

        game = baker.make("api.Game", game_type__name="Test Game")

        orphaned_event = baker.make(
            "api.Event",
            game=game,
            date=today - timezone.timedelta(days=1),
            quizmaster=None,
        )

        scrape_task = baker.make(
            "django_celery_beat.PeriodicTask",
            name=f"{game} - Auto scrape",
            enabled=False,
            interval=baker.make("django_celery_beat.IntervalSchedule"),
        )

        assert Event.objects.filter(pk=orphaned_event.pk).exists()
        assert not scrape_task.enabled

        reenable_scraping(game_pk=game.pk, task_name=scrape_task.name)

        assert not Event.objects.filter(pk=orphaned_event.pk).exists()
        scrape_task.refresh_from_db()
        assert scrape_task.enabled

    def test_no_orphaned_placeholder_but_task_reenabled(self, mocker):
        today = timezone.localdate()

        mocker.patch("django.utils.timezone.localdate", return_value=today)

        game = baker.make("api.Game", game_type__name="Test Game")

        event = baker.make(
            "api.Event",
            game=game,
            date=today - timezone.timedelta(days=1),
            quizmaster=baker.make("api.Quizmaster"),
        )

        scrape_task = baker.make(
            "django_celery_beat.PeriodicTask",
            name=f"{game} - Auto scrape",
            enabled=False,
            interval=baker.make("django_celery_beat.IntervalSchedule"),
        )

        assert Event.objects.filter(pk=event.pk).exists()
        assert not scrape_task.enabled

        reenable_scraping(game_pk=game.pk, task_name=scrape_task.name)

        assert Event.objects.filter(pk=event.pk).exists()
        scrape_task.refresh_from_db()
        assert scrape_task.enabled

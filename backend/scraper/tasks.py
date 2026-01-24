from api.models import Event
from celery import shared_task
from datetime import timedelta
from django_celery_beat.models import PeriodicTask
from django.utils import timezone
from scraper.services.scraper_service import ScraperService
import logging


logger = logging.getLogger(__name__)


@shared_task
def generate_placeholder_event(game_pk: int):
    Event.objects.create(game_id=game_pk, date=timezone.localdate())


@shared_task
def auto_scrape(game_pk: int, url: str, task_name: str):
    service = ScraperService(is_manual=False)

    most_recent_event = (
        Event.objects.filter(game__venue__url=url, quizmaster__isnull=False)
        .order_by("-date")
        .first()
    )

    logger.info(f"Most recent event in database for {url}: {most_recent_event}")

    date = timezone.localdate()

    end_date = most_recent_event.date if most_recent_event else date - timedelta(days=1)

    data = service.scrape_data(source_url=url, end_date=end_date)

    if not service.push_to_db(data=data, autoscrape_game_id=game_pk):
        return

    PeriodicTask.objects.filter(name=task_name).update(enabled=False)


@shared_task
def reenable_scraping(game_pk: int, task_name: str):
    orphaned_event = Event.objects.filter(
        game_id=game_pk,
        date=timezone.localdate() - timedelta(days=1),
    ).first()

    # If orphaned placeholder event exists, delete it
    if orphaned_event:
        orphaned_event.delete()
        logger.warning(f"Deleted orphaned placeholder event for game {game_pk}")

    # Otherwise, re-enable scraping task
    else:
        PeriodicTask.objects.filter(name=task_name).update(enabled=True)

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from api.models import Event
from scraper.exceptions import EmailNotRoutedError
from scraper.models import ScraperAccount
from scraper.services.scraper_service import ScraperService
from scraper.utils.accounts import AccountManager
from scraper.utils.live_scraper import LiveScraper

logger = logging.getLogger(__name__)


@shared_task
def generate_placeholder_event(game_pk: int) -> None:
    Event.objects.create(game_id=game_pk, date=timezone.localdate())


@shared_task
def auto_scrape(game_pk: int, url: str, task_name: str) -> None:
    service = ScraperService(is_manual=False)

    most_recent_event = (
        Event.objects.filter(game__venue__url=url, quizmaster__isnull=False)
        .order_by("-date")
        .first()
    )

    logger.info("Most recent event in database for %s: %s", url, most_recent_event)

    date = timezone.localdate()

    end_date = most_recent_event.date if most_recent_event else date - timedelta(days=1)

    data = service.scrape_data(source_url=url, end_date=end_date)

    if not service.push_to_db(data=data, autoscrape_game_id=game_pk):
        return

    PeriodicTask.objects.filter(name=task_name).update(enabled=False)


@shared_task
def reenable_scraping(game_pk: int, task_name: str) -> None:
    orphaned_event = Event.objects.filter(
        game_id=game_pk,
        date=timezone.localdate() - timedelta(days=1),
        quizmaster__isnull=True,
    ).first()

    # If orphaned placeholder event exists, delete it
    if orphaned_event:
        orphaned_event.delete()
        logger.warning("Deleted orphaned placeholder event for game %s", game_pk)

    # Either way, re-enable scraping task
    PeriodicTask.objects.filter(name=task_name).update(enabled=True)


@shared_task
def populate_slug(event_pk: int, join_code: str) -> None:
    slug = LiveScraper().fetch_game_id(join_code=join_code)
    Event.objects.filter(pk=event_pk).update(slug=slug)


@shared_task
def authenticate_account(account_pk: int, email: str, name: str) -> None:
    ac = AccountManager(email=email)

    try:
        if ac.exists():
            ac.login()
            if ac.name != name:
                ac.name = name
                ac.refresh_token()
        else:
            ac.login(username=name)
    except EmailNotRoutedError:
        logger.info(
            "Email %s is not routed to worker; cannot authenticate",
            email,
        )
        return
    except Exception:
        logger.exception(
            "Failed to authenticate account %s",
            email,
        )
        return

    ScraperAccount.objects.filter(pk=account_pk).update(
        name=ac.name,
        token=ac.jwt,
        player_id=ac.player_id,
    )


@shared_task
def update_token(account_pk: int, current_token: str) -> None:
    ac = AccountManager()

    ac.jwt = current_token

    try:
        ac.refresh_token()
    except Exception:
        logger.exception("Failed to update token for account %s", account_pk)
        raise

    ScraperAccount.objects.filter(pk=account_pk).update(token=ac.jwt)


@shared_task
def update_account_data(account_pk: int) -> None:
    account = ScraperAccount.objects.get(pk=account_pk)
    ac = AccountManager()

    if account.token:
        ac.jwt = account.token
        try:
            ac.refresh_token()
        except Exception:
            logger.exception(
                "Failed to refresh token for account %s",
                account.email,
            )
            return

    else:
        ac.email = account.email

        try:
            ac.login()
        except EmailNotRoutedError:
            logger.info(
                "Email %s is not routed to worker; cannot update data",
                account.email,
            )
            return
        except Exception:
            logger.exception(
                "Failed to authenticate account %s for data update",
                account.email,
            )
            return

    new_data = {"name": ac.name, "player_id": ac.player_id, "token": ac.jwt}
    changed_fields = []

    for field, value in new_data.items():
        if getattr(account, field) != value:
            setattr(account, field, value)
            changed_fields.append(field)

    if changed_fields:
        account.save(update_fields=changed_fields)

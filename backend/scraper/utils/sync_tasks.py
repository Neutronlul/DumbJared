import json
import logging
from datetime import time
from typing import TYPE_CHECKING

from django_celery_beat.models import CrontabSchedule, PeriodicTask

if TYPE_CHECKING:
    from api.models import Game


logger = logging.getLogger(__name__)


def sync(games: list[Game], scrape_interval: int = 2) -> None:
    """Sync periodic tasks for official games.

    :param games: List of official Game instances to create tasks for
    :type games: list[Game]
    """
    synced_games = 0
    for game in games:
        if game.day is None or game.time is None:
            raise ValueError("Game must have both day and time set to sync.")

        unique_name = f"{game} - Auto scrape"  # For use as lookup key for reenable_task

        # Generate a placeholder event an hour before the game starts
        generate_placeholder_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=str(game.time.minute),
            hour=str(game.time.hour - 1),
            day_of_week=str(
                (
                    game.day
                    # CrontabSchedule uses 0=Sunday, 6=Saturday (bad, wrong, and dumb)
                    # so we have to offset the day by 1 and modulo
                    + 1
                )
                % 7,
            ),
            day_of_month="*",
            month_of_year="*",
        )

        PeriodicTask.objects.get_or_create(
            name=f"{game} - Generate placeholder event",
            task="scraper.tasks.generate_placeholder_event",
            crontab=generate_placeholder_schedule,
            kwargs=json.dumps({"game_pk": game.pk}),
        )

        # Automatic scraping task
        #
        # This runs every `scrape_interval` minutes for
        # two hours, starting an hour after the game starts,
        # rounded to the nearest hour (30 mins is rounded up).
        #
        # For games that get rounded up, the scraping window is extended by an hour.
        #
        # I.e. a game starting at 7:00-29 PM will run at:
        # 8:00-9:58 PM, every `scrape_interval` minutes
        #
        # A game starting at 7:30-59 PM will run at:
        # 8:00-10:58 PM, every `scrape_interval` minutes
        scrape_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=f"*/{scrape_interval}",
            hour=_generate_crontab_hours(game_time=game.time),
            day_of_week=str((game.day + 1) % 7),
            day_of_month="*",
            month_of_year="*",
        )

        PeriodicTask.objects.get_or_create(
            name=unique_name,
            task="scraper.tasks.auto_scrape",
            crontab=scrape_schedule,
            kwargs=json.dumps(
                {"game_pk": game.pk, "url": game.venue.url, "task_name": unique_name},
            ),
        )

        # Re-enable scraping task
        # Runs the day after the game at midnight
        reenable_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="0",
            day_of_week=str((game.day + 2) % 7),
            day_of_month="*",
            month_of_year="*",
        )

        PeriodicTask.objects.get_or_create(
            name=f"{game} - Re-enable scraping",
            task="scraper.tasks.reenable_scraping",
            crontab=reenable_schedule,
            kwargs=json.dumps({"game_pk": game.pk, "task_name": unique_name}),
        )

        synced_games += 1

    logger.info("Synced %s games with periodic tasks.", synced_games)


def _generate_crontab_hours(game_time: time) -> str:
    max_start_time = time(hour=21, minute=30)
    half_hour = 30

    # This would be really annoying to handle properly
    if game_time >= max_start_time:
        raise NotImplementedError(
            "Games must start before 9:30 PM.",
        )

    if game_time.minute < half_hour:
        return f"{game_time.hour + 1}-{game_time.hour + 2}"

    return f"{game_time.hour + 1}-{game_time.hour + 3}"

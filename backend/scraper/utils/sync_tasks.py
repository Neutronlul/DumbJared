from api.models import Game
from datetime import time
from django_celery_beat.models import CrontabSchedule, PeriodicTask
import json
import logging
# from scraper import tasks


logger = logging.getLogger(__name__)


def sync(games: list[Game], scrape_interval: int = 2):
    """
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
                    + 1  # CrontabSchedule uses 0=Sunday, 6=Saturday (bad, wrong, and dumb)
                )
                % 7
            ),
            day_of_month="*",
            month_of_year="*",
        )

        # Automatic scraping task schedule
        #
        # This runs every `scrape_interval` minutes for two hours, starting
        # an hour after the game starts, rounded to the nearest hour (30 mins is rounded up).
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

        # Re-enable scraping task schedule
        # Runs the day after the game at midnight
        reenable_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="0",
            day_of_week=str((game.day + 2) % 7),
            day_of_month="*",
            month_of_year="*",
        )

        generate_placeholder_task, _ = PeriodicTask.objects.get_or_create(
            name=f"{game} - Generate placeholder event",
            task="scraper.tasks.generate_placeholder_event",
            crontab=generate_placeholder_schedule,
            kwargs=json.dumps({"game_pk": game.pk}),
        )

        scrape_task, _ = PeriodicTask.objects.get_or_create(
            name=unique_name,
            task="scraper.tasks.auto_scrape",
            crontab=scrape_schedule,
            kwargs=json.dumps(
                {"game_pk": game.pk, "url": game.venue.url, "task_name": unique_name}
            ),
        )

        reenable_task, _ = PeriodicTask.objects.get_or_create(
            name=f"{game} - Re-enable scraping",
            task="scraper.tasks.reenable_scraping",
            crontab=reenable_schedule,
            kwargs=json.dumps({"game_pk": game.pk, "task_name": unique_name}),
        )

        synced_games += 1

    logger.info(f"Synced {synced_games} games with periodic tasks.")


def _generate_crontab_hours(game_time: time) -> str:
    if game_time >= time(hour=21, minute=30):
        raise NotImplementedError(
            "Games must start before 9:30 PM."  # This would be really annoying to handle properly
        )

    if game_time.minute < 30:
        return f"{game_time.hour + 1}-{game_time.hour + 2}"
    else:
        return f"{game_time.hour + 1}-{game_time.hour + 3}"

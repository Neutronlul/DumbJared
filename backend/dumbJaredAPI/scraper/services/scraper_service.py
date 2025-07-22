from dumbJaredAPI.scraper.utils.trivia_scraper import TriviaScraper
from dumbJaredAPI.api.models import (
    Quizmaster,
    Team,
    Event,
    TeamEventParticipation,
)
from django.db import transaction
from datetime import datetime

from django.db import IntegrityError


class ScraperService:
    def scrape_data(self, source_url, end_date) -> dict:
        # In order of priority:
        # 1. Try to use the provided end_date if valid
        #    (format: YYYY-MM-DD)
        # 2. Use the last event's date from the database if available
        # 3. Default to a hardcoded date (e.g., 2024-08-08) if no other date is available
        if end_date is not None:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD.")
        else:
            if Event.objects.exists():
                end_date = Event.objects.latest("date").date
                # TODO: log this
            else:
                end_date = datetime(2021, 9, 15).date()

        scraper = TriviaScraper(source_url, end_date)

        try:
            scraped_data = scraper.scrape()
            return scraped_data
        except Exception as e:
            # TODO: change this to a logger/somthing else
            print(f"Error scraping data: {e}")
            raise

    def pushToDB(self, data):
        with transaction.atomic():
            qms = []
            events = []
            teams = []

            for date, instance in data.items():
                qms.append(instance["quizmaster"])

                Quizmaster.objects.get_or_create(name=instance["quizmaster"])

                Event.objects.get_or_create(
                    date=date.date(),
                    quizmaster=Quizmaster.objects.get(name=instance["quizmaster"]),
                )

                for team in instance["teams"]:
                    Team.objects.get_or_create(
                        name=team["name"],
                        # team_id=team["team_id"],
                    )
                    try:
                        tep, created = TeamEventParticipation.objects.get_or_create(
                            team=Team.objects.get(name=team["name"]),
                            event=Event.objects.get(date=date.date()),
                            score=team["score"],
                        )
                    except IntegrityError:
                        print(
                            f"IntegrityError: Duplicate team-event combo - "
                            f"team={team['name']}, event={date.date()}, score={team['score']}"
                        )

            # Quizmaster.objects.bulk_create(list(set(qms)), ignore_conflicts=True)

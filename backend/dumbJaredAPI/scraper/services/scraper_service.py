from dumbJaredAPI.scraper.utils.trivia_scraper import TriviaScraper
from dumbJaredAPI.api.models import (
    Quizmaster,
    Team,
    Event,
    TeamEventParticipation,
)
from django.db import transaction
from datetime import datetime


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
                end_date = datetime(
                    2021, 9, 15
                ).date()  # one day before the first event

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
            # qms = {instance["quizmaster"] for instance in data.values()}
            qms = set()

            # teams = {
            #     (team["name"], team["team_id"])
            #     for instance in data.values()
            #     for team in instance["teams"]
            # }
            teams = set()

            events = []

            teps = []

            for date, instance in data.items():
                qmsOBJ = Quizmaster(name=instance["quizmaster"])
                qms.add(instance["quizmaster"])

                eventOBJ = Event(
                    date=date.date(),
                    quizmaster=qmsOBJ,
                )
                events.append(eventOBJ)

                for team in instance["teams"]:
                    teamOBJ = Team(name=team["name"], team_id=team["team_id"])
                    teams.append(teamOBJ)

                    teps.append(
                        TeamEventParticipation(teamOBJ, eventOBJ, team["score"])
                    )

            Quizmaster.objects.bulk_create(qms, ignore_conflicts=True)
            Event.objects.bulk_create(events, ignore_conflicts=True)
            Team.objects.bulk_create(teams, ignore_conflicts=True)
            TeamEventParticipation.objects.bulk_create(teps, ignore_conflicts=True)

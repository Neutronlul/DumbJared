from datetime import date, datetime

from django.db import transaction

# TODO: Sort these
from api.models import (
    Event,
    EventType,
    Venue,
)
from scraper.utils.trivia_scraper import TriviaScraper


class ScraperService:
    def __init__(self, source_url: str, end_date: str):
        self.source_url = source_url
        self.end_date = end_date

    def process_end_date(self) -> date | None:
        # In order of priority:
        # 1. Try to use the provided end_date if valid
        #    (format: YYYY-MM-DD)
        # 2. Use the last event's date from the database for the provided venue url if available
        # 3. Default to None if no other date is available
        if self.end_date is not None:
            try:
                return datetime.strptime(self.end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD.")
        else:
            try:
                return (
                    Event.objects.filter(venue__url=self.source_url)
                    .latest("start_datetime")
                    .start_datetime.date()
                )
            except Event.DoesNotExist:
                return None

    def scrape_data(self) -> dict:
        scraper = TriviaScraper(self.source_url, self.process_end_date())

        try:
            scraped_data = scraper.scrape()
            return scraped_data
        except Exception as e:
            # TODO: change this to a logger/something else
            print(f"Error scraping data: {e}")
            raise

    # def pushToDB(self, data):
    # with transaction.atomic():
    #     # qms = {instance["quizmaster"] for instance in data.values()}
    #     qms = set()

    #     # teams = {
    #     #     (team["name"], team["team_id"])
    #     #     for instance in data.values()
    #     #     for team in instance["teams"]
    #     # }
    #     teams = set()

    #     events = []

    #     teps = []

    #     for date, instance in data.items():
    #         qmsOBJ = Quizmaster(name=instance["quizmaster"])
    #         qms.add(instance["quizmaster"])

    #         eventOBJ = Event(
    #             date=date.date(),
    #             quizmaster=qmsOBJ,
    #         )
    #         events.append(eventOBJ)

    #         for team in instance["teams"]:
    #             teamOBJ = Team(name=team["name"], team_id=team["team_id"])
    #             teams.append(teamOBJ)

    #             teps.append(
    #                 TeamEventParticipation(teamOBJ, eventOBJ, team["score"])
    #             )

    #     Quizmaster.objects.bulk_create(qms, ignore_conflicts=True)
    #     Event.objects.bulk_create(events, ignore_conflicts=True)
    #     Team.objects.bulk_create(teams, ignore_conflicts=True)
    #     TeamEventParticipation.objects.bulk_create(teps, ignore_conflicts=True)

    def push_to_db(self, data):
        with transaction.atomic():
            # Add the venue name and url if not already in db
            # If the name has changed, update it
            venue, _created = Venue.objects.update_or_create(
                url=self.source_url,
                defaults={"name": data["venue_data"]["name"]},
            )

            # TODO: Use the events list to bulk create events
            _events = [
                Event(
                    venue=venue,
                    game_type=EventType.objects.get_or_create(name=event["game_type"])[
                        0
                    ],
                    # start_datetime
                )
                for event in data["event_data"]
            ]

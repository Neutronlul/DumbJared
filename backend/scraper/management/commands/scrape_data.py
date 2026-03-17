from typing import TYPE_CHECKING, Any, override

from django.core.management.base import BaseCommand

from scraper.services.scraper_service import ScraperService

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Scrape data from trivia website and save it to the database"

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--url",
            metavar="URL",
            type=str,
            required=True,
            help="The base URL of the website to scrape data from",
        )
        parser.add_argument(
            "--end-date",
            metavar="YYYY-MM-DD",
            type=str,
            required=False,
            default=None,
            help="The date to stop scraping at, in YYYY-MM-DD format",
        )

    @override
    def handle(self, *_args: Any, **options: Any) -> None:
        service = ScraperService()

        data = service.scrape_data(
            source_url=options["url"],
            end_date=options["end_date"],
        )

        service.push_to_db(data)

        self.stdout.write(self.style.SUCCESS("Data scraped and saved successfully."))

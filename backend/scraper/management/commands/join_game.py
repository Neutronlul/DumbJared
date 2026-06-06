import re
from argparse import ArgumentTypeError
from typing import TYPE_CHECKING, Any, override

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from core.constants import HEX_24_REGEX, JOIN_CODE_REGEX
from scraper.exceptions import (
    ScraperFetchError,
    ScraperGameNotFoundError,
    ScraperPostError,
    ScraperUnexpectedResponseError,
)
from scraper.utils.live_scraper import LiveScraper

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Join a live game using a join code (or slug) and UUID."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--code",
            metavar="XXXXXX",
            type=lambda v: self.validate_type(
                v,
                JOIN_CODE_REGEX,
                "join code",
                "6 digits",
            ),
            required=False,
            help="The code of the game to join.",
        )
        parser.add_argument(
            "--uuid",
            metavar="UUID",
            type=str,
            required=True,
            help="The client ID to use when joining the game.",
        )
        parser.add_argument(
            "--slug",
            metavar="SLUG",
            type=lambda v: self.validate_type(
                v,
                HEX_24_REGEX,
                "slug",
                "24 hexadecimal characters",
            ),
            required=False,
            help=(
                "Slug of the game to join "
                "(optional; looked up via join code if not provided)."
            ),
        )

    @override
    def handle(self, *args: Any, **options: Any) -> None:
        scraper = LiveScraper()
        join_code = options["code"]
        client_id = options["uuid"]
        slug = options["slug"]

        if not slug:
            if not join_code:
                msg = "Either code or slug must be provided to join a game."
                raise CommandError(
                    msg,
                )

            try:
                slug = scraper.fetch_game_id(
                    join_code,
                    client_id,
                )
            except (
                ValueError,
                ScraperGameNotFoundError,
                ScraperFetchError,
                ScraperUnexpectedResponseError,
            ) as e:
                msg = f"Error occurred while fetching game ID: {e}"
                raise CommandError(msg) from e

        try:
            scraper.join_game(slug, client_id)
        except (ValueError, ScraperPostError, ScraperUnexpectedResponseError) as e:
            msg = f"Error occurred while joining game: {e}"
            raise CommandError(msg) from e

        self.stdout.write(self.style.SUCCESS("Successfully joined game"))

    def validate_type(
        self,
        value: str,
        pattern: str,
        name: str,
        reason: str,
    ) -> str:
        if not re.fullmatch(pattern, value):
            msg = f"Invalid {name} '{value}'. {name.capitalize()} must be {reason}."
            raise ArgumentTypeError(msg)
        return value

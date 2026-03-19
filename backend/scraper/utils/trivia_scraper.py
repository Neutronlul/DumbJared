import logging
from calendar import day_name
from datetime import date, time
from re import compile as re_compile
from typing import TYPE_CHECKING, cast, override

from requests import Session

from scraper.exceptions import ScraperParseError, ScraperUnexpectedPageError
from scraper.types import EventData, GameData, PageData, TeamData, VenueData
from scraper.utils.base_scraper import BaseScraper

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag


logger = logging.getLogger(__name__)


class TriviaScraper(BaseScraper[date | None]):
    @override
    def __init__(self, base_url: str, break_flag: date | None) -> None:
        super().__init__(base_url, break_flag)
        self.done_scraping = False

    def _extract_venue_data(self, soup: BeautifulSoup) -> VenueData:
        # Check if the page even fits the expected format
        if not soup.select_one(".game_times > li > div:nth-child(1) > b:nth-child(1)"):
            raise ScraperUnexpectedPageError

        # Get venue name
        venue_name = (
            venue_name_element := soup.select_one(".venue_address > h3:nth-child(1)")
        ) and venue_name_element.get_text(strip=True)

        if not isinstance(venue_name, str):
            target = "venue name"
            source = "page"
            raise ScraperParseError(target, source)

        # Get event types and their times
        # Expected format: GAME TYPE—Mondays @ 1:00pm
        # Extracts:
        # type: str: "GAME TYPE"
        # day: int: 0
        # time: datetime.time(): 13:00
        games = [
            GameData(
                type=(game_parsed := game.get_text(strip=True)).split("—")[0],
                day=list(day_name).index(game_parsed.split("—")[1].split("s @")[0]),
                time=time.strptime(game_parsed.split("@ ")[1].upper(), "%I:%M%p"),
            )
            for game in soup.select(
                ".game_times > li > div:nth-child(1) > b:nth-child(1)",
            )
        ]

        return VenueData(
            name=venue_name,
            games=games,
        )

    def _parse_event_instance(self, instance: Tag) -> EventData | None:
        # Get date in format: Mon Jan 1 2000
        raw_date = (
            (tag := instance.find(name="div", class_="recap_meta"))
            and (
                date_str := tag.find(
                    string=re_compile(r"(?:[A-Z][a-z]{2} ){2}\d{1,2} \d{4}"),
                )
            )
            and date_str.strip()
        )

        if not isinstance(raw_date, str):
            target = "date"
            raise ScraperParseError(target)

        # Format date into datetime object
        formatted_date = date.strptime(raw_date, "%a %b %d %Y")

        logger.debug(
            "Scraping data for %s",
            formatted_date.strftime("%Y-%m-%d"),
        )

        # If this event's data is already in the db, return
        if self.break_flag and formatted_date <= self.break_flag:
            logger.info(
                "Stopping scrape at %s, already in database.",
                formatted_date.strftime("%Y-%m-%d"),
            )
            self.done_scraping = True
            return None

        # Get game type
        game_type = (
            tag := instance.select_one("h1:nth-child(1) > a:nth-child(1)")
        ) and tag.get_text(strip=True).removesuffix(" RECAP")

        if not isinstance(game_type, str):
            target = "game type"
            raise ScraperParseError(target)

        # Normalize game type string to official naming conventions
        match game_type:
            case "QUIZ":
                game_type = "PUB QUIZ"
            case "BINGO":
                game_type = "MUSIC BINGO"

        # Get quizmaster name
        qm = (
            (tag := instance.find(name="div", class_="recap_meta"))
            and (qm_str := tag.find(string=re_compile(r"by Quizmaster")))
            and (qm_str := qm_str.removeprefix("by Quizmaster ").strip())
            and qm_str.removesuffix(" |")
        )

        if not isinstance(qm, str):
            target = "quizmaster"
            raise ScraperParseError(target)

        # Get description via short-circuiting of and operator:
        #
        # If the element is found, assign it to desc_element,
        # call get_text on it, and assign it to description.
        #
        # If the element is not found, desc_element will be
        # None, and "" will be assigned to description.
        description = (
            (desc_element := instance.select_one(":scope > p:not(:empty)"))
            and desc_element.get_text(separator="\n\n", strip=True)
        ) or ""

        # This will probably never evaluate true,
        # and really just serves as type narrowing
        if not isinstance(description, str):
            target = "description"
            raise ScraperParseError(target)

        # Extracts team data from the recap table for each event instance.
        # For each row in the table, creates a TeamData object with:
        #   - team_id: int from the second column (if present), else None
        #   - name: string from the third column
        #   - score: int from the fourth column
        # Will raise an exception if name or score cannot be properly extracted.
        teams = [
            TeamData(
                team_id=(
                    int(cast("Tag", team_id_element).get_text(strip=True))
                    if (
                        team_id_element := team.select_one(
                            "td:nth-child(2):not(:empty)",
                        )
                    )
                    else None
                ),
                name=cast("Tag", team.select_one("td:nth-child(3)")).get_text(
                    strip=True,
                ),
                score=int(
                    cast("Tag", team.select_one("td:nth-child(4)")).get_text(
                        strip=True,
                    ),
                ),
            )
            for team in instance.select(".recap_table > tbody > tr")
        ]

        # Append data from event instance to event_data
        return EventData(
            date=formatted_date,
            game_type=game_type,
            quizmaster=qm,
            description=description,
            teams=teams,
        )

    def _extract_data(
        self,
        soup: BeautifulSoup,
        event_data: list[EventData] | None = None,
    ) -> list[EventData]:
        if event_data is None:
            event_data = []

        # Check if page has no event instances
        if not soup.find(name="div", class_="venue_recap"):
            logger.debug("No event instances found on this page; stopping scrape.")
            self.done_scraping = True
            return event_data

        # Parse each event on page (usually 3)
        for instance in soup.find_all(name="div", class_="venue_recap"):
            parsed_data = self._parse_event_instance(instance)

            if parsed_data is None:
                break

            event_data.append(parsed_data)

        return event_data

    def scrape(
        self,
    ) -> PageData:
        # Create a requests session for the scraping process
        session = Session()

        # Get rid of the default User-Agent header
        session.headers.pop("User-Agent", None)

        page_data = PageData(
            venue_data=self._extract_venue_data(
                self._fetch_page(self.base_url, session),
            ),
            event_data=[],
        )

        page_counter = 0
        while True:
            page_counter += 1
            page_data.event_data = self._extract_data(
                self._fetch_page(
                    self.base_url + "?pg=" + str(page_counter)
                    if page_counter > 1
                    else self.base_url,
                    session,
                ),
                page_data.event_data,
            )
            logger.info(
                "Scraped page %s with %s total events",
                page_counter,
                len(page_data.event_data),
            )
            if self.done_scraping:
                break

        return page_data

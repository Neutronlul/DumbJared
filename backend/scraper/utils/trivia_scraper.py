from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from re import compile
from datetime import date, time
from calendar import day_name
from requests import Session


class TriviaScraper(BaseScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.done_scraping = False

    def _extract_venue_data(
        self, soup: BeautifulSoup
    ) -> dict[str, str | list[dict[str, str | int | time]]]:
        # Check if the page even fits the expected format
        if not soup.select_one(".game_times > li > div:nth-child(1) > b:nth-child(1)"):
            raise Exception("Unexpected page data. Are you sure the URL is correct?")

        # Get venue name
        venue_name = (
            venue_name_element := soup.select_one(".venue_address > h3:nth-child(1)")
        ) and venue_name_element.get_text(strip=True)

        if not isinstance(venue_name, str):
            raise Exception("Failed to extract venue name from page.")

        # Get event types and their times
        # Expected format: GAME TYPE—Mondays @ 1:00pm
        # Extracts:
        # type: str: "GAME TYPE"
        # day: int: 0
        # time: datetime.time(): 13:00
        games = [
            {
                "type": (game_parsed := game.get_text(strip=True)).split("—")[0],
                "day": list(day_name).index(game_parsed.split("—")[1].split("s @")[0]),
                "time": time.strptime(game_parsed.split("@ ")[1].upper(), "%I:%M%p"),
            }
            for game in soup.select(
                ".game_times > li > div:nth-child(1) > b:nth-child(1)"
            )
        ]

        return {
            "name": venue_name,
            "games": games,
        }

    def _extract_data(
        self, soup: BeautifulSoup, event_data=None
    ) -> list[dict[str, date | str | None | list[dict[str, int | None | str]]]]:
        if event_data is None:
            event_data = []

        # Check if page has no event instances
        if not soup.find(name="div", class_="venue_recap"):
            print("No event instances found on this page; stopping scrape.")
            self.done_scraping = True
            return event_data

        # Parse each event on page (usually 3)
        for instance in soup.find_all(name="div", class_="venue_recap"):
            # Get date in format: Mon Jan 1 2000
            raw_date = (
                (tag := instance.find(name="div", class_="recap_meta"))
                and (
                    date_str := tag.find(
                        string=compile(r"(?:[A-Z][a-z]{2} ){2}\d{1,2} \d{4}")
                    )
                )
                and date_str.strip()
            )

            if not isinstance(raw_date, str):
                raise Exception("Failed to extract date from event instance.")

            # Format date into datetime object
            formatted_date = date.strptime(raw_date, "%a %b %d %Y")

            print(f"Scraping data for {formatted_date.strftime('%Y-%m-%d')}")

            # If this event's data is already in the db, return
            if self.break_flag and formatted_date <= self.break_flag:
                print(
                    f"Stopping scrape at {formatted_date.strftime('%Y-%m-%d')}, already in database."
                )
                self.done_scraping = True
                break

            # Get game type
            game_type = (
                tag := instance.select_one("h1:nth-child(1) > a:nth-child(1)")
            ) and tag.get_text(strip=True).removesuffix(" RECAP")

            if not isinstance(game_type, str):
                raise Exception("Failed to extract game type from event instance.")

            # Normalize game type string to official naming conventions
            match game_type:
                case "QUIZ":
                    game_type = "PUB QUIZ"
                case "BINGO":
                    game_type = "MUSIC BINGO"

            # Get quizmaster name
            qm = (
                (tag := instance.find(name="div", class_="recap_meta"))
                and (qm_str := tag.find(string=compile(r"by Quizmaster")))
                and qm_str.removeprefix("by Quizmaster ").strip()
            )

            if not isinstance(qm, str):
                raise Exception("Failed to extract quizmaster from event instance.")

            # Get description via short-circuiting of and operator:
            # If the element is found, assign it to desc_element, call get_text on it, and assign it to description.
            # If the element is not found, desc_element will be None, and will be assigned to description.
            description = (
                desc_element := instance.select_one(":scope > p:not(:empty)")
            ) and desc_element.get_text(separator="\n\n", strip=True)

            if description is not None and not isinstance(description, str):
                raise Exception("Failed to extract description from event instance.")

            # Extracts team data from the recap table for each event instance.
            # For each row in the table, creates a dictionary with:
            #   - team_id: int from the second column (if present), else None
            #   - name: string from the third column
            #   - score: int from the fourth column
            teams = [
                {
                    "team_id": (
                        team_id_element := team.select_one(
                            "td:nth-child(2):not(:empty)"
                        )
                    )
                    and int(team_id_element.get_text(strip=True)),
                    "name": (tag := team.select_one("td:nth-child(3)"))
                    and tag.get_text(strip=True),
                    "score": (
                        (tag := team.select_one("td:nth-child(4)"))
                        and int(tag.get_text(strip=True))
                    ),
                }
                for team in instance.select(".recap_table > tbody > tr")
            ]

            # Append data from event instance to event_data
            event_data.append(
                {
                    "date": formatted_date,
                    "game_type": game_type,
                    "quizmaster": qm,
                    "description": description,
                    "teams": teams,
                }
            )

        return event_data

    def scrape(
        self,
    ) -> dict[
        str,
        dict[str, str | list[dict[str, str | int | time]]]
        | list[dict[str, date | str | list[dict[str, int | str | None]] | None]],
    ]:
        # Create a requests session for the scraping process
        session = Session()

        # Get rid of the default User-Agent header TODO: Is there a way to just not set it in the first place?
        session.headers.pop("User-Agent", None)

        page_data = {
            "venue_data": self._extract_venue_data(
                self._fetch_page(self.base_url, session)
            ),
            "event_data": [],
        }

        page_counter = 0
        while True:
            page_counter += 1
            page_data["event_data"] = self._extract_data(
                self._fetch_page(
                    self.base_url + "?pg=" + str(page_counter)
                    if page_counter > 1
                    else self.base_url,
                    session,
                ),
                page_data["event_data"],
            )
            print(
                f"Scraped page {page_counter} with {len(page_data['event_data'])} total events"
            )
            if self.done_scraping:
                break

        return page_data

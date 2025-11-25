from .base_scraper import BaseScraper
import re
from datetime import datetime
import calendar
import requests


class TriviaScraper(BaseScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.done_scraping = False

    def _extract_venue_data(self, soup):
        # Check if the page even fits the expected format
        if not soup.select_one(".game_times > li > div:nth-child(1) > b:nth-child(1)"):
            raise Exception("Unexpected page data. Are you sure the URL is correct?")

        # Get venue name
        venueName = soup.select_one(".venue_address > h3:nth-child(1)").get_text(
            strip=True
        )

        # Get event types and their times
        # Expected format: GAME TYPE—Mondays @ 1:00pm
        # Extracts:
        # type: str: "GAME TYPE"
        # day: int: 0
        # time: datetime.time(): 13:00
        games = [
            {
                "type": (game_parsed := game.get_text(strip=True)).split("—")[0],
                "day": list(calendar.day_name).index(
                    game_parsed.split("—")[1].split("s @")[0]
                ),
                "time": datetime.strptime(
                    game_parsed.split("@ ")[1].upper(), "%I:%M%p"
                ).time(),
            }
            for game in soup.select(
                ".game_times > li > div:nth-child(1) > b:nth-child(1)"
            )
        ]

        return {
            "name": venueName,
            "games": games,
        }

    def _extract_data(self, soup, event_data=None):
        if event_data is None:
            event_data = []

        # Check if page has no event instances
        if not soup.find("div", class_="venue_recap"):
            print("No event instances found on this page; stopping scrape.")
            self.done_scraping = True
            return event_data

        # Parse each event on page (usually 3)
        for instance in soup.find_all("div", class_="venue_recap"):
            # Get date in format: Mon Jan 1 2000
            rawDate = (
                instance.find("div", class_="recap_meta")
                .find(string=re.compile(r"(?:[A-Z][a-z]{2} ){2}\d{1,2} \d{4}"))
                .strip()
            )

            # Format date into datetime object
            formatted_date = datetime.strptime(rawDate, "%a %b %d %Y")

            print(f"Scraping data for {formatted_date.strftime('%Y-%m-%d')}")

            # If this event's data is already in the db, return
            if self.break_flag and formatted_date.date() <= self.break_flag:
                print(
                    f"Stopping scrape at {formatted_date.strftime('%Y-%m-%d')}, already in database."
                )
                self.done_scraping = True
                break

            # Get game type
            game_type = (
                instance.select_one("h1:nth-child(1) > a:nth-child(1)")
                .get_text(strip=True)
                .removesuffix(" RECAP")
            )

            # Get quizmaster name
            qm = (
                instance.find("div", class_="recap_meta")
                .find(string=re.compile(r"by Quizmaster"))
                .removeprefix("by Quizmaster ")
                .strip()
            )

            # Get description via short-circuiting of and operator:
            # If the element is found, assign it to desc_element, call get_text on it, and assign it to description.
            # If the element is not found, desc_element will be None, and will be assigned to description.
            description = (
                desc_element := instance.select_one(":scope > p:not(:empty)")
            ) and desc_element.get_text("\n\n", strip=True)

            # Clean up
            del desc_element

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
                    "name": team.select_one("td:nth-child(3)").get_text(strip=True),
                    "score": int(
                        team.select_one("td:nth-child(4)").get_text(strip=True)
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

    def scrape(self):
        # Create a requests session for the scraping process
        session = requests.Session()

        # Get rid of the default User-Agent header
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
                f"Scraped page {page_counter} with {len(page_data['event_data'])} total weeks"
            )
            if self.done_scraping:
                break

        return page_data

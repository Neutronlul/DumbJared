import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.core.cache import cache
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright
from requests import Session

from scraper.exceptions import (
    ScraperCacheError,
    ScraperFetchError,
    ScraperPlaywrightError,
)

logger = logging.getLogger(__name__)


ACCEPTED = 202
SESSION = Session()


class BaseScraper[BreakFlag](ABC):
    def __init__(self, base_url: str, break_flag: BreakFlag) -> None:
        self.ua = UserAgent()
        self.base_url = base_url
        self.break_flag = break_flag
        self._fetch_page = lru_cache(maxsize=1)(self.__fetch_page)

    def _ensure_headers(self, session: Session) -> None:
        """Ensure session headers are set.

        This should only run once per scraping session, at the start
        And will only generate a new User-Agent if the cache is empty
        """
        if session.headers.get("User-Agent"):
            return

        headers = cache.get_or_set(
            f"header:{urlparse(self.base_url).hostname}",
            {"User-Agent": self.ua.random},
            None,
        )

        if headers:
            session.headers.update(headers)
        else:
            msg = "Unable to get/set headers"
            raise ScraperCacheError(msg)

    def __fetch_page(self, url: str, session: Session = SESSION) -> BeautifulSoup:
        try:
            self._ensure_headers(session)
        except ScraperCacheError:
            raise
        except Exception as e:
            msg = "Unexpected error while getting/setting headers"
            raise ScraperCacheError(msg) from e

        logger.debug("Fetching page: %s", url)

        r = session.get(url)

        if r.ok and r.status_code != ACCEPTED:
            return BeautifulSoup(r.content, "html.parser")

        if r.status_code == ACCEPTED:
            logger.debug("Challenged; using Playwright to fetch token...")

            # This will also update the cache and session headers with the new token
            # The User-Agent will stay the same
            content = self._fetch_page_playwright(url, session)

            return BeautifulSoup(content, "html.parser")

        msg = f"Failed to fetch page: {url} with status code {r.status_code}"
        raise ScraperFetchError(msg)

    def _fetch_page_playwright(self, url: str, session: Session) -> str:
        with sync_playwright() as p:
            browser = None
            context = None
            page = None

            try:
                # Connect to the Playwright container
                browser = p.chromium.connect("ws://playwright:3000/")

                # Create a new browser context with the same User-Agent
                context = browser.new_context(
                    extra_http_headers={
                        "User-Agent": str(session.headers.get("User-Agent")),
                    },
                )

                # Navigate to the URL
                page = context.new_page()
                page.goto(url)

                # Wait for the challenge to pass, then
                # extract the cookies and the page content
                page.wait_for_selector(
                    selector=".game_times > li > div:nth-child(1) > b:nth-child(1)",
                    state="attached",
                )

                cookies = context.cookies()
                content = page.content()

                # Extract the token from the cookies,
                # and update the cache and session headers
                try:
                    token_cookie = next(
                        (c for c in cookies if c.get("name") == "aws-waf-token"),
                        None,
                    )

                    if token_cookie:
                        token = token_cookie.get("value")

                        # Update cache
                        cache.set(
                            f"header:{urlparse(self.base_url).hostname}",
                            {
                                "User-Agent": session.headers.get("User-Agent"),
                                "Cookie": f"aws-waf-token={token}",
                            },
                            290,  # 10 seconds less than the expected cookie expiry time
                        )

                        # Update session headers
                        session.headers.update(
                            {
                                "Cookie": f"aws-waf-token={token}",
                            },
                        )

                        logger.debug("Token retrieved, resuming scraping")

                        return content

                    msg = "Token not found in cookies"
                    raise ScraperPlaywrightError(msg)  # noqa: TRY301

                except Exception as e:
                    msg = "Failed to retrieve token"
                    raise ScraperPlaywrightError(msg) from e
            except Exception as e:
                msg = "Playwright failed"
                raise ScraperPlaywrightError(msg) from e
            finally:
                if page:
                    page.close()
                if context:
                    context.close()
                if browser:
                    browser.close()

    @abstractmethod
    def _extract_data(self, soup: BeautifulSoup) -> object:
        pass

    @abstractmethod
    def scrape(self) -> object:
        pass

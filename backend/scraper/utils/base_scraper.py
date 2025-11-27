from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from functools import lru_cache
from django.core.cache import cache
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse


class BaseScraper(ABC):
    def __init__(self, base_url: str, break_flag):
        self.ua = UserAgent()
        self.base_url = base_url
        self.break_flag = break_flag

    @lru_cache(maxsize=1)
    def _fetch_page(
        self, url: str, session: requests.Session = requests.Session()
    ) -> BeautifulSoup:
        # This should only run once per scraping session, at the start
        # And will only generate a new User-Agent if the cache is empty
        if not session.headers.get("User-Agent"):
            try:
                headers = cache.get_or_set(
                    f"header:{urlparse(self.base_url).hostname}",
                    {"User-Agent": self.ua.random},
                    None,
                )
                if headers:
                    session.headers.update(headers)
                else:
                    raise Exception("Unable to get/set headers in cache")
            except Exception as e:
                raise Exception(
                    "Failed to set headers. Is the cache responsive?"
                ) from e

        print(f"Fetching page: {url}")

        r = session.get(url)

        if r.ok and r.status_code != 202:
            return BeautifulSoup(r.content, "html.parser")
        elif r.status_code == 202:
            print("Challenged; Using Playwright to fetch token...")

            # This will also update the cache and session headers with the new token
            # The User-Agent will stay the same
            content = self._fetch_page_playwright(url, session)

            return BeautifulSoup(content, "html.parser")
        else:
            raise Exception(
                f"Failed to fetch page: {url} with status code {r.status_code}"
            )

    def _fetch_page_playwright(self, url: str, session: requests.Session) -> str:
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
                        "User-Agent": str(session.headers.get("User-Agent"))
                    }
                )

                # Navigate to the URL
                page = context.new_page()
                page.goto(url)

                # Wait for the challenge to pass, then extract the cookies and the page content
                page.wait_for_selector(
                    selector=".game_times > li > div:nth-child(1) > b:nth-child(1)",
                    state="attached",
                )

                cookies = context.cookies()
                content = page.content()

                # Extract the token from the cookies, and update the cache and session headers
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
                            }
                        )

                        print("Token retrieved, resuming scraping")

                        return content
                    else:
                        raise Exception("Token not found in cookies")
                except Exception as e:
                    raise Exception("Failed to retrieve token") from e
            except Exception as e:
                raise Exception("Playwright failed") from e
            finally:
                if page:
                    page.close()
                if context:
                    context.close()
                if browser:
                    browser.close()

    @abstractmethod
    def _extract_data(self, soup) -> list:
        pass

    @abstractmethod
    def scrape(self) -> dict:
        pass

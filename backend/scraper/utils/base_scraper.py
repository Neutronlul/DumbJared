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
    def _fetchPage(
        self, url: str, session: requests.Session = requests.Session()
    ) -> BeautifulSoup:
        if not session.headers.get("User-Agent"):
            headers = cache.get_or_set(
                f"header:{urlparse(self.base_url).hostname}",
                {"User-Agent": self.ua.random},
                None,
            )
            if headers:
                session.headers.update(headers)
            else:
                raise Exception("Failed to set headers. Is the cache responsive?")
        print(f"Fetching page: {url}")
        r = session.get(url)
        if r.ok and r.status_code != 202:
            return BeautifulSoup(r.content, "html.parser")
        elif r.status_code == 202:
            print("Challenged; Using Playwright to fetch token...")
            with sync_playwright() as p:
                browser = p.chromium.connect("ws://playwright:3000/")
                context = browser.new_context(
                    extra_http_headers={
                        "User-Agent": str(session.headers.get("User-Agent"))
                    }
                )
                page = context.new_page()
                page.goto(url)
                page.wait_for_selector(
                    selector=".game_times > li > div:nth-child(1) > b:nth-child(1)",
                    state="attached",
                )
                cookies = context.cookies()
                token_cookie = next(
                    (c for c in cookies if c.get("name") == "aws-waf-token"), None
                )
                if token_cookie:
                    token = token_cookie.get("value")
                    # update cache
                    cache.set(
                        f"header:{urlparse(self.base_url).hostname}",
                        {
                            "User-Agent": session.headers.get("User-Agent"),
                            "Cookie": f"aws-waf-token={token}",
                        },
                        290,
                    )

                    # update session headers
                    session.headers.update(
                        {
                            "Cookie": f"aws-waf-token={token}",
                        }
                    )
                else:
                    raise Exception("Failed to retrieve token")
                print("Token retrieved, resuming scraping")
                content = page.content()
                browser.close()
                return BeautifulSoup(content, "html.parser")
        else:
            raise Exception(
                f"Failed to fetch page: {url} with status code {r.status_code}"
            )

    @abstractmethod
    def _extractData(self, soup) -> list:
        pass

    @abstractmethod
    def scrape(self) -> dict:
        pass

from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from functools import lru_cache


class BaseScraper(ABC):
    def __init__(self, base_url: str, break_flag):
        self.ua = UserAgent()
        self.base_url = base_url
        self.break_flag = break_flag

    @lru_cache(maxsize=1)
    def _fetchPage(self, url: str):
        print(f"Fetching page: {url}")
        r = requests.get(url, headers={"User-Agent": self.ua.random})
        if r.ok:
            return BeautifulSoup(r.content, "html.parser")
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

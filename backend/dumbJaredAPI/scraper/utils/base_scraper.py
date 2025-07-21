from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class BaseScraper(ABC):
    def __init__(self, base_url: str, break_flag):
        self.ua = UserAgent()
        self.base_url = base_url
        self.break_flag = break_flag

    def fetchPage(self, url: str):
        r = requests.get(url, headers={"User-Agent": self.ua.random})
        if r.ok:
            return BeautifulSoup(r.content, "html.parser")
        else:
            raise Exception(
                f"Failed to fetch page: {url} with status code {r.status_code}"
            )

    @abstractmethod
    def extractData(self, soup) -> dict:
        pass

    @abstractmethod
    def scrape(self) -> dict:
        pass

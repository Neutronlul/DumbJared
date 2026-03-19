class ScraperError(Exception):
    """Base class for all scraper-related exceptions."""


class ScraperFetchError(ScraperError, OSError):
    """Raised when fetching of the page content fails."""


class ScraperParseError(ScraperError):
    """Raised when parsing of the scraped content fails."""

    def __init__(self, target: str, source: str = "event instance") -> None:
        super().__init__(f"Failed to extract {target} from {source}.")


class ScraperUnexpectedPageError(ScraperParseError):
    """Raised when the page structure is not as expected.

    Indicates a possible issue with the URL or page format.
    """

    def __init__(
        self,
        message: str = "Unexpected page data. Are you sure the URL is correct?",
    ) -> None:
        ScraperError.__init__(self, message)


class ScraperPlaywrightError(ScraperFetchError):
    """Raised when an error occurs during Playwright operations."""

    def __init__(self, message: str) -> None:
        super().__init__(f"An error occurred while fetching with Playwright: {message}")


class ScraperCacheError(ScraperError):
    """Raised when there is an issue with the caching mechanism."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Cache error: {message}")


class ScraperInvalidEndDateError(ScraperError, ValueError):
    """Raised when a date string cannot be parsed into a valid date."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ScraperMatchGameError(ScraperError, KeyError):
    """Raised when a game cannot be matched to an event."""

    def __init__(self, game_type: str, day: int) -> None:
        super().__init__(
            f"No matching game found for type '{game_type}' on day {day}. "
            "Expected this game to exist in self.games.",
        )

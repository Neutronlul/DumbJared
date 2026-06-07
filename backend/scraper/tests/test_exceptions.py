from scraper.exceptions import (
    AccountAlreadyExistsError,
    EmailNotRoutedError,
    EmailNotSetError,
    ScraperCacheError,
    ScraperGameNotFoundError,
    ScraperLoginError,
    ScraperPlaywrightError,
    ScraperPostError,
    ScraperUnexpectedResponseError,
)


class TestScraperPlaywrightError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = ScraperPlaywrightError(msg)
        assert str(exc) == f"An error occurred while fetching with Playwright: {msg}"


class TestScraperCacheError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = ScraperCacheError(msg)
        assert str(exc) == f"Cache error: {msg}"


class TestScraperGameNotFoundError:
    def test_message(self) -> None:
        code = "123456"
        exc = ScraperGameNotFoundError(code)
        assert str(exc) == f"No game found for code {code}"


class TestScraperUnexpectedResponseError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = ScraperUnexpectedResponseError(msg)
        assert str(exc) == msg


class TestScraperPostError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = ScraperPostError(msg)
        assert str(exc) == msg


class TestScraperLoginError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = ScraperLoginError(msg)
        assert str(exc) == msg


class TestEmailNotSetError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = EmailNotSetError(msg)
        assert str(exc) == msg

    def test_default_message(self) -> None:
        exc = EmailNotSetError()
        assert str(exc)


class TestEmailNotRoutedError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = EmailNotRoutedError(msg)
        assert str(exc) == msg

    def test_default_message(self) -> None:
        exc = EmailNotRoutedError()
        assert str(exc)


class TestAccountAlreadyExistsError:
    def test_message(self) -> None:
        msg = "Test message"
        exc = AccountAlreadyExistsError(msg)
        assert str(exc) == f"Account with email {msg} already exists, cannot register."

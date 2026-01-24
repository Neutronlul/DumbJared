from datetime import date, timedelta
from datetime import time
from model_bakery import baker
from model_bakery.utils import seq
from scraper.services.scraper_service import ScraperService
import pytest
from scraper.types import PageData, VenueData


pytestmark = pytest.mark.django_db


class TestScraperService:
    class TestScrapeData:
        def test_successful_scrape(self, mocker):
            expected_data = PageData(
                venue_data=VenueData(name="Test Venue", games=[]), event_data=[]
            )

            mock_scraper = mocker.Mock()
            mock_scraper.scrape.return_value = expected_data

            mock_trivia_scraper = mocker.patch(
                "scraper.services.scraper_service.TriviaScraper",
                return_value=mock_scraper,
            )

            mocker.patch(
                "scraper.services.scraper_service.ScraperService._process_end_date",
                return_value=None,
            )

            service = ScraperService()

            result = service.scrape_data(source_url="http://example.com", end_date=None)

            assert result == expected_data
            assert isinstance(result, PageData)

            mock_trivia_scraper.assert_called_once_with(
                base_url="http://example.com", break_flag=None
            )
            mock_scraper.scrape.assert_called_once()

    class TestPushToDB:
        pass

    class TestProcessEndDate:
        def test_date_object(self):
            service = ScraperService()
            service.end_date = date(2001, 9, 11)

            assert service._process_end_date() == date(2001, 9, 11)

        def test_proper_date_string_conversion(self):
            service = ScraperService()
            service.end_date = "2001-09-11"

            assert service._process_end_date() == date(2001, 9, 11)

        def test_none_date_no_event(self):
            service = ScraperService()
            service.end_date = None
            service.source_url = "http://example.com/data"

            assert service._process_end_date() is None

        def test_none_date_with_events(self):
            url = "http://example.com/"
            venue = baker.make("api.Venue", url=url)

            baker.make(
                "api.Event",
                date=seq(date(2001, 9, 11), increment_by=timedelta(days=1)),
                game__venue=venue,
                _quantity=3,
            )

            service = ScraperService()
            service.end_date = None
            service.source_url = url

            assert service._process_end_date() == date(2001, 9, 14)

        def test_valid_date_format(self):
            service = ScraperService()
            service.end_date = "Blah"
            with pytest.raises(ValueError):
                service._process_end_date()

    class TestMatchGameToEvent:
        def test_match_official(self):
            game = baker.make(
                "api.Game",
                day=2,
                time=time(hour=16),
                game_type__name="Official Game",
            )

            service = ScraperService()
            service.games = {("Official Game", 2): game}

            assert (
                service._match_game_to_event(game_type="Official Game", day=2) == game
            )

        def test_match_custom(self):
            game = baker.make("api.Game", game_type__name="Custom Game")

            service = ScraperService()
            service.games = {("Custom Game", None): game}

            assert service._match_game_to_event(game_type="Custom Game", day=3) == game

        def test_no_match(self):
            game = baker.make(
                "api.Game", day=None, time=None, game_type__name="Custom Game"
            )

            service = ScraperService()
            service.games = {("Custom Game", None): game}
            with pytest.raises(KeyError):
                service._match_game_to_event(game_type="Different Game", day=4)

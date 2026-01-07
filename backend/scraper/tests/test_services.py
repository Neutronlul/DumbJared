from datetime import date, timedelta

from model_bakery import baker
from model_bakery.utils import seq

import pytest

from scraper.services.scraper_service import ScraperService

pytestmark = pytest.mark.django_db


class TestScraperService:
    class TestScrapeData:
        pass

    class TestPushToDB:
        pass

    class TestProcessEndDate:
        def test_proper_date_conversion(self):
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
                date=seq(date(2001, 9, 11), increment_by=timedelta(days=1)),  # pyright: ignore[reportArgumentType] TODO: Remove when model_bakery is updated
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
            pass

        def test_match_custom(self):
            game = baker.make("api.Game", game_type__name="Custom Game")

            service = ScraperService()
            service.games = {("Custom Game", None): game}

            event = baker.make("api.Event", game=game)

            assert (
                service._match_game_to_event(
                    game_type=event.game.game_type.name, day=event.date.day
                )
                == event.game
            )

        def test_no_match(self):
            service = ScraperService()
            service.games = {("OfficialGameType", 1): None}
            with pytest.raises(KeyError):
                service._match_game_to_event(game_type="NonExistentGameType", day=0)

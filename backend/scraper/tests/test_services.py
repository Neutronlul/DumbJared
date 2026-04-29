from datetime import date, time, timedelta
from typing import TYPE_CHECKING

import pytest
from model_bakery import baker
from model_bakery.utils import seq

from api.models import TeamEventParticipation
from scraper.exceptions import ScraperInvalidEndDateError
from scraper.services.scraper_service import ScraperService
from scraper.types import EventData, PageData, TeamData, VenueData

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

pytestmark = pytest.mark.django_db


class TestScraperService:
    class TestScrapeData:
        def test_successful_scrape(self, mocker: MockerFixture) -> None:
            expected_data = PageData(
                venue_data=VenueData(name="Test Venue", games=[]),
                event_data=[],
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
                base_url="http://example.com",
                break_flag=None,
            )
            mock_scraper.scrape.assert_called_once()

        def test_failed_scrape(self, mocker: MockerFixture) -> None:
            mock_scraper = mocker.Mock()
            mock_scraper.scrape.side_effect = Exception("Scrape failed")

            mock_trivia_scraper = mocker.patch(
                "scraper.services.scraper_service.TriviaScraper",
                return_value=mock_scraper,
            )

            mocker.patch(
                "scraper.services.scraper_service.ScraperService._process_end_date",
                return_value=None,
            )

            with pytest.raises(Exception, match="Scrape failed"):
                ScraperService().scrape_data(
                    source_url="http://example.com",
                    end_date=None,
                )

            mock_trivia_scraper.assert_called_once_with(
                base_url="http://example.com",
                break_flag=None,
            )
            mock_scraper.scrape.assert_called_once()

    class TestPushToDB:
        pass

    class TestProcessTeamEventParticipations:
        def test_drops_lower_score_on_duplicate(self) -> None:
            """Test duplicate team attendances.

            If a team shows up more than once for the same event, the one
            with the lower score is dropped.
            """
            lower_score = 50
            higher_score = 70

            event = baker.make("api.Event")
            event_data = [
                EventData(
                    date=event.date,
                    game_type=event.game.game_type.name,
                    quizmaster="Test Quizmaster",
                    description="",
                    teams=[
                        TeamData(team_id=None, name="Team A", score=lower_score),
                        TeamData(team_id=None, name="Team A", score=higher_score),
                    ],
                ),
            ]
            events = {(event.game_id, event.date): event.pk}
            guest_team_1 = baker.make("api.Team", team_id=None)
            guest_team_name_1 = baker.make(
                "api.TeamName",
                team=guest_team_1,
                name="Team A",
                guest=True,
            )
            teams = {}
            guest_teams = {guest_team_name_1.name: guest_team_1.pk}

            service = ScraperService()
            service.games = {(event.game.game_type.name, event.game.day): event.game}

            service._process_team_event_participations(
                event_data=event_data,
                events=events,
                teams=teams,
                guest_teams=guest_teams,
            )

            assert TeamEventParticipation.objects.count() == 1
            assert TeamEventParticipation.objects.get().score == higher_score

        def test_associates_correct_team_name_variant(self) -> None:
            """Test team name variant association.

            The specific name variant used in the event data is tied to the
            participation record.
            """
            team = baker.make("api.Team", team_id=123)
            name1 = baker.make("api.TeamName", team=team, name="Name 1", guest=False)
            _name2 = baker.make("api.TeamName", team=team, name="Name 2", guest=False)

            event = baker.make("api.Event")
            event_data = [
                EventData(
                    date=event.date,
                    game_type=event.game.game_type.name,
                    quizmaster="Test Quizmaster",
                    description="",
                    teams=[TeamData(team_id=123, name="Name 1", score=10)],
                ),
            ]
            events = {(event.game_id, event.date): event.pk}
            teams = {123: team.pk}
            guest_teams = {}

            service = ScraperService()
            service.games = {(event.game.game_type.name, event.game.day): event.game}

            service._process_team_event_participations(
                event_data=event_data,
                events=events,
                teams=teams,
                guest_teams=guest_teams,
            )

            tep = TeamEventParticipation.objects.get()
            assert tep.team_name == name1

    class TestProcessEndDate:
        def test_date_object(self) -> None:
            service = ScraperService()
            service.end_date = date(2001, 9, 11)

            assert service._process_end_date() == date(2001, 9, 11)

        def test_proper_date_string_conversion(self) -> None:
            service = ScraperService()
            service.end_date = "2001-09-11"

            assert service._process_end_date() == date(2001, 9, 11)

        def test_none_date_no_event(self) -> None:
            service = ScraperService()
            service.end_date = None
            service.source_url = "http://example.com/data"

            assert service._process_end_date() is None

        def test_none_date_with_events(self) -> None:
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

        def test_valid_date_format(self) -> None:
            service = ScraperService()
            service.end_date = "Blah"
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_invalid_type_integer(self) -> None:
            """Test that passing an integer raises ScraperInvalidEndDateError."""
            service = ScraperService()
            service.end_date = 12345  # ty:ignore[invalid-assignment]
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"end_date must be a date object, string, or None.",
            ):
                service._process_end_date()

        def test_invalid_type_list(self) -> None:
            """Test that passing a list raises ScraperInvalidEndDateError."""
            service = ScraperService()
            service.end_date = ["2001-09-11"]  # ty:ignore[invalid-assignment]
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"end_date must be a date object, string, or None.",
            ):
                service._process_end_date()

        def test_invalid_type_dict(self) -> None:
            """Test that passing a dict raises ScraperInvalidEndDateError."""
            service = ScraperService()
            service.end_date = {"date": "2001-09-11"}  # ty:ignore[invalid-assignment]
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"end_date must be a date object, string, or None.",
            ):
                service._process_end_date()

        def test_empty_string(self) -> None:
            """Test that an empty string raises an error."""
            service = ScraperService()
            service.end_date = ""
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_invalid_month_in_string(self) -> None:
            """Test that a string with invalid month raises an error."""
            service = ScraperService()
            service.end_date = "2001-13-11"
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_invalid_day_in_string(self) -> None:
            """Test that a string with invalid day raises an error."""
            service = ScraperService()
            service.end_date = "2001-09-31"
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_non_iso_format_slash(self) -> None:
            """Test that non-ISO date format (MM/DD/YYYY) raises an error."""
            service = ScraperService()
            service.end_date = "09/11/2001"
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_non_iso_format_unpadded(self) -> None:
            """Test that unpadded ISO format (YYYY-M-DD) raises an error."""
            service = ScraperService()
            service.end_date = "2001-9-11"
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_valid_leap_year_date(self) -> None:
            """Test that a valid leap year date is parsed correctly."""
            service = ScraperService()
            service.end_date = "2000-02-29"

            assert service._process_end_date() == date(2000, 2, 29)

        def test_invalid_leap_year_date(self) -> None:
            """Test that an invalid leap year date (non-leap year) raises an error."""
            service = ScraperService()
            service.end_date = "2001-02-29"
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

        def test_very_old_date(self) -> None:
            """Test that very old dates are parsed correctly."""
            service = ScraperService()
            service.end_date = "1900-01-01"

            assert service._process_end_date() == date(1900, 1, 1)

        def test_far_future_date(self) -> None:
            """Test that far future dates are parsed correctly."""
            service = ScraperService()
            service.end_date = "2100-12-31"

            assert service._process_end_date() == date(2100, 12, 31)

        def test_none_with_mixed_venue_urls(self) -> None:
            """Verify venue URL filtering when end_date is None.

            When end_date is None, only events matching the source_url's venue
            are queried from the database.
            """
            target_url = "http://example.com/"
            other_url = "http://other.com/"

            target_venue = baker.make("api.Venue", url=target_url)
            other_venue = baker.make("api.Venue", url=other_url)

            # Create one event for the target venue
            baker.make(
                "api.Event",
                date=date(2001, 9, 11),
                game__venue=target_venue,
            )

            # Create one event for a different venue (should not be considered)
            baker.make(
                "api.Event",
                date=date(2020, 1, 1),
                game__venue=other_venue,
            )

            service = ScraperService()
            service.end_date = None
            service.source_url = target_url

            # Should return the date from the target venue only, ignoring
            # the other venue
            assert service._process_end_date() == date(2001, 9, 11)

        def test_whitespace_in_date_string(self) -> None:
            """Test that date strings with whitespace raise an error."""
            service = ScraperService()
            service.end_date = " 2001-09-11 "
            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                service._process_end_date()

    class TestMatchGameToEvent:
        def test_match_official(self) -> None:
            game = baker.make(
                "api.Game",
                day=2,
                time=time(hour=16),
                game_type__name="Official Game",
            )

            service = ScraperService()
            service.games = {("Official Game", game.day): game}

            assert (
                service._match_game_to_event(game_type="Official Game", day=2) == game
            )

        def test_match_custom(self) -> None:
            game = baker.make("api.Game", game_type__name="Custom Game")

            service = ScraperService()
            service.games = {("Custom Game", game.day): game}

            assert service._match_game_to_event(game_type="Custom Game", day=3) == game

        def test_no_match(self) -> None:
            game = baker.make(
                "api.Game",
                day=None,
                time=None,
                game_type__name="Custom Game",
            )

            service = ScraperService()
            service.games = {("Custom Game", game.day): game}
            with pytest.raises(KeyError):
                service._match_game_to_event(game_type="Different Game", day=4)

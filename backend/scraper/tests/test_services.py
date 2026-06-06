from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from model_bakery import baker
from model_bakery.utils import seq

from api.models import TeamEventParticipation, Venue
from scraper.exceptions import ScraperInvalidEndDateError
from scraper.models import GeocodedAddress
from scraper.services.scraper_service import ScraperService
from scraper.types import EventData, PageData, TeamData, VenueData

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_django import DjangoAssertNumQueries
    from pytest_mock import MockerFixture


class TestScraperService:
    @pytest.fixture
    def scraper_service(self) -> ScraperService:
        return ScraperService()

    class TestScrapeData:
        def test_successful_scrape(
            self,
            mocker: MockerFixture,
            scraper_service: ScraperService,
        ) -> None:
            expected_data = PageData(
                venue_data=VenueData(
                    name="Test Venue",
                    address="708 Northwestern Street, Twin Peaks, WA 99153",
                    games=[],
                ),
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

            result = scraper_service.scrape_data(
                source_url="http://example.com",
                end_date=None,
            )

            assert result == expected_data
            assert isinstance(result, PageData)

            mock_trivia_scraper.assert_called_once_with(
                base_url="http://example.com",
                break_flag=None,
            )
            mock_scraper.scrape.assert_called_once()

        def test_failed_scrape(
            self,
            mocker: MockerFixture,
            scraper_service: ScraperService,
        ) -> None:
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
                scraper_service.scrape_data(
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
        @pytest.mark.django_db
        def test_drops_lower_score_on_duplicate(
            self,
            scraper_service: ScraperService,
        ) -> None:
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

            scraper_service.games = {
                (event.game.game_type.name, event.game.day): event.game,
            }

            scraper_service._process_team_event_participations(
                event_data=event_data,
                events=events,
                teams=teams,
                guest_teams=guest_teams,
            )

            assert TeamEventParticipation.objects.count() == 1
            assert TeamEventParticipation.objects.get().score == higher_score

        @pytest.mark.django_db
        def test_associates_correct_team_name_variant(
            self,
            scraper_service: ScraperService,
        ) -> None:
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

            scraper_service.games = {
                (event.game.game_type.name, event.game.day): event.game,
            }

            scraper_service._process_team_event_participations(
                event_data=event_data,
                events=events,
                teams=teams,
                guest_teams=guest_teams,
            )

            tep = TeamEventParticipation.objects.get()
            assert tep.team_name == name1

    class TestProcessEndDate:
        @pytest.mark.parametrize(
            ("input_date", "expected"),
            [
                pytest.param(
                    "2001-09-11",
                    date(2001, 9, 11),
                    id="valid string",
                ),
                pytest.param(
                    date(2001, 9, 11),
                    date(2001, 9, 11),
                    id="date object",
                ),
                pytest.param(
                    "2000-02-29",
                    date(2000, 2, 29),
                    id="leap year date",
                ),
                pytest.param(
                    "1900-01-01",
                    date(1900, 1, 1),
                    id="very old date",
                ),
                pytest.param(
                    "2100-12-31",
                    date(2100, 12, 31),
                    id="far future date",
                ),
            ],
        )
        def test_valid_date_input(
            self,
            input_date: str | date,
            expected: date,
            scraper_service: ScraperService,
        ) -> None:
            scraper_service.end_date = input_date

            assert scraper_service._process_end_date() == expected

        @pytest.mark.parametrize(
            "input_date",
            [
                pytest.param("blah", id="non-date string"),
                pytest.param("", id="empty string"),
                pytest.param("2001-13-11", id="invalid month"),
                pytest.param("2001-09-31", id="invalid day"),
                pytest.param("2001/09/11", id="non-ISO format with slashes"),
                pytest.param("2001-9-11", id="non-ISO format with unpadded month"),
                pytest.param("2001-02-29", id="invalid leap year date"),
                pytest.param(" 2001-09-11 ", id="whitespace around valid date string"),
            ],
        )
        def test_invalid_string_date_input(
            self,
            input_date: str,
            scraper_service: ScraperService,
        ) -> None:
            scraper_service.end_date = input_date

            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"Invalid date format. Please use YYYY-MM-DD.",
            ):
                scraper_service._process_end_date()

        @pytest.mark.parametrize(
            "input_date",
            [
                pytest.param(12345, id="integer"),
                pytest.param(["2001-09-11"], id="list"),
                pytest.param({"date": "2001-09-11"}, id="dict"),
            ],
        )
        def test_invalid_date_input_type(
            self,
            input_date: int | list | dict,
            scraper_service: ScraperService,
        ) -> None:
            scraper_service.end_date = input_date  # ty:ignore[invalid-assignment]

            with pytest.raises(
                ScraperInvalidEndDateError,
                match=r"end_date must be a date object, string, or None.",
            ):
                scraper_service._process_end_date()

        @pytest.mark.django_db
        def test_none_date_no_event(self, scraper_service: ScraperService) -> None:
            scraper_service.end_date = None
            scraper_service.source_url = "http://example.com/data"

            assert scraper_service._process_end_date() is None

        @pytest.mark.django_db
        def test_none_date_with_events(self, scraper_service: ScraperService) -> None:
            url = "http://example.com/"
            venue = baker.make("api.Venue", url=url)

            baker.make(
                "api.Event",
                date=seq(date(2001, 9, 11), increment_by=timedelta(days=1)),
                game__venue=venue,
                _quantity=3,
            )

            scraper_service.end_date = None
            scraper_service.source_url = url

            assert scraper_service._process_end_date() == date(2001, 9, 14)

        @pytest.mark.django_db
        def test_none_with_mixed_venue_urls(
            self,
            scraper_service: ScraperService,
        ) -> None:
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

            scraper_service.end_date = None
            scraper_service.source_url = target_url

            # Should return the date from the target venue only, ignoring
            # the other venue
            assert scraper_service._process_end_date() == date(2001, 9, 11)

    class TestMatchGameToEvent:
        @pytest.mark.django_db
        def test_match_official(self, scraper_service: ScraperService) -> None:
            game = baker.make(
                "api.Game",
                day=2,
                time=time(hour=16),
                game_type__name="Official Game",
            )

            scraper_service.games = {("Official Game", game.day): game}

            assert (
                scraper_service._match_game_to_event(game_type="Official Game", day=2)
                == game
            )

        @pytest.mark.django_db
        def test_match_custom(self, scraper_service: ScraperService) -> None:
            game = baker.make("api.Game", game_type__name="Custom Game")

            scraper_service.games = {("Custom Game", game.day): game}

            assert (
                scraper_service._match_game_to_event(game_type="Custom Game", day=3)
                == game
            )

        @pytest.mark.django_db
        def test_no_match(self, scraper_service: ScraperService) -> None:
            game = baker.make(
                "api.Game",
                day=None,
                time=None,
                game_type__name="Custom Game",
            )

            scraper_service.games = {("Custom Game", game.day): game}
            with pytest.raises(KeyError):
                scraper_service._match_game_to_event(game_type="Different Game", day=4)

    class TestCreateOrUpdateVenue:
        @pytest.fixture
        def mock_now(self, mocker: MockerFixture) -> MagicMock:
            return mocker.patch(
                "scraper.services.scraper_service.timezone.now",
                return_value=datetime(
                    2001,
                    9,
                    11,
                    9,
                    3,
                    tzinfo=ZoneInfo("America/New_York"),
                ),
            )

        @pytest.fixture
        def mock_geocode_address(self, mocker: MockerFixture) -> MagicMock:
            return mocker.patch(
                "scraper.services.scraper_service.geocode_address",
                return_value=baker.make_recipe("scraper.tests.geocoded_address"),
            )

        @pytest.mark.django_db
        def test_create_new_venue(
            self,
            mock_now: MagicMock,
            scraper_service: ScraperService,
            mock_geocode_address: MagicMock,
            django_assert_num_queries: DjangoAssertNumQueries,
        ) -> None:
            venue_name = "Test Venue"
            venue_url = "http://example.com/"
            venue_address = "708 Northwestern Street, Twin Peaks, WA 99153"

            scraper_service.source_url = venue_url

            with django_assert_num_queries(4):
                result = scraper_service._create_or_update_venue(
                    venue_name=venue_name,
                    venue_address=venue_address,
                )

            assert result.name == venue_name
            assert result.url == venue_url
            assert result.address.pk == mock_geocode_address.return_value.pk
            assert result.last_scraped_at == mock_now.return_value

            mock_geocode_address.assert_called_once_with(venue_address)
            assert Venue.objects.count() == 1

        @pytest.mark.django_db
        def test_update_existing_venue(
            self,
            mock_now: MagicMock,
            scraper_service: ScraperService,
            mock_geocode_address: MagicMock,
            django_assert_num_queries: DjangoAssertNumQueries,
        ) -> None:
            old_name = "Old Venue Name"
            venue_url = "http://example.com/"
            old_address = baker.make(
                "scraper.GeocodedAddress",
                address="Old Address",
                longitude=0,
                latitude=0,
            )
            old_scrape_time = datetime(2000, 9, 11, tzinfo=ZoneInfo("America/New_York"))

            new_name = "New Venue Name"
            new_address = "708 Northwestern Street, Twin Peaks, WA 99153"

            baker.make(
                "api.Venue",
                name=old_name,
                url=venue_url,
                address=old_address,
                last_scraped_at=old_scrape_time,
            )

            scraper_service.source_url = venue_url

            with django_assert_num_queries(3):
                result = scraper_service._create_or_update_venue(
                    venue_name=new_name,
                    venue_address=new_address,
                )

            assert result.name == new_name
            assert result.url == venue_url
            assert result.address.pk == mock_geocode_address.return_value.pk
            assert result.last_scraped_at == mock_now.return_value

            mock_geocode_address.assert_called_once_with(new_address)
            assert Venue.objects.count() == 1
            assert GeocodedAddress.objects.count() == 2  # noqa: PLR2004

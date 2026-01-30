from api.models import TeamEventParticipation
from datetime import date, timedelta
from datetime import time
from model_bakery import baker
from model_bakery.utils import seq
from scraper.services.scraper_service import ScraperService
import pytest
from scraper.types import PageData, VenueData, EventData, TeamData


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

    class TestProcessTeamEventParticipations:
        def test_drops_lower_score_on_duplicate(self):
            """
            Test that if a team shows up more than once for the
            same event, the one with the lower score is dropped.
            """
            event = baker.make("api.Event")
            event_data = [
                EventData(
                    date=event.date,
                    game_type=event.game.game_type.name,
                    quizmaster="Test Quizmaster",
                    description=None,
                    teams=[
                        TeamData(team_id=None, name="Team A", score=50),
                        TeamData(team_id=None, name="Team A", score=70),
                    ],
                )
            ]
            events = {(event.game_id, event.date): event.pk}
            guest_team_1 = baker.make("api.Team", team_id=None)
            guest_team_name_1 = baker.make(
                "api.TeamName", team=guest_team_1, name="Team A", guest=True
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
            assert TeamEventParticipation.objects.get().score == 70

        def test_associates_correct_team_name_variant(self):
            """
            Test that the specific name variant used in the event data
            is tied to the participation record.
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
                    description=None,
                    teams=[TeamData(team_id=123, name="Name 1", score=10)],
                )
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
            service.games = {("Official Game", game.day): game}

            assert (
                service._match_game_to_event(game_type="Official Game", day=2) == game
            )

        def test_match_custom(self):
            game = baker.make("api.Game", game_type__name="Custom Game")

            service = ScraperService()
            service.games = {("Custom Game", game.day): game}

            assert service._match_game_to_event(game_type="Custom Game", day=3) == game

        def test_no_match(self):
            game = baker.make(
                "api.Game", day=None, time=None, game_type__name="Custom Game"
            )

            service = ScraperService()
            service.games = {("Custom Game", game.day): game}
            with pytest.raises(KeyError):
                service._match_game_to_event(game_type="Different Game", day=4)

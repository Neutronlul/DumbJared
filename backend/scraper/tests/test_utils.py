from datetime import time
from unittest.mock import patch

import pytest
from requests import Session

from scraper.utils import sync_tasks
from scraper.utils.trivia_scraper import TriviaScraper

pytestmark = pytest.mark.django_db

_DEFAULT_REQUESTS_USER_AGENT = Session().headers.get("User-Agent")


class TestBaseScraper:
    class TestCreateSession:
        def test_returns_session_with_custom_user_agent(self):
            scraper = TriviaScraper(
                base_url="https://example.com",
                break_flag=None,
            )
            fake_ua = "FakeAgent/1.0"

            with patch(
                "django.core.cache.cache.get_or_set",
                return_value={"User-Agent": fake_ua},
            ):
                session = scraper._create_session()

            assert isinstance(session, Session)
            assert session.headers.get("User-Agent") == fake_ua

        def test_does_not_use_default_requests_user_agent(self):
            scraper = TriviaScraper(
                base_url="https://example.com",
                break_flag=None,
            )
            fake_ua = "CustomAgent/2.0"

            with patch(
                "django.core.cache.cache.get_or_set",
                return_value={"User-Agent": fake_ua},
            ):
                session = scraper._create_session()

            assert session.headers.get("User-Agent") != _DEFAULT_REQUESTS_USER_AGENT

        def test_raises_on_cache_failure(self):
            scraper = TriviaScraper(
                base_url="https://example.com",
                break_flag=None,
            )
            with patch(
                "django.core.cache.cache.get_or_set",
                side_effect=Exception("cache unavailable"),
            ):
                with pytest.raises(Exception, match="Failed to set headers"):
                    scraper._create_session()

    class TestFetchPage:
        def test_initialization(self):
            pass

    class TestFetchPagePlaywright:
        pass


class TestSyncTasks:
    # class TestSync:
    #     def test_normal_hours(self):
    #         game = baker.make(
    #             "api.Game",
    #             day=2,
    #             time=time(hour=14),  # 2:00 PM
    #             venue__name="Test Venue",  # These are just to avoid PeriodicTask's name length limit
    #             game_type__name="Test Game Type",
    #         )

    #         sync([game])

    #         schedule = CrontabSchedule.objects.first()

    #         assert schedule is not None
    #         assert schedule.hour == "15-16"  # 3 PM to 4 PM
    #         assert schedule.day_of_week == "3"  # Wednesday

    #     def test_offset_hours(self):
    #         game = baker.make(
    #             "api.Game",
    #             day=4,
    #             time=time(hour=9, minute=30),  # 9:30 AM
    #             venue__name="Test Venue",  # These are just to avoid PeriodicTask's name length limit
    #             game_type__name="Test Game Type",
    #         )

    #         sync([game])

    #         schedule = CrontabSchedule.objects.first()

    #         assert schedule is not None
    #         assert schedule.hour == "10-11"  # 10 AM to 11 AM
    #         assert schedule.day_of_week == "5"  # Friday

    #     def test_crontab_unique(self):
    #         game1 = baker.make(
    #             "api.Game",
    #             day=3,
    #             time=time(hour=16),  # 4:00 PM
    #             venue__name="Test Venue 1",  # These are just to avoid PeriodicTask's name length limit
    #             game_type__name="Test Game Type 1",
    #         )
    #         game2 = baker.make(
    #             "api.Game",
    #             day=3,
    #             time=time(hour=16),  # 4:00 PM
    #             venue__name="Test Venue 2",  # These are just to avoid PeriodicTask's name length limit
    #             game_type__name="Test Game Type 2",
    #         )

    #         sync([game1, game2])

    #         schedules = CrontabSchedule.objects.all()

    #         assert schedules.count() == 1

    class TestGenerateCrontabHours:
        def test_normal_hours(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=14, minute=0),  # 2:00 PM
            )
            assert result == "15-16"  # 3 PM to 4 PM

        def test_offset_hours_before_half(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=9, minute=15),  # 9:15 AM
            )
            assert result == "10-11"  # 10 AM to 11 AM

        def test_offset_hours_after_half(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=17, minute=45),  # 5:45 PM
            )
            assert result == "18-20"  # 6 PM to 8 PM

        def test_latest_supported_hour(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=21, minute=15),  # 9:15 PM
            )
            assert result == "22-23"  # 10 PM to 11 PM

        def test_unsupported_hours(self):
            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=21, minute=30),  # 9:30 PM
                )

            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=21, minute=45),  # 9:45 PM
                )

            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=22, minute=0),  # 10:00 PM
                )

            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=23, minute=45),  # 11:45 PM
                )


class TestTriviaScraper:
    class TestExtractVenueData:
        pass

    class TestExtractData:
        pass

    class TestScrape:
        pass

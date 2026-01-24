import pytest
from scraper.utils.base_scraper import BaseScraper
from scraper.utils import sync_tasks
from datetime import time
from model_bakery import baker
from django_celery_beat.models import CrontabSchedule, PeriodicTask


pytestmark = pytest.mark.django_db


class TestBaseScraper:
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
                time(hour=14, minute=0)  # 2:00 PM
            )
            assert result == "15-16"  # 3 PM to 4 PM

        def test_offset_hours_before_half(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=9, minute=15)  # 9:15 AM
            )
            assert result == "10-11"  # 10 AM to 11 AM

        def test_offset_hours_after_half(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=17, minute=45)  # 5:45 PM
            )
            assert result == "18-20"  # 6 PM to 8 PM

        def test_latest_supported_hour(self):
            result = sync_tasks._generate_crontab_hours(
                time(hour=21, minute=15)  # 9:15 PM
            )
            assert result == "22-23"  # 10 PM to 11 PM

        def test_unsupported_hours(self):
            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=21, minute=30)  # 9:30 PM
                )

            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=21, minute=45)  # 9:45 PM
                )

            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=22, minute=0)  # 10:00 PM
                )

            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    time(hour=23, minute=45)  # 11:45 PM
                )


class TestTriviaScraper:
    class TestExtractVenueData:
        pass

    class TestExtractData:
        pass

    class TestScrape:
        pass

from datetime import time

import pytest

from scraper.utils import sync_tasks
from scraper.utils.accounts import AccountManager

pytestmark = pytest.mark.django_db


class TestBaseScraper:
    class TestFetchPage:
        def test_initialization(self) -> None:
            pass

    class TestFetchPagePlaywright:
        pass


class TestSyncTasks:
    class TestSync:
        pass

    class TestGenerateCrontabHours:
        def test_normal_hours(self) -> None:
            result = sync_tasks._generate_crontab_hours(
                time(hour=14, minute=0),  # 2:00 PM
            )
            assert result == "15-16"  # 3 PM to 4 PM

        def test_offset_hours_before_half(self) -> None:
            result = sync_tasks._generate_crontab_hours(
                time(hour=9, minute=15),  # 9:15 AM
            )
            assert result == "10-11"  # 10 AM to 11 AM

        def test_offset_hours_after_half(self) -> None:
            result = sync_tasks._generate_crontab_hours(
                time(hour=17, minute=45),  # 5:45 PM
            )
            assert result == "18-20"  # 6 PM to 8 PM

        def test_latest_supported_hour(self) -> None:
            result = sync_tasks._generate_crontab_hours(
                time(hour=21, minute=15),  # 9:15 PM
            )
            assert result == "22-23"  # 10 PM to 11 PM

        def test_unsupported_hours(self) -> None:
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


class TestAccountManager:
    @pytest.fixture
    def account_manager(self) -> AccountManager:
        return AccountManager(base_url="example.com")

    class TestStripSubaddress:
        @pytest.mark.parametrize(
            ("email", "expected"),
            [
                # no subaddress
                ("test@example.com", "test@example.com"),
                # basic subaddress
                ("test+123@example.com", "test@example.com"),
                # empty subaddress
                ("test+@example.com", "test@example.com"),
                # multiple + signs: only first matters
                ("test+foo+bar@example.com", "test@example.com"),
                # + in domain should not matter
                ("test@example+foo.com", "test@example+foo.com"),
                # preserve case/domain exactly
                ("Test+abc@Example.COM", "Test@Example.COM"),
                # local part starts with +
                ("+foo@example.com", "@example.com"),
                # multiple @ signs after first
                ("test+abc@sub@domain.com", "test@sub@domain.com"),
            ],
            ids=[
                "no_subaddress",
                "basic_subaddress",
                "empty_subaddress",
                "multiple_plus_signs",
                "plus_in_domain",
                "preserve_case_domain",
                "local_part_starts_with_plus",
                "multiple_at_signs",
            ],
        )
        def test_strip_subaddress(
            self,
            account_manager: AccountManager,
            email: str,
            expected: str,
        ) -> None:
            assert account_manager._strip_subaddress(email) == expected

        def test_strip_subaddress_missing_at(
            self,
            account_manager: AccountManager,
        ) -> None:
            with pytest.raises(
                ValueError,
                match="not enough values to unpack",
            ):
                account_manager._strip_subaddress("not-an-email")

        def test_strip_subaddress_idempotent(
            self,
            account_manager: AccountManager,
        ) -> None:
            result = account_manager._strip_subaddress(
                "test+abc@example.com",
            )

            assert account_manager._strip_subaddress(result) == result

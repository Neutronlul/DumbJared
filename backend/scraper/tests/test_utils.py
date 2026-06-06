from calendar import day_name
from datetime import time
from types import SimpleNamespace
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from bs4 import BeautifulSoup
from model_bakery import baker

from scraper.exceptions import ScraperParseError, ScraperUnexpectedPageError
from scraper.models import GeocodedAddress
from scraper.utils import sync_tasks
from scraper.utils.accounts import AccountManager
from scraper.utils.base_url import get_base_url
from scraper.utils.timezone import geocode_address
from scraper.utils.trivia_scraper import TriviaScraper

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_django import DjangoAssertNumQueries
    from pytest_mock import MockerFixture


class TestBaseScraper:
    class TestFetchPage:
        def test_initialization(self) -> None:
            pass

    class TestFetchPagePlaywright:
        pass


@pytest.mark.django_db
class TestBaseURL:
    def test_no_venues(
        self,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with (
            django_assert_num_queries(1),
            pytest.raises(ValueError, match="No venues found in database"),
        ):
            get_base_url()

    def test_single_venue(
        self,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        baker.make("api.Venue", url="https://www.example.com/some/path")

        with django_assert_num_queries(1):
            assert get_base_url() == "example.com"

    def test_multiple_venues_same_host(
        self,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        baker.make("api.Venue", url="https://www.example.com/some/path")
        baker.make("api.Venue", url="http://example.com/other/path")

        with django_assert_num_queries(1):
            assert get_base_url() == "example.com"

    def test_multiple_venues_different_hosts(
        self,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        baker.make("api.Venue", url="https://www.example.com/some/path")
        baker.make("api.Venue", url="http://other.com/other/path")

        with (
            django_assert_num_queries(1),
            pytest.raises(
                ValueError,
                match="Multiple distinct venue hostnames found in database",
            ),
        ):
            get_base_url()


class TestSyncTasks:
    class TestSync:
        pass

    class TestGenerateCrontabHours:
        @pytest.mark.parametrize(
            ("input_time", "expected"),
            [
                pytest.param(
                    time(hour=0, minute=0),
                    "1-2",
                    id="1:00 AM to 2:00 AM",
                ),
                pytest.param(
                    time(hour=6, minute=59),
                    "7-9",
                    id="7:00 AM to 9:00 AM",
                ),
                pytest.param(
                    time(hour=9, minute=15),
                    "10-11",
                    id="10:00 AM to 11:00 AM",
                ),
                pytest.param(
                    time(hour=14, minute=0),
                    "15-16",
                    id="3:00 PM to 4:00 PM",
                ),
                pytest.param(
                    time(hour=17, minute=45),
                    "18-20",
                    id="6:00 PM to 8:00 PM",
                ),
                pytest.param(
                    time(hour=21, minute=15),
                    "22-23",
                    id="10:00 PM to 11:00 PM",
                ),
                pytest.param(
                    time(hour=21, minute=29),
                    "22-23",
                    id="10:00 PM to 11:00 PM (latest supported time)",
                ),
            ],
        )
        def test_normal_hours(self, input_time: time, expected: str) -> None:
            result = sync_tasks._generate_crontab_hours(input_time)
            assert result == expected

        @pytest.mark.parametrize(
            "unsupported_time",
            [
                pytest.param(time(hour=21, minute=30), id="9:30 PM"),
                pytest.param(time(hour=21, minute=45), id="9:45 PM"),
                pytest.param(time(hour=22, minute=0), id="10:00 PM"),
                pytest.param(time(hour=23, minute=45), id="11:45 PM"),
                pytest.param(time(hour=23, minute=59), id="11:59 PM"),
            ],
        )
        def test_unsupported_hours(self, unsupported_time: time) -> None:
            with pytest.raises(NotImplementedError):
                sync_tasks._generate_crontab_hours(
                    unsupported_time,
                )


class TestTriviaScraper:
    class TestExtractVenueData:
        @pytest.fixture(scope="class")
        def make_soup(self) -> Callable[..., BeautifulSoup]:
            def _make_soup(
                name_element: str,
                map_element: str,
                game_type: str,
                game_day: int,
                game_time: time,
            ) -> BeautifulSoup:
                formatted_time = game_time.strftime("%I:%M%p").lstrip("0").lower()
                day_name_str = day_name[game_day]

                return BeautifulSoup(
                    f"""
                        <div class="venue_address">
                            <h3>{name_element}</h3>
                            708 Northwestern Street
                            <br>
                            Twin Peaks WA 99153
                            <br>
                            (900) 860-0911
                            <div class="venue_game_time">
                                <ul class="game_times">
                                    <li><div><b>{game_type}—{day_name_str}s @ {formatted_time}</b></div></li>
                                </ul>
                            </div>
                        </div>

                        <a
                            href="https://maps.google.com/maps?f=q&amp;hl=en&amp;geocode=&amp;q={map_element}"
                            target="_blank"
                        >
                        </a>

                    """,  # noqa: E501
                    "html.parser",
                )

            return _make_soup

        @pytest.fixture(scope="class")
        def scraper(self) -> TriviaScraper:
            return TriviaScraper(base_url="example.com", break_flag=None)

        @pytest.mark.parametrize(
            "name_element",
            [
                pytest.param("Test Venue Name", id="valid venue name"),
                pytest.param("", id="empty venue name"),
                pytest.param(" Test Venue   Name ", id="venue name with whitespace"),
            ],
        )
        @pytest.mark.parametrize(
            "map_element",
            [
                pytest.param(
                    "708+Northwestern+Street+Twin+Peaks+WA+99153",
                    id="northwestern street",
                ),
                pytest.param(
                    "1640+Riverside+Drive+Hill+Valley+CA+94952",
                    id="riverside drive",
                ),
            ],
        )
        @pytest.mark.parametrize(
            "game_type",
            [
                pytest.param("PUB QUIZ", id="pub quiz"),
                pytest.param("MUSIC BINGO", id="music bingo"),
                pytest.param("CUSTOM GAME TYPE", id="custom game type"),
            ],
        )
        @pytest.mark.parametrize(
            "game_day",
            [pytest.param(d, id=day_name[d]) for d in range(7)],
        )
        @pytest.mark.parametrize(
            "game_time",
            [
                pytest.param(time(hour=5), id="5am"),
                pytest.param(time(hour=18), id="6pm"),
            ],
        )
        def test_extract_venue_data(  # noqa: PLR0913
            self,
            scraper: TriviaScraper,
            make_soup: Callable[..., BeautifulSoup],
            name_element: str,
            map_element: str,
            game_type: str,
            game_day: int,
            game_time: time,
        ) -> None:
            soup = make_soup(
                name_element,
                map_element,
                game_type,
                game_day,
                game_time,
            )

            expected_address = map_element.replace("+", " ")

            venue_data = scraper._extract_venue_data(soup)

            assert venue_data.name == name_element.strip()
            assert venue_data.address == expected_address
            assert len(venue_data.games) == 1

            game = venue_data.games[0]
            assert game.type == game_type
            assert game.day == game_day
            assert game.time == game_time

        def test_invalid_page_format(
            self,
            scraper: TriviaScraper,
        ) -> None:
            soup = BeautifulSoup("<div>Invalid page format</div>", "html.parser")

            with pytest.raises(ScraperUnexpectedPageError):
                scraper._extract_venue_data(soup)

        def test_missing_name(
            self,
            scraper: TriviaScraper,
        ) -> None:
            soup = BeautifulSoup(
                """<ul class="game_times"><li><div><b></b></div></li></ul>""",
                "html.parser",
            )

            with pytest.raises(ScraperParseError, match="venue name from page"):
                scraper._extract_venue_data(soup)

        def test_missing_address(
            self,
            scraper: TriviaScraper,
        ) -> None:
            soup = BeautifulSoup(
                """
                    <ul class="game_times"><li><div><b></b></div></li></ul>
                    <div class="venue_address">
                            <h3>Venue Name</h3>
                    </div>
                    """,
                "html.parser",
            )

            with pytest.raises(ScraperParseError, match="address from page"):
                scraper._extract_venue_data(soup)

    class TestExtractData:
        pass

    class TestScrape:
        pass


class TestAccountManager:
    @pytest.fixture
    def account_manager(self, mocker: MockerFixture) -> AccountManager:
        return AccountManager(
            base_url="example.com",
            client_id="test-client-id",
            redis=mocker.Mock(),
        )

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
            email: str,
            expected: str,
        ) -> None:
            assert AccountManager._strip_subaddress(email) == expected

        def test_strip_subaddress_missing_at(
            self,
        ) -> None:
            with pytest.raises(
                ValueError,
                match="Invalid email address: missing '@' symbol",
            ):
                AccountManager._strip_subaddress("not-an-email")

        def test_strip_subaddress_idempotent(
            self,
        ) -> None:
            result = AccountManager._strip_subaddress(
                "test+abc@example.com",
            )

            assert AccountManager._strip_subaddress(result) == result


class TestTimeZone:
    @pytest.fixture
    def block_geocoding(self, mocker: MockerFixture) -> None:
        mocker.patch(
            target="scraper.utils.timezone.Nominatim.geocode",
            side_effect=AssertionError("Geocoding should not be called"),
        )

    @pytest.mark.parametrize(
        "address",
        [
            pytest.param("", id="empty string"),
            pytest.param("   ", id="whitespace only"),
            pytest.param("\n", id="newline only"),
            pytest.param("\t", id="tab only"),
            pytest.param("\r\n", id="crlf only"),
            pytest.param(" \t \n ", id="mixed whitespace"),
        ],
    )
    @pytest.mark.usefixtures("block_geocoding")
    def test_invalid_address(self, address: str) -> None:
        with pytest.raises(ValueError, match="Address cannot be empty"):
            geocode_address(address)

    @pytest.mark.usefixtures("block_geocoding")
    @pytest.mark.django_db
    def test_cached_address(
        self,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        geocoded_address = baker.make_recipe("scraper.tests.geocoded_address")

        with django_assert_num_queries(1):
            result = geocode_address(geocoded_address.address)

        assert result == geocoded_address
        assert GeocodedAddress.objects.count() == 1

    @pytest.mark.django_db
    def test_ungeocodable_address(
        self,
        mocker: MockerFixture,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:

        mock_geocoder = mocker.patch(
            target="scraper.utils.timezone.Nominatim.geocode",
            return_value=None,
        )

        address = "Invalid Address"
        with (
            django_assert_num_queries(1),
            pytest.raises(
                ValueError,
                match=f"Could not geocode address: {address}",
            ),
        ):
            geocode_address(address)

        mock_geocoder.assert_called_once_with(address)

        assert GeocodedAddress.objects.count() == 0

    @pytest.mark.django_db
    def test_bad_timezone(
        self,
        mocker: MockerFixture,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        address = "Some Address"

        mocker.patch("scraper.utils.timezone.get_tz", return_value="")
        mocker.patch(
            target="scraper.utils.timezone.Nominatim.geocode",
            return_value=SimpleNamespace(address=address, longitude=0, latitude=0),
        )

        with (
            django_assert_num_queries(1),
            pytest.raises(
                ValueError,
                match="Could not determine timezone for location",
            ),
        ):
            geocode_address(address)

    @pytest.mark.django_db
    def test_new_valid_address(
        self,
        mocker: MockerFixture,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        address = "633 Stagtrail Rd. N. Caldwell New Jersey"
        timezone = ZoneInfo("America/New_York")
        longitude = -74.24529
        latitude = 40.86800

        mock_geocoder = mocker.patch(
            target="scraper.utils.timezone.Nominatim.geocode",
            return_value=SimpleNamespace(
                longitude=longitude,
                latitude=latitude,
            ),
        )

        mock_get_tz = mocker.patch(
            target="scraper.utils.timezone.get_tz",
            return_value=timezone.key,
        )

        with django_assert_num_queries(5):  # Should be 3 but whatever
            result = geocode_address(address)

        assert result.address == address
        assert result.timezone == timezone
        assert result.longitude == longitude
        assert result.latitude == latitude

        mock_geocoder.assert_called_once_with(address)
        mock_get_tz.assert_called_once_with(longitude, latitude)
        assert GeocodedAddress.objects.count() == 1

    @pytest.mark.django_db
    def test_idempotency(
        self,
        mocker: MockerFixture,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        address = "633 Stagtrail Rd. N. Caldwell New Jersey"
        timezone = ZoneInfo("America/New_York")
        longitude = -74.24529
        latitude = 40.86800

        mock_geocoder = mocker.patch(
            target="scraper.utils.timezone.Nominatim.geocode",
            return_value=SimpleNamespace(
                longitude=longitude,
                latitude=latitude,
            ),
        )

        mock_get_tz = mocker.patch(
            target="scraper.utils.timezone.get_tz",
            return_value=timezone.key,
        )

        with django_assert_num_queries(5):
            result1 = geocode_address(address)

        mock_geocoder.assert_called_once_with(address)
        mock_get_tz.assert_called_once_with(longitude, latitude)

        with django_assert_num_queries(1):
            result2 = geocode_address(address)

        mock_geocoder.assert_called_once_with(address)
        mock_get_tz.assert_called_once_with(longitude, latitude)

        assert result1 == result2
        assert GeocodedAddress.objects.count() == 1

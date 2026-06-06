from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import DataError, IntegrityError
from model_bakery import baker

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from scraper.models import ScraperAccount

pytestmark = pytest.mark.django_db


class TestScraperAccount:
    @pytest.fixture
    def scraper_account(self) -> ScraperAccount:
        return baker.prepare_recipe("scraper.tests.scraper_account")

    @pytest.fixture(scope="class")
    def make_scraper_account(self) -> Callable[..., ScraperAccount]:
        def _make(**kwargs: object) -> ScraperAccount:
            return baker.make_recipe("scraper.tests.scraper_account", **kwargs)

        return _make

    def test_str(self, scraper_account: ScraperAccount) -> None:
        assert str(scraper_account) == scraper_account.name

    def test_str_no_name(self, scraper_account: ScraperAccount) -> None:
        scraper_account.name = ""
        assert str(scraper_account) == scraper_account.email

    @pytest.mark.parametrize(
        "player_id",
        [
            pytest.param("69d49757f4205d88e104a910", id="valid"),
            pytest.param("a" * 24 + " ", id="trailing space"),
            pytest.param("", id="blank"),
            pytest.param("0" * 24, id="all zeros"),
            pytest.param("f" * 24, id="all f"),
        ],
    )
    def test_player_id_valid(
        self,
        make_scraper_account: Callable[..., ScraperAccount],
        player_id: str,
    ) -> None:
        scraper_account = make_scraper_account(player_id=player_id)
        assert scraper_account.player_id == player_id

    @pytest.mark.parametrize(
        ("player_id", "exception"),
        [
            pytest.param("69d49757f", IntegrityError, id="too short"),
            pytest.param("a" * 25, DataError, id="too long"),
            pytest.param("A" * 24, IntegrityError, id="uppercase"),
            pytest.param("m" * 24, IntegrityError, id="non-hex characters"),
            pytest.param(10, IntegrityError, id="non-string type"),
            pytest.param(" " + "6" * 24, DataError, id="leading space"),
        ],
    )
    def test_player_id_invalid(
        self,
        make_scraper_account: Callable[..., ScraperAccount],
        player_id: str | int,
        exception: type[IntegrityError | DataError],
    ) -> None:
        with pytest.raises(exception):
            make_scraper_account(player_id=player_id)

    def test_email_uniqueness(
        self,
        make_scraper_account: Callable[..., ScraperAccount],
    ) -> None:
        make_scraper_account()
        with pytest.raises(IntegrityError):
            make_scraper_account()


class TestGeocodedAddress:
    def test_str(self) -> None:
        geocoded_address = baker.make_recipe("scraper.tests.geocoded_address")

        assert (
            str(geocoded_address)
            == f"{geocoded_address.address} ({geocoded_address.timezone})"
        )

    @pytest.mark.parametrize(
        "address",
        [
            pytest.param(
                "1640 Riverside Drive, Hill Valley CA 94952",
                id="valid address",
            ),
            pytest.param(
                "A",
                id="min length address",
            ),
            pytest.param(
                "A" * 500,
                id="max length address",
            ),
            pytest.param(
                " ",  # It might be stupid to allow this but whatever
                id="whitespace address",
            ),
        ],
    )
    def test_valid_address(
        self,
        address: str,
    ) -> None:
        geocoded_address = baker.make_recipe(
            "scraper.tests.geocoded_address",
            address=address,
        )
        assert geocoded_address.address == address

    @pytest.mark.parametrize(
        ("address", "exception"),
        [
            pytest.param("", IntegrityError, id="blank address"),
            pytest.param("A" * 501, DataError, id="too long address"),
            pytest.param(None, IntegrityError, id="non-string address"),
        ],
    )
    def test_invalid_address(
        self,
        address: str | None,
        exception: type[IntegrityError | DataError],
    ) -> None:
        with pytest.raises(exception):
            baker.make_recipe(
                "scraper.tests.geocoded_address",
                address=address,
            )

    @pytest.mark.parametrize(
        "timezone",
        [
            pytest.param("America/Los_Angeles", id="valid timezone"),
            pytest.param(ZoneInfo("America/Los_Angeles"), id="ZoneInfo timezone"),
            pytest.param("UTC", id="UTC"),
            pytest.param(ZoneInfo("UTC"), id="ZoneInfo UTC"),
            pytest.param("Etc/GMT+5", id="GMT offset timezone"),
        ],
    )
    def test_valid_timezone(
        self,
        timezone: str | ZoneInfo,
    ) -> None:
        geocoded_address = baker.make_recipe(
            "scraper.tests.geocoded_address",
            timezone=timezone,
        )
        assert str(geocoded_address.timezone) == str(timezone)

    @pytest.mark.parametrize(
        ("timezone", "exception"),
        [
            pytest.param("Invalid/Timezone", ValidationError, id="invalid timezone"),
            pytest.param("", IntegrityError, id="blank timezone"),
            pytest.param(None, IntegrityError, id="non-string timezone"),
        ],
    )
    def test_invalid_timezone(
        self,
        timezone: str,
        exception: type[ValidationError],
    ) -> None:
        with pytest.raises(exception):
            baker.make_recipe(
                "scraper.tests.geocoded_address",
                timezone=timezone,
            )

    @pytest.mark.parametrize(
        "longitude",
        [
            pytest.param(0, id="zero longitude"),
            pytest.param(10, id="positive longitude"),
            pytest.param(-10, id="negative longitude"),
            pytest.param(180, id="max longitude"),
            pytest.param(-180, id="min longitude"),
            pytest.param(5.5, id="float longitude"),
            pytest.param(-5.5, id="negative float longitude"),
        ],
    )
    def test_valid_longitude(
        self,
        longitude: float,
    ) -> None:
        geocoded_address = baker.make_recipe(
            "scraper.tests.geocoded_address",
            longitude=longitude,
        )
        assert geocoded_address.longitude == longitude

    @pytest.mark.parametrize(
        "longitude",
        [
            pytest.param(-180.1, id="longitude too low"),
            pytest.param(180.1, id="longitude too high"),
            pytest.param(None, id="non-float longitude"),
        ],
    )
    def test_invalid_longitude(
        self,
        longitude: float,
    ) -> None:
        with pytest.raises(IntegrityError):
            baker.make_recipe(
                "scraper.tests.geocoded_address",
                longitude=longitude,
            )

    @pytest.mark.parametrize(
        "latitude",
        [
            pytest.param(0, id="zero latitude"),
            pytest.param(10, id="positive latitude"),
            pytest.param(-10, id="negative latitude"),
            pytest.param(90, id="max latitude"),
            pytest.param(-90, id="min latitude"),
            pytest.param(5.5, id="float latitude"),
            pytest.param(-5.5, id="negative float latitude"),
        ],
    )
    def test_valid_latitude(
        self,
        latitude: float,
    ) -> None:
        geocoded_address = baker.make(
            "scraper.GeocodedAddress",
            longitude=0,
            latitude=latitude,
        )
        assert geocoded_address.latitude == latitude

    @pytest.mark.parametrize(
        "latitude",
        [
            pytest.param(-90.1, id="latitude too low"),
            pytest.param(90.1, id="latitude too high"),
            pytest.param(None, id="non-float latitude"),
        ],
    )
    def test_invalid_latitude(
        self,
        latitude: float,
    ) -> None:
        with pytest.raises(IntegrityError):
            baker.make_recipe(
                "scraper.tests.geocoded_address",
                latitude=latitude,
            )

    def test_create_from_address(
        self,
        mocker: MockerFixture,
    ) -> None:
        geocoded_address = baker.prepare_recipe("scraper.tests.geocoded_address")

        mock_geocode_address = mocker.patch(
            "scraper.models.geocode_address",
            return_value=geocoded_address,
        )

        result = geocoded_address.create_from_address(geocoded_address.address)

        assert result is geocoded_address

        mock_geocode_address.assert_called_once_with(geocoded_address.address)

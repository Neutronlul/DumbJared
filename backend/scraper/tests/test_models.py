from typing import TYPE_CHECKING

import pytest
from django.db.utils import DataError, IntegrityError
from model_bakery import baker

if TYPE_CHECKING:
    from collections.abc import Callable

    from scraper.models import ScraperAccount

pytestmark = pytest.mark.django_db


class TestScraperAccount:
    @pytest.fixture
    def scraper_account(self) -> ScraperAccount:
        return baker.prepare_recipe("scraper.tests.scraper_account")

    @pytest.fixture
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

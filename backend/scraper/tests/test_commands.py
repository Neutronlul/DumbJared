from io import StringIO
from typing import TYPE_CHECKING

import pytest
from django.core.management import call_command

from scraper.types import PageData, VenueData

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestJoinGame:
    pass


class TestPollGame:
    pass


class TestScrapeData:
    @pytest.fixture(scope="class")
    @classmethod
    def page_data(cls) -> PageData:
        return PageData(
            venue_data=VenueData(
                name="Test Venue",
                address="123 Test St",
                games=[],
            ),
            event_data=[],
        )

    @pytest.mark.parametrize(
        "end_date",
        [
            pytest.param(None, id="no end date"),
            pytest.param("2001-09-11", id="with end date"),
        ],
    )
    def test_scrape_data_command(
        self,
        mocker: MockerFixture,
        end_date: str | None,
        page_data: PageData,
    ) -> None:
        mock_service = mocker.Mock()
        mocker.patch(
            "scraper.management.commands.scrape_data.ScraperService",
            return_value=mock_service,
        )
        mock_service.scrape_data.return_value = page_data

        out = StringIO()

        call_command(
            "scrape_data",
            url="http://example.com",
            end_date=end_date,
            stdout=out,
        )

        mock_service.scrape_data.assert_called_once_with(
            source_url="http://example.com",
            end_date=end_date,
        )
        mock_service.push_to_db.assert_called_once()
        assert "Data scraped and saved successfully." in out.getvalue()

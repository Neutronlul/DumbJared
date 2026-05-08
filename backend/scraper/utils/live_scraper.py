import logging
import uuid
from urllib.parse import urlparse

import requests

from api.models import Event, Venue
from scraper.exceptions import (
    ScraperFetchError,
    ScraperGameNotFoundError,
    ScraperPostError,
    ScraperUnexpectedResponseError,
)

logger = logging.getLogger(__name__)


HTTP_OK = 200
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_SERVER_ERROR = 500


class LiveScraper:
    def __init__(self, event: Event | None = None) -> None:
        self.event = event

    def fetch_game_id(
        self,
        join_code: str,
        client_id: str | None = None,
    ) -> str:
        """Fetch the game ID associated with a join code.

        Args:
            join_code: Join code used to look up the live game.
            client_id: Optional client ID sent in the request header. If not
                provided, a random UUID is generated. The value must not be an
                empty string.

        Returns:
            The game's 24-character hex ID.

        Raises:
            ValueError: If `client_id` is an empty string.
            ScraperGameNotFoundError: If the join code does not match a game.
            ScraperFetchError: If the request returns an unexpected error.
            ScraperUnexpectedResponseError: If the response body is malformed.

        """
        # Guard against empty string client_id, which is the one
        # thing that will actually cause the endpoint to error
        if client_id == "":
            msg = "client_id cannot be an empty string"
            raise ValueError(msg)

        # If no client_id is provided, generate a random one
        if client_id is None:
            client_id = str(uuid.uuid4())
            client_id_generated = True
        else:
            client_id_generated = False

        logger.debug(
            "Fetching game ID for join code %s with %s client ID %s",
            join_code,
            "randomly generated" if client_id_generated else "provided",
            client_id,
        )

        r = requests.get(
            url=f"https://live.{self._base_url()}/api/player/game/{join_code}/exists",
            headers={"user-client-id": client_id},
            timeout=10,
        )

        logger.debug(
            "Received response with status code %s and body %s",
            r.status_code,
            r.text,
        )

        # Map the known not-found response to the dedicated scraper error
        if not r.ok:
            if (
                r.status_code == HTTP_NOT_FOUND
                and r.json().get("detail") == "game not found"
            ):
                raise ScraperGameNotFoundError(join_code)

            # Treat all other non-OK responses as generic fetch failures
            msg = (
                f"Failed to fetch game ID for join code {join_code}: "
                f"{r.status_code} {r.text}"
            )
            raise ScraperFetchError(msg)

        game = r.json().get("game")

        if game is None:
            msg = f"Unexpected response shape for join code {join_code}: {r.text}"
            raise ScraperUnexpectedResponseError(msg)

        game_id = game.get("gameid")

        logger.debug("Extracted game ID %s for join code %s", game_id, join_code)

        return game_id

    def join_game(
        self,
        slug: str,
        client_id: str,
    ) -> bool:
        """Join a live game with the provided slug and client ID.

        Attempting to join a game with a client ID that has already
        been registered will result in the same response as a successful join.

        Args:
            slug: The game's slug or identifier.
            client_id: The client ID to use when joining the game.

        Returns:
            True if the game was successfully joined.

        Raises:
            ValueError: If `slug` or `client_id` is empty.
            ScraperPostError: If the request returns a non-OK status code.
            ScraperUnexpectedResponseError: If the response does not contain
                `success: true`.

        """
        if not slug or not client_id:
            msg = "slug and client_id must not be empty"
            raise ValueError(msg)

        logger.debug(
            "Attempting to join game with slug %s as client ID %s",
            slug,
            client_id,
        )

        r = requests.post(
            url=f"https://live.{self._base_url()}/api/player/game/{slug}/new-player",
            headers={"Content-Type": "application/json", "user-client-id": client_id},
            json={"client_id": client_id},
            timeout=10,
        )

        logger.debug(
            "Received response with status code %s and body %s",
            r.status_code,
            r.text,
        )

        if not r.ok:
            msg = (
                f"Failed to join game with slug {slug} as client ID {client_id}: "
                f"{r.status_code} {r.text}"
            )
            raise ScraperPostError(msg)

        if r.json().get("success") is not True:
            msg = (
                f"Unexpected response joining game with slug {slug} as "
                f"client ID {client_id}: {r.status_code} {r.text}"
            )
            raise ScraperUnexpectedResponseError(msg)

        logger.debug(
            "Successfully joined game with slug %s as client ID %s",
            slug,
            client_id,
        )
        return True

    def poll_game(
        self,
        slug: str,
        user_client_id: str,
    ) -> dict:
        """Poll the live game endpoint and return the parsed JSON response.

        Args:
            slug: The game's slug or identifier used as the `game_id` query
                parameter.
            user_client_id: Value to send in the `user-client-id` request header.

        Returns:
            The parsed JSON response from the server as a Python dict.

        Raises:
            ValueError: If `slug` or `user_client_id` is empty.
            ScraperFetchError: If the request fails or returns an error status.
            ScraperUnexpectedResponseError: If the response body is malformed.

        """
        if not slug or not user_client_id:
            msg = "slug and user_client_id must not be empty"
            raise ValueError(msg)

        logger.debug(
            "Polling game with slug %s as client ID %s",
            slug,
            user_client_id,
        )

        r = requests.get(
            url=f"https://live.{self._base_url()}/api/player/game/load?game_id={slug}",
            headers={"user-client-id": user_client_id},
            timeout=10,
        )

        logger.debug(
            "Received poll response with status code %s and body %s",
            r.status_code,
            r.text[:500],
        )

        if (
            r.status_code == HTTP_FORBIDDEN
            and r.json().get("detail") == "You do not have access to this game"
        ):
            msg = (
                f"Access denied when polling game with slug {slug} as Client ID "
                f"`{user_client_id}`: "
                f"You must register this client ID to the game before polling."
            )
            raise ScraperFetchError(msg)

        if r.status_code == HTTP_INTERNAL_SERVER_ERROR:
            msg = (
                f"Encountered server error when polling game with slug {slug} "
                f"as Client ID `{user_client_id}`. Are you sure the slug is correct? "
            )
            raise ScraperFetchError(msg)

        if not r.ok:
            msg = (
                f"Failed to poll game with slug {slug} as client ID "
                f"`{user_client_id}`: {r.status_code} {r.text}"
            )
            raise ScraperFetchError(msg)

        try:
            data = r.json()
        except ValueError as e:
            msg = f"Invalid JSON response for slug {slug}: {r.text[:500]}"
            raise ScraperUnexpectedResponseError(msg) from e

        logger.debug(
            "Successfully polled game with slug `%s`, returning data of size %d",
            slug,
            len(r.content),
        )

        return data

    # This works, but it sucks and needs a once-over
    def _base_url(self) -> str:
        if self.event:
            hostname = urlparse(self.event.game.venue.url).hostname

            if hostname is None:
                msg = f"Venue URL {self.event.game.venue.url} is malformed"
                raise ValueError(msg)

            return hostname.removeprefix("www.")

        venue_count = Venue.objects.count()
        if venue_count == 0:
            msg = (
                "Expected at least one Venue in the database to determine "
                "base URL, but found none"
            )
            raise ValueError(msg)

        if venue_count == 1:
            return urlparse(Venue.objects.first().url).hostname.removeprefix("www.")

        msg = "Expected exactly one Venue in the database to determine base URL"
        raise ValueError(msg)

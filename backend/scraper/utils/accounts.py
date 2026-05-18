import logging
import uuid
from typing import cast

import jwt as pyjwt
import requests
from django.conf import settings
from django.core.cache import cache
from redis import Redis

from scraper.exceptions import (
    EmailNotSetError,
    ScraperFetchError,
    ScraperLoginError,
    ScraperPostError,
    ScraperUnexpectedResponseError,
)
from scraper.utils.base_url import get_base_url

logger = logging.getLogger(__name__)


class AccountManager:
    def __init__(
        self,
        email: str | None = None,
        base_url: str | None = None,
        client_id: str | None = None,
        redis: Redis | None = None,
    ) -> None:
        self._base_url = base_url or get_base_url()
        self._email = email
        self._jwt = None
        self._name = None
        self._player_id = None
        self._redis = redis or Redis.from_url(settings.REDIS_URL)
        self.client_id = client_id or str(uuid.uuid4())

    @property
    def email(self) -> str:
        if self._email is None:
            raise EmailNotSetError
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if self._email == value:
            return

        # Changing email changes account identity; clear state tied to prior login.
        # I don't expect to ever actually need this guard, but it doesn't hurt.
        self._jwt = None
        self._name = None
        self._player_id = None
        self._email = value

    @property
    def name(self) -> str:
        if self._name is None:
            msg = (
                "Name is not set for this account. "
                "Try logging in to populate account details."
            )
            raise ValueError(msg)
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        r = requests.put(
            url=f"https://live.{self._base_url}/api/player/set-name",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.jwt}",
            },
            json={"name": value},
            timeout=10,
        )

        if not r.ok:
            msg = f"Failed to change name to {value}: {r.status_code} {r.text}"
            raise ScraperPostError(msg)

        if r.json().get("status") != "success":
            msg = (
                f"Unexpected response while changing name to {value}: "
                f"{r.status_code} {r.text}"
            )
            raise ScraperUnexpectedResponseError(msg)

        logger.debug("Successfully changed name to %s", value)

        self._name = value

    @property
    def jwt(self) -> str:
        if self._jwt is None:
            msg = "No JWT token available for this account, try logging in first"
            raise ScraperLoginError(msg)
        return self._jwt

    @jwt.setter
    def jwt(self, value: str) -> None:
        self._jwt = value
        decoded = pyjwt.decode(value, options={"verify_signature": False})
        self._name = decoded.get("player_name")
        self._player_id = decoded.get("playerid")
        self._email = decoded.get("email")

    @property
    def player_id(self) -> str:
        if self._player_id is None:
            msg = "No player ID available for this account, try logging in first"
            raise ScraperLoginError(msg)

        return self._player_id

    def exists(self) -> bool:
        """Check whether the account exists.

        Sends a GET request to the contact-check endpoint using the
        email stored on this Account instance and returns True if an
        account exists, False otherwise.

        Returns:
            bool: True if the account exists, False if not.

        Raises:
            AttributeError: If the account has no email set.
            ScraperFetchError: If the HTTP request fails (non-OK response).

        Known issue: The endpoint will incorrectly report inexistence
            of accounts if they haven't participated
            in a game yet? Not sure. Needs testing.

        """
        r = requests.get(
            url=f"https://live.{self._base_url}/api/player/contact-check?email={self.email}",
            timeout=10,
        )

        if not r.ok:
            msg = (
                "Failed to check account existence for "
                f"email {self.email}: {r.status_code} {r.text}"
            )
            raise ScraperFetchError(msg)

        exists = r.json()

        logger.debug(
            "Account %sfound for email %s",
            "" if exists else "not ",
            self.email,
        )

        return exists

    def login(
        self,
        username: str | None = None,
        timeout: int = 120,
    ) -> None:
        """Log in to the account, registering it first if necessary.

        Attempts to register and log in with the account's email. If a username
        is provided and the account already exists, raises a ValueError.
        Uses email verification via login code for authentication.

        Args:
            username: Optional player name to register with. If not provided,
                defaults to an empty string.
            timeout: Maximum time in seconds to wait for login code verification.
                Defaults to 120 seconds.

        Raises:
            ScraperLoginError: If a login is already in progress for this account.
            ValueError: If username is provided but the account already exists.
            ScraperPostError: If the registration or validation requests fail.
            ScraperUnexpectedResponseError: If the API response is unexpected.
            TimeoutError: If login code is not received within the timeout period.

        """
        lock_key = f"login_lock:{self.email.lower()}"

        if not cache.add(
            key=lock_key,
            value=True,
            timeout=timeout,
        ):
            msg = f"Login flow already in progress for account {self.email}"
            raise ScraperLoginError(msg)

        try:
            # This guard doesn't make a lot of sense for multiple reasons:
            #
            # 1. If you post to the login endpoint with a new email and no name it'll
            #    happily create the account with a blank name
            #
            # 2. If you post to the login endpoint with an existing email and a new
            #    name, it ignores the new name and logs you in just fine
            #
            # 3. The account existence check isn't really reliable, and only reports
            #    accounts as existing if they've participated in a game or something.
            #
            # You'd think that if I was going to take the time to write all of this I'd
            # just remove the guard entirely, but where's the fun in that?
            if username and self.exists():
                msg = f"Account with email {self.email} already exists, cannot register"
                raise ValueError(msg)

            r = requests.post(
                url=f"https://live.{self._base_url}/api/player/registerplayer",
                headers={
                    "Content-Type": "application/json",
                    "user-client-id": self.client_id,
                },
                json={"email": self.email, "phone": "", "player_name": username or ""},
                timeout=10,
            )

            if not r.ok:
                msg = (
                    f"Failed to log in with email {self.email}: "
                    f"{r.status_code} {r.text}"
                )
                raise ScraperPostError(msg)

            if r.json().get("status") != "success":
                msg = (
                    f"Unexpected response logging in with email "
                    f"{self.email}: {r.status_code} {r.text}"
                )
                raise ScraperUnexpectedResponseError(msg)

            player_id = r.json().get("playerid")

            logger.debug(
                "Initiated login for email %s, player ID %s",
                self.email,
                player_id,
            )

            login_code = self._wait_for_login_code(timeout // 2)

            r = requests.post(
                url=f"https://live.{self._base_url}/api/player/validate-code",
                headers={
                    "Content-Type": "application/json",
                    "user-client-id": self.client_id,
                },
                json={"code": login_code, "playerid": player_id},
                timeout=10,
            )

            if not r.ok:
                msg = (
                    f"Failed to validate login code for email {self.email}: "
                    f"{r.status_code} {r.text}"
                )
                raise ScraperPostError(msg)

            if r.json().get("status") != "success":
                msg = (
                    f"Unexpected response validating login code for email "
                    f"{self.email}: {r.status_code} {r.text}"
                )
                raise ScraperUnexpectedResponseError(msg)

            jwt = r.json().get("message")

            logger.debug(
                "Successfully logged in with email %s, player ID %s",
                self.email,
                player_id,
            )

            self.jwt = jwt

        finally:
            cache.delete(lock_key)

    def _wait_for_login_code(self, timeout: int = 60) -> str:
        key = f":1:login_code:{self.email.lower()}"

        # On the off chance that a code was pushed from a
        # previous attempt but hasn't yet expired, clear it
        #
        # This will probably never actually happen, but better safe than sorry
        self._redis.delete(key)

        result = cast(
            "tuple[bytes, bytes] | None",
            self._redis.blpop(keys=key, timeout=timeout),
        )

        if result is None:
            msg = f"Timed out waiting for login code for {self.email}"
            raise TimeoutError(msg)

        logger.debug("Received login code for %s: %s", self.email, result)

        return result[1].decode()

    def update_token(self) -> str:
        """Request a refreshed JWT from the server and update the instance.

        Sends a POST to the player update-token endpoint using the current
        JWT for authorization. On success the instance attribute ``jwt`` is
        replaced with the returned token and the new token is returned.

        Returns:
            str: the newly issued JWT.

        Raises:
            ScraperPostError: if the HTTP request fails (non-OK status).
            ScraperUnexpectedResponseError: if the response doesn't contain
                the expected token in the JSON payload.

        """
        r = requests.post(
            url=f"https://live.{self._base_url}/api/player/update-token",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.jwt}",
            },
            timeout=10,
        )

        if not r.ok:
            msg = f"Failed to update token for {self.email}: {r.status_code} {r.text}"
            raise ScraperPostError(msg)

        new_token = r.json().get("message")

        if not new_token:
            msg = (
                f"Unexpected response updating token for {self.email}: "
                f"{r.status_code} {r.text}"
            )
            raise ScraperUnexpectedResponseError(msg)

        self.jwt = new_token

        logger.debug("Successfully updated token for %s", self.email)

        return new_token

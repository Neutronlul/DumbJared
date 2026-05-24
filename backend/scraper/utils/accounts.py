import logging
import uuid
from typing import cast

import jwt as pyjwt
import requests
from django.conf import settings
from django.core.cache import cache
from redis import Redis

from core.utils.configuration_guard import require_settings
from scraper.exceptions import (
    AccountAlreadyExistsError,
    EmailNotRoutedError,
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
        self._email = email.lower() if email else None
        self._exists_cache: bool | None = None
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
        if self._email == value.lower():
            return

        # Changing email changes account identity; clear state tied to prior login.
        # I don't expect to ever actually need this guard, but it doesn't hurt.
        self._exists_cache = None
        self._jwt = None
        self._name = None
        self._player_id = None
        self._email = value.lower()

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
        if self._name == value:
            logger.debug("Name is already set to %s, skipping update", value)
            return

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
        if self._jwt == value:
            return

        self._jwt = value
        decoded = pyjwt.decode(value, options={"verify_signature": False})
        self._name = decoded.get("player_name")
        self._player_id = decoded.get("playerid")

        if (email := decoded.get("email")) is not None:
            self._email = email.lower()
            self._exists_cache = (
                True  # This is not entirely truthful but it might save an API call
            )

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
            EmailNotSetError: If the account has no email set.
            ScraperFetchError: If the HTTP request fails (non-OK response).

        Known issue: The endpoint will incorrectly report inexistence
            of accounts if they haven't participated
            in a game yet? Not sure. Needs testing.

        """
        if self._exists_cache is not None:
            return self._exists_cache

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

        self._exists_cache = exists

        return exists

    def login(
        self,
        *,
        manual: bool = False,
        username: str | None = None,
        timeout: int = 120,
    ) -> None:
        """Log in to the account, registering it first if necessary.

        Attempts to register and log in with the account's email. If a username
        is provided and the account already exists, raises a ValueError.
        Uses email verification via login code for authentication.

        Args:
            manual: If True, prompt the user to enter the login code manually
                via stdin instead of waiting for a code pushed to Redis.
                Defaults to False.
            username: Optional player name to register with. If not provided,
                defaults to an empty string.
            timeout: Maximum time in seconds to wait for login code verification.
                Defaults to 120 seconds.

        Raises:
            ScraperLoginError: If a login is already in progress for this account.
            AccountAlreadyExistsError: If username is provided but the account
                already exists.
            EmailNotRoutedError: If email is not routed to worker and manual is False.
            ScraperPostError: If the registration or validation requests fail.
            ScraperUnexpectedResponseError: If the API response is unexpected.
            TimeoutError: If login code is not received within the timeout period.

        """
        lock_key = f"login_lock:{self.email}"

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
            #    accounts as existing if they've participated in a game or something
            #
            # You'd think that if I was going to take the time to write all of this I'd
            # just remove the guard entirely, but where's the fun in that?
            if username and self.exists():
                raise AccountAlreadyExistsError(self.email)

            # This guard makes a little more sense, but is only
            # relevant when trying to do an automated login.
            if not manual:
                # On the off chance that a code was pushed from a
                # previous attempt but hasn't yet expired, clear it
                #
                # This will probably never actually happen, but better safe than sorry
                code_key = f":1:login_code:{self.email}"
                self._redis.delete(code_key)

                # Manual logins with addresses that are routed to the worker are fine,
                # if a little strange. Automated ones are obviously not.
                if not self._email_is_routed():
                    msg = (
                        f"Email {self.email} is not routed to the worker, cannot "
                        "automatically receive login code. Either route the email or "
                        "set manual=True to enter the code manually."
                    )
                    raise EmailNotRoutedError(msg)

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

            data = r.json()

            if data.get("status") != "success" or "playerid" not in data:
                msg = (
                    f"Unexpected response logging in with email "
                    f"{self.email}: {r.status_code} {r.text}"
                )
                raise ScraperUnexpectedResponseError(msg)

            player_id = data["playerid"]

            logger.debug(
                "Initiated login for email %s, player ID %s",
                self.email,
                player_id,
            )

            login_code = (
                input("Enter login code: ")
                if manual
                else self._wait_for_login_code(code_key, timeout // 2)
            )

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

            data = r.json()

            if data.get("status") != "success":
                msg = (
                    f"Unexpected response validating login code for email "
                    f"{self.email}: {r.status_code} {r.text}"
                )
                raise ScraperUnexpectedResponseError(msg)

            jwt = data.get("message")

            if not jwt:
                msg = (
                    f"Login code validation response missing JWT for email "
                    f"{self.email}: {r.status_code} {r.text}"
                )
                raise ScraperUnexpectedResponseError(msg)

            logger.debug(
                "Successfully logged in with email %s, player ID %s",
                self.email,
                player_id,
            )

            self.jwt = jwt

        finally:
            cache.delete(lock_key)

    def _wait_for_login_code(self, key: str, timeout: int = 60) -> str:
        """Wait for and return the login code from Redis.

        Args:
            key: Redis list key to read from.
            timeout: Seconds to wait before timing out.

        Returns:
            The login code as a decoded string.

        Raises:
            TimeoutError: If no login code is received before timing out.

        """
        result = cast(
            "tuple[bytes, bytes] | None",
            self._redis.blpop(keys=key, timeout=timeout),
        )

        if result is None:
            msg = f"Timed out waiting for login code for {self.email}"
            raise TimeoutError(msg)

        logger.debug("Received login code for %s: %s", self.email, result)

        return result[1].decode()

    def _email_is_routed(self) -> bool:
        """Check if the email is routed to the email worker.

        Queries the Cloudflare email routing API to verify if the email
        is configured to route to the email worker, including subaddressing.

        Returns:
            bool: True if the email is routed to the worker, False otherwise.

        Raises:
            ScraperFetchError: if the HTTP request fails (non-OK status).
            RequiredSettingError: if required settings are not configured.

        """
        require_settings(
            "CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_ZONE_ID",
            "EMAIL_WORKER",
            reason="checking email routing",
        )

        worker_name = settings.EMAIL_WORKER

        for zone_id in settings.CLOUDFLARE_ZONE_ID:
            r = requests.get(
                url=f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules",
                headers={
                    "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
                },
                timeout=10,
            )

            if not r.ok:
                msg = (
                    f"Failed to check email routing for {self.email}: "
                    f"{r.status_code} {r.text}"
                )
                raise ScraperFetchError(msg)

            data = r.json()
            result = data.get("result") or []

            subaddressing = self._subaddressing_enabled(zone_id)

            for rule in result:
                routed = any(
                    action.get("type") == "worker"
                    and worker_name in action.get("value", [])
                    for action in rule.get("actions", [])
                )

                if routed:
                    for matcher in rule.get("matchers", []):
                        if (
                            matcher.get("field") == "to"
                            and matcher.get("type") == "literal"
                        ):
                            address = matcher.get("value").lower()

                            if self.email == address:
                                return True

                            if (
                                subaddressing
                                and self._strip_subaddress(self.email) == address
                            ):
                                return True

        return False

    def _subaddressing_enabled(self, zone_id: str) -> bool:
        """Return whether Cloudflare email routing subaddressing is enabled.

        Queries the Cloudflare API to check if email routing subaddressing
        is supported for the specified zone.

        Args:
            zone_id (str): The Cloudflare zone ID to check.

        Returns:
            bool: True if subaddressing is supported, False otherwise.

        Raises:
            ScraperFetchError: if the HTTP request fails (non-OK status).
            ScraperUnexpectedResponseError: if the response doesn't contain
                the expected subaddressing support field.

        """
        # This guard is kinda stupid because the only time this method gets called is
        # in the context of checking whether an email is routed which implies that the
        # token must be set. I guess it'll pay off if that ever changes.
        require_settings(
            "CLOUDFLARE_API_TOKEN",
            reason="checking subaddressing support",
        )

        r = requests.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing",
            headers={
                "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
            },
            timeout=10,
        )

        if not r.ok:
            msg = (
                f"Failed to check subaddressing for {self.email}: "
                f"{r.status_code} {r.text}"
            )
            raise ScraperFetchError(msg)

        data = r.json()
        result = data.get("result")

        if not result or "support_subaddress" not in result:
            msg = (
                f"Unexpected response checking subaddressing for {self.email}: "
                f"{r.status_code} {r.text}"
            )
            raise ScraperUnexpectedResponseError(msg)

        return result["support_subaddress"]

    def _strip_subaddress(self, email: str) -> str:
        """Strip subaddressing from an email address.

        If the email address contains a '+' character before the '@', this method
        removes the '+' and any characters between it and the '@', returning the
        base email address. If no '+' is present, returns the email unchanged.

        Args:
            email (str): The email address to strip.

        Returns:
            str: The email address without subaddressing.

        """
        local, domain = email.split("@", 1)
        local = local.split("+", 1)[0]
        return f"{local}@{domain}"

    def refresh_token(self) -> str:
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

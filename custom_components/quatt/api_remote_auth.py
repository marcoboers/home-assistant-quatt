"""Shared auth client for the Quatt mobile (remote) API.

Handles the Firebase anonymous signup, profile creation, token refresh and
storage used by both the CIC (heatpump) and home battery APIs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import (
    FIREBASE_ACCOUNT_INFO_URL,
    FIREBASE_INSTALLATIONS_URL,
    FIREBASE_REMOTE_CONFIG_URL,
    FIREBASE_SIGNUP_URL,
    FIREBASE_TOKEN_URL,
    GOOGLE_ANDROID_CERT,
    GOOGLE_ANDROID_PACKAGE,
    GOOGLE_API_KEY,
    GOOGLE_APP_ID,
    GOOGLE_APP_INSTANCE_ID,
    GOOGLE_CLIENT_VERSION,
    GOOGLE_FIREBASE_CLIENT,
    QUATT_API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


class QuattRemoteAuthClient:
    """Handles Firebase-based authentication for the Quatt mobile API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        store=None,
    ) -> None:
        """Initialize the auth client."""
        self._session = session
        self._store = store
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._first_name: str | None = None
        self._last_name: str | None = None
        self._fid: str | None = None
        self._firebase_auth_token: str | None = None
        # Serialize refresh_token() so concurrent 401/403 retries across
        # multiple coordinators don't each consume the refresh token.
        self._refresh_lock = asyncio.Lock()

    @property
    def id_token(self) -> str | None:
        """Return the current Firebase id token."""
        return self._id_token

    @property
    def is_authenticated(self) -> bool:
        """Return True when an id token has been obtained."""
        return self._id_token is not None

    @property
    def first_name(self) -> str | None:
        """Return the stored user first name, if any."""
        return self._first_name

    @property
    def last_name(self) -> str | None:
        """Return the stored user last name, if any."""
        return self._last_name

    @property
    def session(self) -> aiohttp.ClientSession:
        """Expose the underlying aiohttp session."""
        return self._session

    def load_tokens(
        self,
        id_token: str | None,
        refresh_token: str | None,
    ) -> None:
        """Load tokens from storage."""
        self._id_token = id_token
        self._refresh_token = refresh_token
        if id_token:
            _LOGGER.debug("Auth tokens loaded from storage")

    def load_profile(
        self,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        """Load the stored user profile (first/last name) from storage."""
        self._first_name = first_name
        self._last_name = last_name

    async def save_tokens(self) -> None:
        """Persist the current auth tokens, preserving other store fields."""
        if not self._store:
            return
        existing = await self._store.async_load() or {}
        existing["id_token"] = self._id_token
        existing["refresh_token"] = self._refresh_token
        await self._store.async_save(existing)
        _LOGGER.debug("Auth tokens saved to storage")

    async def save_profile(self) -> None:
        """Persist the current user profile (first/last name)."""
        if not self._store:
            return
        existing = await self._store.async_load() or {}
        existing["first_name"] = self._first_name
        existing["last_name"] = self._last_name
        await self._store.async_save(existing)
        _LOGGER.debug("Auth profile saved to storage")

    async def ensure_authenticated(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> bool:
        """Ensure we have a valid id token, signing up a new user if needed.

        Returns True when tokens are available (already-loaded, refreshed, or
        freshly signed up). Pairing with a specific device is NOT performed
        here - callers do that per API.

        If ``first_name``/``last_name`` are provided they override any stored
        profile and are persisted after a successful signup.
        """
        if first_name is not None:
            self._first_name = first_name
        if last_name is not None:
            self._last_name = last_name

        effective_first = self._first_name or "HomeAssistant"
        effective_last = self._last_name or "User"

        # Existing tokens: try refreshing to make sure they are valid
        if self._id_token and self._refresh_token:
            if await self.refresh_token():
                await self.save_tokens()
                return True
            _LOGGER.debug("Stored tokens no longer valid, performing full signup")

        # Full signup flow
        if not await self._get_firebase_installation():
            return False
        if not await self._firebase_fetch():
            return False
        if not await self._signup_new_user():
            return False
        if not await self._get_account_info():
            return False
        if not await self._update_user_profile(
            first_name=effective_first, last_name=effective_last
        ):
            return False
        self._first_name = effective_first
        self._last_name = effective_last
        await self.save_tokens()
        await self.save_profile()
        return True

    async def refresh_token(self) -> bool:
        """Refresh the Firebase id token using the stored refresh token.

        Serialized under ``_refresh_lock`` so two concurrent 401/403 retries
        can't both try to spend the same refresh token. The second caller
        waits, then re-checks whether the first already rotated the token.
        """
        async with self._refresh_lock:
            if not self._refresh_token:
                return False

            refresh_token_in_flight = self._refresh_token

            headers = self._firebase_headers()
            payload = {
                "grantType": "refresh_token",
                "refreshToken": refresh_token_in_flight,
            }
            url = f"{FIREBASE_TOKEN_URL}?key={GOOGLE_API_KEY}"

            try:
                async with self._session.post(
                    url, json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._id_token = data.get("id_token")
                        self._refresh_token = data.get("refresh_token")
                        _LOGGER.debug("Token refresh successful")
                        return True
                    # Another caller may have already rotated the token while
                    # we were waiting - succeed silently in that case.
                    if refresh_token_in_flight != self._refresh_token:
                        _LOGGER.debug(
                            "Refresh token rotated by concurrent caller"
                        )
                        return True
                    _LOGGER.warning(
                        "Token refresh failed: %s", await response.text()
                    )
                    return False
            except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
                _LOGGER.warning("Token refresh error: %s", err)
                return False

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200, 201, 204),
        retry_on_auth_error: bool = True,
    ) -> tuple[int, Any | None]:
        """Make an authenticated request to the Quatt mobile API.

        Returns (status, parsed_json_or_none). For non-success responses the
        json body may still be returned when available. On a 401/403 the token
        is refreshed and the request is retried once.
        """
        if not self._id_token:
            return (0, None)

        url = (
            path if path.startswith("http") else f"{QUATT_API_BASE_URL}{path}"
        )

        async def _do_request() -> tuple[int, Any | None]:
            headers = {"Authorization": f"Bearer {self._id_token}"}
            kwargs: dict[str, Any] = {"headers": headers}
            if json_body is not None:
                kwargs["json"] = json_body
            if params is not None:
                kwargs["params"] = params

            async with self._session.request(method, url, **kwargs) as response:
                status = response.status
                data: Any | None = None
                try:
                    data = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    data = None
                if status not in expected_statuses:
                    text = await response.text() if data is None else json.dumps(data)
                    _LOGGER.debug(
                        "Request %s %s failed with status %s: %s",
                        method,
                        url,
                        status,
                        text,
                    )
                return (status, data)

        try:
            status, data = await _do_request()
            if status in (401, 403) and retry_on_auth_error:
                _LOGGER.debug("Got %s, attempting to refresh token", status)
                if await self.refresh_token():
                    await self.save_tokens()
                    status, data = await _do_request()
            return (status, data)
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("Request error %s %s: %s", method, url, err)
            return (0, None)

    def _firebase_headers(self) -> dict[str, str]:
        """Return headers used for Firebase auth requests."""
        return {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Client-Version": GOOGLE_CLIENT_VERSION,
            "X-Firebase-GMPID": GOOGLE_APP_ID,
            "X-Firebase-Client": GOOGLE_FIREBASE_CLIENT,
        }

    async def _get_firebase_installation(self) -> bool:
        """Get the Firebase Installation ID and auth token."""
        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "x-firebase-client": GOOGLE_FIREBASE_CLIENT,
            "x-goog-api-key": GOOGLE_API_KEY,
        }
        payload = {
            "fid": GOOGLE_APP_INSTANCE_ID,
            "appId": GOOGLE_APP_ID,
            "authVersion": "FIS_v2",
            "sdkVersion": "a:19.0.1",
        }

        try:
            async with self._session.post(
                FIREBASE_INSTALLATIONS_URL, json=payload, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._fid = data.get("fid")
                    auth_token = data.get("authToken", {})
                    self._firebase_auth_token = auth_token.get("token")
                    return True
                _LOGGER.error(
                    "Firebase installation failed: %s", await response.text()
                )
                return False
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.error("Firebase installation error: %s", err)
            return False

    async def _firebase_fetch(self) -> bool:
        """Fetch Firebase remote config (required by the mobile app handshake)."""
        if not self._firebase_auth_token:
            return False

        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Goog-Api-Key": GOOGLE_API_KEY,
            "X-Google-GFE-Can-Retry": "yes",
            "X-Goog-Firebase-Installations-Auth": self._firebase_auth_token,
            "X-Firebase-RC-Fetch-Type": "BASE/1",
        }
        payload = {
            "appVersion": "1.42.0",
            "firstOpenTime": "2025-10-14T15:00:00.000Z",
            "timeZone": "Europe/Amsterdam",
            "appInstanceIdToken": self._firebase_auth_token,
            "languageCode": "en-US",
            "appBuild": "964",
            "appInstanceId": GOOGLE_APP_INSTANCE_ID,
            "countryCode": "US",
            "analyticsUserProperties": {},
            "appId": GOOGLE_APP_ID,
            "platformVersion": "33",
            "sdkVersion": "23.0.1",
            "packageName": GOOGLE_ANDROID_PACKAGE,
        }

        try:
            async with self._session.post(
                FIREBASE_REMOTE_CONFIG_URL, json=payload, headers=headers
            ) as response:
                if response.status == 200:
                    return True
                _LOGGER.error(
                    "Firebase remote config fetch failed: %s", await response.text()
                )
                return False
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.error("Firebase remote config fetch error: %s", err)
            return False

    async def _signup_new_user(self) -> bool:
        """Sign up a new anonymous Firebase user."""
        headers = self._firebase_headers()
        payload = {"clientType": "CLIENT_TYPE_ANDROID"}
        url = f"{FIREBASE_SIGNUP_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url, json=payload, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._id_token = data.get("idToken")
                    self._refresh_token = data.get("refreshToken")
                    return True
                _LOGGER.error("User signup failed: %s", await response.text())
                return False
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.error("User signup error: %s", err)
            return False

    async def _get_account_info(self) -> bool:
        """Fetch account info (required by the mobile flow before profile update)."""
        if not self._id_token:
            return False

        headers = self._firebase_headers()
        payload = {"idToken": self._id_token}
        url = f"{FIREBASE_ACCOUNT_INFO_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url, json=payload, headers=headers
            ) as response:
                if response.status == 200:
                    return True
                _LOGGER.error("Get account info failed: %s", await response.text())
                return False
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            _LOGGER.error("Get account info error: %s", err)
            return False

    async def _update_user_profile(self, first_name: str, last_name: str) -> bool:
        """Set the user profile first/last name on the Quatt API side."""
        status, _data = await self.request(
            "PUT",
            "/me",
            json_body={"firstName": first_name, "lastName": last_name},
            expected_statuses=(200, 201),
            retry_on_auth_error=False,
        )
        return status in (200, 201)

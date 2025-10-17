"""Quatt API Client."""
from __future__ import annotations

import asyncio
import logging
import socket
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
    GOOGLE_FIREBASE_CLIENT,
    QUATT_API_BASE_URL,
)

# Number of retries on ServerDisconnectedError
RETRY_ATTEMPTS = 3
PAIRING_TIMEOUT = 60  # seconds to wait for button press
PAIRING_CHECK_INTERVAL = 2  # seconds between checks

_LOGGER = logging.getLogger(__name__)


class QuattApiClientError(Exception):
    """Exception to indicate a general API error."""


class QuattApiClientCommunicationError(QuattApiClientError):
    """Exception to indicate a communication error."""


class QuattApiClientAuthenticationError(QuattApiClientError):
    """Exception to indicate an authentication error."""

class QuattLocalApiClient:
    """Quatt Local API Client."""

    def __init__(
        self,
        ip_address: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Quatt Local API Client."""
        self._ip_address = ip_address
        self._session = session

    async def async_get_data(self) -> any:
        """Get data from the API."""
        return await self._api_wrapper(method="get", path="/beta/feed/data.json")

    @staticmethod
    def check_response_status(response):
        """Check the response status of the api response."""
        if response.status in (401, 403):
            raise QuattApiClientAuthenticationError("Invalid credentials")

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        url = "http://" + self._ip_address + ":8080" + path

        for attempt in range(RETRY_ATTEMPTS):
            try:
                _LOGGER.debug("Fetching data from url: %s (Attempt %d)", url, attempt + 1)
                async with asyncio.timeout(20):
                    response = await self._session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                    )
                    self.check_response_status(response)
                    response.raise_for_status()

                    return await response.json()

            except aiohttp.ServerDisconnectedError as exception:
                # Sometimes the ServerDisconnectedError is raised so retry to get the information
                _LOGGER.debug("Server disconnected error. Retrying... Attempt %d", attempt + 1)
                if attempt == RETRY_ATTEMPTS - 1:
                    raise QuattApiClientCommunicationError(
                        "Server disconnected after multiple attempts"
                    ) from exception
                await asyncio.sleep(0.1)

            except TimeoutError as exception:
                _LOGGER.error("Timeout error fetching information from %s: %s", url, exception)
                raise QuattApiClientCommunicationError(
                    "Timeout error fetching information",
                ) from exception

            except aiohttp.ClientError as exception:
                _LOGGER.error("Client error fetching information from %s: %s", url, exception)
                raise QuattApiClientCommunicationError(
                    "Client error fetching information",
                ) from exception

            except socket.gaierror as exception:
                _LOGGER.error("Socket error fetching information from %s: %s", url, exception)
                raise QuattApiClientCommunicationError(
                    "Socket error fetching information",
                ) from exception

            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected error in _api_wrapper. URL: %s, Exception: %s", url, exception)
                raise QuattApiClientError(
                    "Unexpected error in _api_wrapper",
                ) from exception

        return None


class QuattRemoteApiClient:
    """Remote Quatt API Client (via mobile API)."""

    def __init__(
        self,
        cic: str,
        session: aiohttp.ClientSession,
        store=None,
    ) -> None:
        """Initialize the remote API client."""
        self.cic = cic
        self._session = session
        self._store = store
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._fid: str | None = None
        self._firebase_auth_token: str | None = None
        self._installation_id: str | None = None
        self._pairing_completed: bool = False

    def load_tokens(
        self,
        id_token: str | None,
        refresh_token: str | None,
        installation_id: str | None,
    ) -> None:
        """Load tokens from storage."""
        self._id_token = id_token
        self._refresh_token = refresh_token
        self._installation_id = installation_id
        if id_token:
            _LOGGER.debug("Tokens loaded from storage")

    async def _save_tokens(self) -> None:
        """Save tokens to storage."""
        if self._store:
            await self._store.async_save({
                "id_token": self._id_token,
                "refresh_token": self._refresh_token,
                "installation_id": self._installation_id,
            })
            _LOGGER.debug("Tokens saved to storage")

    async def authenticate(self, first_name: str = "HomeAssistant", last_name: str = "User") -> bool:
        """Authenticate with Firebase and Quatt API."""
        try:
            # Check if we have existing tokens
            if self._id_token and self._refresh_token:
                _LOGGER.debug("Using existing tokens")
                # Try to validate token by getting CIC data
                cic_data = await self.get_cic_data()

                if cic_data:
                    _LOGGER.info("Successfully authenticated with existing tokens")
                    return True

                # Token might be expired, try refresh
                _LOGGER.debug("Existing token failed, attempting refresh")
                if await self.refresh_token():
                    await self._save_tokens()
                    # Verify refreshed token works
                    cic_data = await self.get_cic_data()
                    if cic_data:
                        _LOGGER.info("Successfully authenticated with refreshed token")
                        return True

                # Refresh failed, fall through to full auth
                _LOGGER.warning("Token refresh failed, performing full authentication")

            # Full authentication flow (needed for initial setup or when tokens fail)
            # Step 1: Get Firebase Installation ID
            if not await self._get_firebase_installation():
                return False

            # Step 2: Fetch Firebase Remote Config
            if not await self._firebase_fetch():
                return False

            # Step 3: Sign up new user (anonymous)
            if not await self._signup_new_user():
                return False

            # Step 4: Get account information
            if not await self._get_account_info():
                return False

            # Step 5: Update user profile
            if not await self._update_user_profile(first_name=first_name, last_name=last_name):
                return False

            # Step 6: Request pairing with CIC
            if not await self._request_pair():
                return False

            # Step 7: Wait for user to press button on CIC and verify pairing
            if not await self._wait_for_pairing():
                return False

            # Step 8: Get installation ID
            if not await self._get_installation_id():
                return False

            # Save tokens after successful authentication
            await self._save_tokens()

            return True
        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err)
            return False

    async def _get_firebase_installation(self) -> bool:
        """Get Firebase Installation ID and auth token."""
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
                FIREBASE_INSTALLATIONS_URL,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._fid = data.get("fid")
                    auth_token = data.get("authToken", {})
                    self._firebase_auth_token = auth_token.get("token")
                    _LOGGER.debug("Firebase installation successful")
                    return True
                _LOGGER.error(
                    "Firebase installation failed: %s", await response.text()
                )
                return False
        except Exception as err:
            _LOGGER.error("Firebase installation error: %s", err)
            return False

    async def _firebase_fetch(self) -> bool:
        """Fetch Firebase Remote Config."""
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
                FIREBASE_REMOTE_CONFIG_URL,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    _LOGGER.debug("Firebase remote config fetched successfully")
                    return True
                _LOGGER.error(
                    "Firebase remote config fetch failed: %s", await response.text()
                )
                return False
        except Exception as err:
            _LOGGER.error("Firebase remote config fetch error: %s", err)
            return False

    async def _signup_new_user(self) -> bool:
        """Sign up new anonymous user with Firebase."""
        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Client-Version": "Android/Fallback/X24000001/FirebaseCore-Android",
            "X-Firebase-GMPID": GOOGLE_APP_ID,
            "X-Firebase-Client": GOOGLE_FIREBASE_CLIENT,
        }

        payload = {"clientType": "CLIENT_TYPE_ANDROID"}

        url = f"{FIREBASE_SIGNUP_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._id_token = data.get("idToken")
                    self._refresh_token = data.get("refreshToken")
                    _LOGGER.debug("User signup successful")
                    return True
                _LOGGER.error("User signup failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("User signup error: %s", err)
            return False

    async def _get_account_info(self) -> bool:
        """Get account information from Firebase."""
        if not self._id_token:
            return False

        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Client-Version": "Android/Fallback/X24000001/FirebaseCore-Android",
            "X-Firebase-GMPID": GOOGLE_APP_ID,
            "X-Firebase-Client": GOOGLE_FIREBASE_CLIENT,
        }

        payload = {"idToken": self._id_token}

        url = f"{FIREBASE_ACCOUNT_INFO_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    _LOGGER.debug("Account info retrieved successfully")
                    return True
                _LOGGER.error("Get account info failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("Get account info error: %s", err)
            return False

    async def _update_user_profile(self, first_name: str, last_name: str) -> bool:
        """Update user profile with name."""
        if not self._id_token:
            return False

        headers = {"Authorization": f"Bearer {self._id_token}"}
        payload = {"firstName": first_name, "lastName": last_name}
        url = f"{QUATT_API_BASE_URL}/me"

        try:
            async with self._session.put(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status in (200, 201):
                    _LOGGER.debug("User profile updated with firstName: %s, lastName: %s", first_name, last_name)
                    return True
                _LOGGER.error(
                    "User profile update failed: %s", await response.text()
                )
                return False
        except Exception as err:
            _LOGGER.error("User profile update error: %s", err)
            return False

    async def _request_pair(self) -> bool:
        """Request pairing with CIC device."""
        if not self._id_token:
            return False

        headers = {"Authorization": f"Bearer {self._id_token}"}
        payload = {}
        url = f"{QUATT_API_BASE_URL}/me/cic/{self.cic}/requestPair"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status in (200, 201, 204):
                    _LOGGER.debug("Pairing request successful")
                    return True
                _LOGGER.error("Pairing request failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("Pairing request error: %s", err)
            return False

    async def _wait_for_pairing(self) -> bool:
        """Wait for user to press button on CIC device and verify pairing."""
        if not self._id_token:
            return False

        _LOGGER.info("Waiting for user to press button on CIC device...")

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me"

        # Poll for up to PAIRING_TIMEOUT seconds
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < PAIRING_TIMEOUT:
            try:
                async with self._session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if CIC is in the user's account
                        result = data.get("result", {})
                        cic_ids = result.get("cicIds", [])

                        if cic_ids and self.cic in cic_ids:
                            _LOGGER.info("Pairing completed successfully!")
                            self._pairing_completed = True
                            return True

                        _LOGGER.debug("Pairing not yet completed, waiting...")
                    else:
                        _LOGGER.warning("Failed to check pairing status: %s", await response.text())
            except Exception as err:
                _LOGGER.warning("Error checking pairing status: %s", err)

            # Wait before checking again
            await asyncio.sleep(PAIRING_CHECK_INTERVAL)

        _LOGGER.error("Pairing timeout - user did not press button within %s seconds", PAIRING_TIMEOUT)
        return False

    async def _get_installation_id(self) -> bool:
        """Get installation ID from installations endpoint."""
        if not self._id_token:
            return False

        installations = await self.get_installations()

        if not installations:
            _LOGGER.error("No installations found")
            return False

        # Get the first installation (or match by CIC if available)
        for installation in installations:
            external_id = installation.get("externalId")
            if external_id and external_id.startswith("INS-"):
                self._installation_id = external_id
                _LOGGER.info("Installation ID: %s", self._installation_id)
                return True

        _LOGGER.error("No valid installation ID found")
        return False

    async def refresh_token(self) -> bool:
        """Refresh the authentication token."""
        if not self._refresh_token:
            return False

        headers = {
            "X-Android-Cert": GOOGLE_ANDROID_CERT,
            "X-Android-Package": GOOGLE_ANDROID_PACKAGE,
            "X-Client-Version": "Android/Fallback/X24000001/FirebaseCore-Android",
            "X-Firebase-GMPID": GOOGLE_APP_ID,
            "X-Firebase-Client": GOOGLE_FIREBASE_CLIENT,
        }

        payload = {
            "grantType": "refresh_token",
            "refreshToken": self._refresh_token,
        }

        url = f"{FIREBASE_TOKEN_URL}?key={GOOGLE_API_KEY}"

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._id_token = data.get("id_token")
                    self._refresh_token = data.get("refresh_token")
                    _LOGGER.debug("Token refresh successful")
                    return True
                _LOGGER.error("Token refresh failed: %s", await response.text())
                return False
        except Exception as err:
            _LOGGER.error("Token refresh error: %s", err)
            return False

    async def get_installations(self) -> list[dict[str, Any]]:
        """Get list of installations."""
        if not self._id_token:
            return []

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me/installations"

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", [])
                _LOGGER.error("Get installations failed: %s", await response.text())
                return []
        except Exception as err:
            _LOGGER.error("Get installations error: %s", err)
            return []

    async def get_cic_data(self, retry_on_403: bool = True) -> dict[str, Any] | None:
        """Get CIC device data."""
        if not self._id_token:
            return None

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me/cic/{self.cic}"

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()

                # Handle 401 Unauthorized or 403 Forbidden - token might be expired
                if response.status in (401, 403) and retry_on_403:
                    _LOGGER.warning("Got %s, attempting to refresh token", response.status)
                    if await self.refresh_token():
                        await self._save_tokens()
                        # Retry once with new token (prevent infinite loop with retry_on_403=False)
                        return await self.get_cic_data(retry_on_403=False)
                    _LOGGER.error("Token refresh failed after %s", response.status)
                    return None

                _LOGGER.error("Get CIC data failed with status %s: %s", response.status, await response.text())
                return None
        except Exception as err:
            _LOGGER.error("Get CIC data error: %s", err)
            return None

    async def async_get_data(self) -> Any:
        """Get data from the remote API (compatible with local client interface)."""
        # Get CIC data from remote API
        cic_data = await self.get_cic_data()
        if cic_data:
            return cic_data.get("result", {})
        return None

    async def update_cic_settings(self, settings: dict[str, Any]) -> bool:
        """Update CIC device settings.

        Args:
            settings: Dictionary of settings to update (e.g., {"dayMaxSoundLevel": "normal", "nightMaxSoundLevel": "library"})

        Returns:
            True if update was successful, False otherwise
        """
        if not self._id_token:
            _LOGGER.error("Cannot update CIC settings: not authenticated")
            return False

        headers = {"Authorization": f"Bearer {self._id_token}"}
        url = f"{QUATT_API_BASE_URL}/me/cic/{self.cic}"

        try:
            async with self._session.put(
                url,
                json=settings,
                headers=headers,
            ) as response:
                if response.status in (200, 201, 204):
                    _LOGGER.debug("CIC settings updated successfully: %s", settings)
                    return True

                # Handle 401 Unauthorized or 403 Forbidden - token might be expired
                if response.status in (401, 403):
                    _LOGGER.warning("Got %s while updating CIC settings, attempting to refresh token", response.status)
                    if await self.refresh_token():
                        await self._save_tokens()
                        # Retry once with new token
                        headers = {"Authorization": f"Bearer {self._id_token}"}
                        async with self._session.put(
                            url,
                            json=settings,
                            headers=headers,
                        ) as retry_response:
                            if retry_response.status in (200, 201, 204):
                                _LOGGER.debug("CIC settings updated successfully after token refresh: %s", settings)
                                return True
                            _LOGGER.error("CIC settings update failed after token refresh: %s", await retry_response.text())
                            return False
                    _LOGGER.error("Token refresh failed while updating CIC settings")
                    return False

                _LOGGER.error("CIC settings update failed with status %s: %s", response.status, await response.text())
                return False
        except Exception as err:
            _LOGGER.error("Error updating CIC settings: %s", err)
            return False

"""Remote Quatt CIC (heatpump) API client.

Only contains CIC-specific endpoints (pair, installation lookup, CIC data,
settings, insights). Authentication is delegated to
:class:`QuattRemoteAuthClient`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from .api import QuattApiClient
from .api_remote_auth import QuattRemoteAuthClient
from .const import INSIGHTS_REMOTE_SCAN_INTERVAL

PAIRING_TIMEOUT = 60  # Seconds to wait for button press
PAIRING_CHECK_INTERVAL = 2  # Seconds between checks

_LOGGER = logging.getLogger(__name__)


class QuattCicRemoteApiClient(QuattApiClient):
    """Remote Quatt CIC API Client (via mobile API)."""

    def __init__(
        self,
        cic: str,
        session: aiohttp.ClientSession,
        store=None,
        auth: QuattRemoteAuthClient | None = None,
    ) -> None:
        """Initialize the remote CIC API client."""
        self.cic = cic
        self._session = session
        self._store = store
        self._auth = auth or QuattRemoteAuthClient(session)
        self._installation_id: str | None = None
        self._pairing_completed: bool = False
        # Insights cache keyed by request parameters: key -> (expires_at, result_dict)
        self._insights_cache: dict[
            tuple[str, str, bool], tuple[datetime, dict[str, Any]]
        ] = {}

    @property
    def auth(self) -> QuattRemoteAuthClient:
        """Return the shared auth client."""
        return self._auth

    def load_installation_id(self, installation_id: str | None) -> None:
        """Load the CIC installation id from storage.

        Auth tokens are loaded separately on the shared auth client.
        """
        self._installation_id = installation_id

    async def _save_installation_id(self) -> None:
        """Persist the CIC installation id to this hub's store."""
        if self._store:
            existing = await self._store.async_load() or {}
            existing["installation_id"] = self._installation_id
            await self._store.async_save(existing)

    async def authenticate(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> bool:
        """Authenticate and pair with the CIC device.

        Backward compatible with the pre-split flow: reuse existing tokens when
        available, refresh when expired, otherwise sign up a new user and run
        the pairing handshake.
        """
        try:
            if self._auth.is_authenticated:
                # Try existing tokens first (auth.request handles 401/403 refresh)
                cic_data = await self.get_cic_data()
                if cic_data:
                    _LOGGER.info("Successfully authenticated with existing tokens")
                    return True

                # An explicit refresh + retry as a last effort before full re-signup
                if await self._auth.refresh_token():
                    await self._auth.save_tokens()
                    cic_data = await self.get_cic_data()
                    if cic_data:
                        _LOGGER.info(
                            "Successfully authenticated with refreshed token"
                        )
                        return True

                # Existing tokens no longer usable - reset and fall through
                _LOGGER.warning(
                    "Existing tokens could not be validated, re-pairing with CIC"
                )
                self._auth.load_tokens(None, None)
                self._installation_id = None

            # Full authentication flow (signup + profile)
            if not await self._auth.ensure_authenticated(
                first_name=first_name, last_name=last_name
            ):
                return False

            # Pair with the CIC device
            if not await self._request_pair():
                return False
            if not await self._wait_for_pairing():
                return False

            # Resolve installation id from installations list
            if not await self._resolve_installation_id():
                return False

            await self._save_installation_id()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("Authentication failed: %s", err)
            return False
        else:
            _LOGGER.info("Successfully authenticated with Quatt remote API (CIC)")
            return True

    async def _request_pair(self) -> bool:
        """Request pairing with the CIC device."""
        status, _data = await self._auth.request(
            "POST",
            f"/me/cic/{self.cic}/requestPair",
            json_body={},
            expected_statuses=(200, 201, 204),
            retry_on_auth_error=False,
        )
        return status in (200, 201, 204)

    async def _wait_for_pairing(self) -> bool:
        """Poll for the user pressing the CIC button to confirm the pairing."""
        _LOGGER.info("Waiting for user to press button on CIC device")

        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < PAIRING_TIMEOUT:
            status, data = await self._auth.request(
                "GET", "/me", retry_on_auth_error=False
            )
            if status == 200 and data is not None:
                result = data.get("result", {}) if isinstance(data, dict) else {}
                cic_ids = result.get("cicIds", []) if isinstance(result, dict) else []
                if cic_ids and self.cic in cic_ids:
                    _LOGGER.info("Pairing completed successfully")
                    self._pairing_completed = True
                    return True
                _LOGGER.debug("Pairing not yet completed, waiting")

            await asyncio.sleep(PAIRING_CHECK_INTERVAL)

        _LOGGER.error(
            "Pairing timeout - user did not press button within %s seconds",
            PAIRING_TIMEOUT,
        )
        return False

    async def _resolve_installation_id(self) -> bool:
        """Resolve the CIC installation id from the installations endpoint."""
        installations = await self.get_installations()
        if not installations:
            _LOGGER.error("No installations found")
            return False

        for installation in installations:
            external_id = installation.get("externalId")
            if external_id and external_id.startswith("INS-"):
                self._installation_id = external_id
                _LOGGER.info("Installation ID: %s", self._installation_id)
                return True

        _LOGGER.error("No valid installation ID found")
        return False

    async def get_installations(self) -> list[dict[str, Any]]:
        """Return the list of Quatt installations for this account."""
        if not self._auth.is_authenticated:
            return []
        status, data = await self._auth.request("GET", "/me/installations")
        if status == 200 and isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, list):
                return result
        return []

    async def refresh_token(self) -> bool:
        """Proxy to the auth client's token refresh (kept for backwards compat)."""
        refreshed = await self._auth.refresh_token()
        if refreshed:
            await self._auth.save_tokens()
        return refreshed

    async def get_cic_data(self, retry_on_403: bool = True) -> dict[str, Any] | None:
        """Fetch the CIC device data."""
        if not self._auth.is_authenticated:
            return None
        status, data = await self._auth.request(
            "GET",
            f"/me/cic/{self.cic}",
            retry_on_auth_error=retry_on_403,
        )
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def async_get_data(self, retry_on_client_error: bool = False) -> Any:
        """Get data for the coordinator (CIC feed + insights)."""
        cic_data = await self.get_cic_data()
        if not cic_data:
            return None

        result = cic_data.get("result", {})

        if not self._installation_id:
            _LOGGER.debug("No installation ID available, skipping insights fetch")
            return result

        insights_data = await self.get_insights()
        if insights_data is not None:
            result["insights"] = insights_data

        return result

    async def get_insights(
        self,
        from_date: str = "2020-01-01",
        timeframe: str = "all",
        advanced_insights: bool = False,
        retry_on_403: bool = True,
    ) -> dict[str, Any] | None:
        """Get (cached) insights data for the CIC installation."""
        if not self._auth.is_authenticated or not self._installation_id:
            _LOGGER.error(
                "Cannot get insights: not authenticated or no installation ID"
            )
            return None

        params = {
            "from": from_date,
            "timeframe": timeframe,
            "advancedInsights": str(advanced_insights).lower(),
        }

        key = (from_date, timeframe, advanced_insights)
        cached = self._insights_cache.get(key)
        now = datetime.now(timezone.utc)  # noqa: UP017
        if cached and cached[0] > now:
            _LOGGER.debug("Using cached insights: %s", key)
            return cached[1]

        status, data = await self._auth.request(
            "GET",
            f"/me/installation/{self._installation_id}/insights",
            params=params,
            retry_on_auth_error=retry_on_403,
        )

        if status == 200 and isinstance(data, dict):
            result = data.get("result", {})
            fetched_at = datetime.now(timezone.utc)  # noqa: UP017
            expires_at = fetched_at + timedelta(
                minutes=INSIGHTS_REMOTE_SCAN_INTERVAL
            )
            self._insights_cache[key] = (expires_at, result)

            # Cleanup expired cache entries (keeps memory bounded over time)
            for cache_key, (cache_expires_at, _cached_result) in list(
                self._insights_cache.items()
            ):
                if cache_expires_at <= fetched_at:
                    self._insights_cache.pop(cache_key, None)
            return result

        # Transport/auth/backend failure: fall back to last cached value if any
        if cached is not None:
            _LOGGER.debug("Insights fetch failed, returning cached value (%s)", key)
            return cached[1]
        return None

    async def update_cic_settings(self, settings: dict[str, Any]) -> bool:
        """Update CIC device settings."""
        if not self._auth.is_authenticated:
            _LOGGER.error("Cannot update CIC settings: not authenticated")
            return False

        status, _data = await self._auth.request(
            "PUT",
            f"/me/cic/{self.cic}",
            json_body=settings,
            expected_statuses=(200, 201, 204),
        )
        if status in (200, 201, 204):
            _LOGGER.debug("CIC settings updated successfully: %s", settings)
            return True
        _LOGGER.error("CIC settings update failed with status %s", status)
        return False

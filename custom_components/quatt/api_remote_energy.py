"""Quatt Energy (mijnenergie.quatt.io) API client.

The Quatt Energy site is a separate, web-only Laravel app: there is no Firebase
bearer token. Authentication is a regular HTML login form protected by a
rotating CSRF token. Every authenticated call rides on the session cookie that
the server set during ``POST /login``.

Auth flow:
    1. ``GET  /login``         -> scrape CSRF from ``<meta name="csrf-token">``.
    2. ``POST /login``         -> form-encoded (username, password, remember=on,
       _token=csrf). On success the server sets a session cookie and returns
       the dashboard HTML containing a fresh CSRF and a JS ``const sessionId``.
    3. ``GET  /usage/api/get-costs-data?year={year}&token={csrf}&vat=true``
       returns JSON with the user's EAN at ``allEANs.e[0]``.

Both the CSRF token and the session id rotate on every authenticated page
load, so the client refreshes them from each response. To keep the session
alive while Home Assistant is running, callers periodically call
:meth:`refresh` which re-issues ``GET /login`` and updates the stored token.
"""

from __future__ import annotations

from datetime import date as date_cls, datetime
import logging
import re
import time
from typing import Any

import aiohttp

from .api import (
    QuattApiClient,
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .const import QUATT_ENERGY_BASE_URL, QUATT_ENERGY_USER_AGENT

# Allowed enum values exposed via the public service interface.
PRICES_PERIODS: tuple[str, ...] = ("day", "month", "year")
PRODUCTS: tuple[str, ...] = ("electricity", "gas")

_LOGGER = logging.getLogger(__name__)

# Patterns that the auth flow scrapes from server HTML. They are intentionally
# permissive about whitespace and quote style because the markup is rendered
# by the upstream framework and not under our control.
_RE_CSRF_META = re.compile(
    r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_RE_SESSION_ID_CONST = re.compile(
    r"""const\s+sessionId\s*=\s*['"]([^'"]+)['"]""",
)


class QuattEnergyApiClient(QuattApiClient):
    """API client for the Quatt Energy (mijnenergie) web portal."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        store=None,
    ) -> None:
        """Initialize the Energy API client.

        The provided ``session`` MUST be an isolated client session (not the
        shared HA one) because the auth flow relies on the laravel session
        cookie surviving across requests for this user only.
        """
        self._session = session
        self._username = username
        self._password = password
        self._store = store

        self._csrf_token: str | None = None
        self._session_id: str | None = None
        self._ean: str | None = None

    # ------------------------------------------------------------------ #
    # State accessors
    # ------------------------------------------------------------------ #

    @property
    def username(self) -> str:
        """Return the configured login username (email)."""
        return self._username

    @property
    def csrf_token(self) -> str | None:
        """Return the current CSRF form token (rotates per request)."""
        return self._csrf_token

    @property
    def session_id(self) -> str | None:
        """Return the JS-side session id scraped from the dashboard HTML."""
        return self._session_id

    @property
    def ean(self) -> str | None:
        """Return the EAN of the primary energy meter, once known."""
        return self._ean

    @property
    def is_authenticated(self) -> bool:
        """Return True when a successful login has produced a session id."""
        return self._csrf_token is not None and self._session_id is not None

    def load_state(
        self,
        csrf_token: str | None,
        session_id: str | None,
        ean: str | None,
    ) -> None:
        """Restore previously persisted state from this hub's store."""
        self._csrf_token = csrf_token
        self._session_id = session_id
        self._ean = ean

    async def _save_state(self) -> None:
        """Persist the current state to this hub's store.

        Cookies live in-memory only (the aiohttp cookie jar is not persisted),
        but storing csrf/session/ean lets us survive restarts gracefully and
        is also what step 2 will read for service calls.
        """
        if not self._store:
            return
        existing = await self._store.async_load() or {}
        existing["csrf_token"] = self._csrf_token
        existing["session_id"] = self._session_id
        existing["ean"] = self._ean
        await self._store.async_save(existing)

    # ------------------------------------------------------------------ #
    # Public auth flow
    # ------------------------------------------------------------------ #

    async def authenticate(self) -> bool:
        """Run the full login flow (form CSRF -> POST -> EAN lookup).

        Returns True only when every step succeeded and we now have a valid
        ``csrf_token``, ``session_id`` and ``ean`` cached on the client.
        """
        try:
            form_csrf = await self._fetch_login_csrf()
            await self._post_login(form_csrf)
            if not await self._fetch_ean():
                # EAN is required for the hub to be useful; treat its absence
                # as an auth failure so the config flow surfaces it to the user.
                _LOGGER.error(
                    "Quatt Energy login succeeded but no EAN was returned",
                )
                return False
        except QuattApiClientError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise QuattApiClientCommunicationError(
                f"Quatt Energy network error: {err}",
            ) from err
        await self._save_state()
        return True

    async def refresh(self) -> bool:
        """Keep the session alive by reloading ``/login`` and rotating tokens.

        If the server has logged us out (no CSRF in the response, or the
        response redirects us back to the auth wall), this transparently
        retries a full :meth:`authenticate` cycle.
        """
        try:
            html = await self._get_text("/login")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise QuattApiClientCommunicationError(
                f"Quatt Energy refresh failed: {err}",
            ) from err

        new_csrf = _extract_csrf(html)
        if not new_csrf:
            # No CSRF in the response means the server doesn't recognise our
            # session anymore -> re-login from scratch.
            _LOGGER.debug("Quatt Energy refresh found no CSRF, re-authenticating")
            return await self.authenticate()

        self._csrf_token = new_csrf
        new_session_id = _extract_session_id(html)
        if new_session_id:
            self._session_id = new_session_id
        await self._save_state()
        return True

    async def async_get_data(self, retry_on_client_error: bool = False) -> Any:
        """Coordinator entry point - keep auth alive and surface state.

        Step 1 only exposes the EAN and the rotating auth identifiers; the
        real timeseries calls are added in step 2.
        """
        await self.refresh()
        return {
            "ean": self._ean,
            "csrfToken": self._csrf_token,
            "sessionId": self._session_id,
        }

    # ------------------------------------------------------------------ #
    # Internal HTTP helpers
    # ------------------------------------------------------------------ #

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build the default headers (User-Agent is required by the portal)."""
        headers = {
            "User-Agent": QUATT_ENERGY_USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        }
        if extra:
            headers.update(extra)
        return headers

    async def _get_text(self, path: str) -> str:
        """GET ``path`` and return the response body as text."""
        url = f"{QUATT_ENERGY_BASE_URL}{path}"
        async with self._session.get(
            url, headers=self._headers(), allow_redirects=True
        ) as response:
            self.check_response_status(response)
            if response.status >= 400:
                text = await response.text()
                raise QuattApiClientError(
                    f"GET {path} returned {response.status}: {text[:200]}",
                )
            return await response.text()

    async def _fetch_login_csrf(self) -> str:
        """Fetch ``GET /login`` and pull out the form CSRF token."""
        html = await self._get_text("/login")
        token = _extract_csrf(html)
        if not token:
            raise QuattApiClientError(
                "Quatt Energy login page did not contain a CSRF token",
            )
        self._csrf_token = token
        return token

    async def _post_login(self, form_csrf: str) -> None:
        """POST the login form and parse the resulting dashboard HTML."""
        url = f"{QUATT_ENERGY_BASE_URL}/login"
        form = {
            "username": self._username,
            "password": self._password,
            "remember": "on",
            "_token": form_csrf,
        }
        headers = self._headers(
            {
                "Origin": QUATT_ENERGY_BASE_URL,
                "Referer": f"{QUATT_ENERGY_BASE_URL}/login",
                # Laravel inspects this to distinguish XHR from full form posts.
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        async with self._session.post(
            url,
            data=form,
            headers=headers,
            allow_redirects=True,
        ) as response:
            if response.status in (401, 403):
                raise QuattApiClientAuthenticationError(
                    "Quatt Energy login rejected the credentials",
                )
            if response.status >= 400:
                text = await response.text()
                raise QuattApiClientError(
                    f"Quatt Energy login failed ({response.status}): {text[:200]}",
                )
            text = await response.text()

        # If we land back on /login the credentials were wrong but the server
        # answered with 200 (typical Laravel behaviour for re-rendered forms).
        if "name=\"password\"" in text and "name=\"username\"" in text:
            raise QuattApiClientAuthenticationError(
                "Quatt Energy login form was re-rendered (bad credentials)",
            )

        new_csrf = _extract_csrf(text)
        if not new_csrf:
            raise QuattApiClientError(
                "Quatt Energy login response missing the new CSRF token",
            )
        self._csrf_token = new_csrf

        session_id = _extract_session_id(text)
        if not session_id:
            raise QuattApiClientError(
                "Quatt Energy login response missing the sessionId constant",
            )
        self._session_id = session_id

    # ------------------------------------------------------------------ #
    # Public service endpoints
    # ------------------------------------------------------------------ #

    async def get_prices(
        self,
        period: str = "day",
        product: str = "electricity",
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch tariff price data from ``/webapp/api/get-prices-data``.

        ``period`` is one of ``day``/``month``/``year``. The API still wants a
        concrete ``date`` parameter on month/year queries; per the portal's
        convention it must be the first of the chosen month, so missing
        month/day default to ``01`` automatically. Day-period queries default
        to today.
        """
        _validate_choice("period", period, PRICES_PERIODS)
        _validate_choice("product", product, PRODUCTS)

        today = datetime.now().astimezone().date()
        if period == "day":
            target = _build_date(today, year, month, day)
        else:
            # Month/year queries: the portal expects the first of the month.
            target = _build_date(today, year, month, 1).replace(day=1)

        params = {
            "suppname": "quatt",
            "product": product,
            "date": target.strftime("%d-%m-%Y"),
            "period": period,
            "vat": "true",
            "tax": "true",
            "markup": "true",
            "drilldown_key": "_drilldown",
        }
        return await self._api_get_json(
            "/webapp/api/get-prices-data",
            params=params,
            include_session=True,
        )

    async def get_power(
        self,
        product: str = "electricity",
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch electricity / gas usage.

        Mirrors the battery services: when ``month`` and ``day`` are both
        supplied a per-day hourly drilldown is returned, otherwise the
        full-year aggregate. ``year`` defaults to the current year.
        """
        _validate_choice("product", product, PRODUCTS)

        if (month is None) ^ (day is None):
            _LOGGER.error(
                "get_power drilldown requires both month and day (got month=%s day=%s)",
                month,
                day,
            )
            return None

        today = datetime.now().astimezone().date()
        effective_year = year if year is not None else today.year

        if month is not None and day is not None:
            target = date_cls(effective_year, month, day)
            params = {
                "date": target.isoformat(),
                "ean": self._ean or "",
                "action": "hourly_usage",
                "type": product,
                "amount_types[]": "dial_total",
                "tooltip_type": "datetime_value_tooltip",
                "vat": "true",
                "merge_energy_tax_with_usage": "true",
            }
            return await self._api_get_json(
                "/usage/api/get-drilldown-data", params=params
            )

        params = {
            "year": str(effective_year),
            "product": product,
            "vat": "true",
        }
        return await self._api_get_json(
            "/usage/api/get-year-data", params=params
        )

    async def get_costs(
        self,
        product: str = "electricity",
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch electricity / gas costs.

        Same scope rules as :meth:`get_power`: ``month`` + ``day`` switches to
        the hourly drilldown (``action=hourly_costs``); otherwise the
        full-year cost aggregate is returned.
        """
        _validate_choice("product", product, PRODUCTS)

        if (month is None) ^ (day is None):
            _LOGGER.error(
                "get_costs drilldown requires both month and day (got month=%s day=%s)",
                month,
                day,
            )
            return None

        today = datetime.now().astimezone().date()
        effective_year = year if year is not None else today.year

        if month is not None and day is not None:
            target = date_cls(effective_year, month, day)
            params = {
                "date": target.isoformat(),
                "ean": self._ean or "",
                "action": "hourly_costs",
                "type": product,
                "amount_types[]": "amounts_total",
                "tooltip_type": "datetime_value_tooltip",
                "vat": "true",
                "merge_energy_tax_with_usage": "true",
            }
            return await self._api_get_json(
                "/usage/api/get-drilldown-data", params=params
            )

        params = {
            "year": str(effective_year),
            "vat": "true",
        }
        return await self._api_get_json(
            "/usage/api/get-costs-data", params=params
        )

    # ------------------------------------------------------------------ #
    # Authenticated JSON helper (used by all public endpoints)
    # ------------------------------------------------------------------ #

    async def _api_get_json(
        self,
        path: str,
        params: dict[str, str],
        include_session: bool = False,
    ) -> dict[str, Any] | None:
        """GET an authenticated JSON endpoint, retrying once on session loss.

        Every call gets a fresh ``token=<csrf>``, an XHR-style cache buster
        (``_=<ms>``) and - when ``include_session`` is set - a ``sess=<id>``
        param. A 401/403 (or a redirect back to /login) triggers one
        full :meth:`authenticate` retry before giving up.
        """
        for attempt in range(2):
            if not self._csrf_token:
                # No token at all -> re-auth before issuing the call.
                if not await self.authenticate():
                    raise QuattApiClientAuthenticationError(
                        "Quatt Energy not authenticated"
                    )

            merged: dict[str, str] = dict(params)
            merged["token"] = self._csrf_token or ""
            if include_session:
                merged["sess"] = self._session_id or ""
            merged["_"] = str(int(time.time() * 1000))

            url = f"{QUATT_ENERGY_BASE_URL}{path}"
            headers = self._headers(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Referer": f"{QUATT_ENERGY_BASE_URL}/usage",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            try:
                async with self._session.get(
                    url,
                    params=merged,
                    headers=headers,
                    allow_redirects=False,
                ) as response:
                    status = response.status
                    location = response.headers.get("Location", "")
                    # 30x to /login means the cookie expired; force re-auth.
                    redirected_to_login = (
                        status in (301, 302, 303, 307, 308)
                        and "/login" in location
                    )
                    if status in (401, 403) or redirected_to_login:
                        if attempt == 0:
                            _LOGGER.debug(
                                "Quatt Energy session lost on %s (status=%s "
                                "location=%s), re-authenticating",
                                path,
                                status,
                                location,
                            )
                            self._csrf_token = None
                            self._session_id = None
                            continue
                        raise QuattApiClientAuthenticationError(
                            f"Quatt Energy auth lost ({path}, status {status})",
                        )
                    if status >= 400:
                        text = await response.text()
                        raise QuattApiClientError(
                            f"{path} returned {status}: {text[:200]}",
                        )
                    try:
                        return await response.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as err:
                        raise QuattApiClientError(
                            f"{path} returned non-JSON body: {err}",
                        ) from err
            except (aiohttp.ClientError, TimeoutError) as err:
                raise QuattApiClientCommunicationError(
                    f"Quatt Energy network error on {path}: {err}",
                ) from err

        # Both attempts fell through without returning - treat as auth failure.
        raise QuattApiClientAuthenticationError(
            f"Quatt Energy auth lost ({path})",
        )

    async def _fetch_ean(self) -> bool:
        """Pull the EAN out of the costs-data JSON endpoint."""
        if not self._csrf_token:
            return False

        year = datetime.now().astimezone().year
        url = f"{QUATT_ENERGY_BASE_URL}/usage/api/get-costs-data"
        params = {
            "year": str(year),
            "token": self._csrf_token,
            "vat": "true",
        }
        headers = self._headers(
            {
                "Accept": "application/json, text/plain, */*",
                "Referer": f"{QUATT_ENERGY_BASE_URL}/usage",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        async with self._session.get(
            url, params=params, headers=headers, allow_redirects=True
        ) as response:
            self.check_response_status(response)
            if response.status >= 400:
                text = await response.text()
                raise QuattApiClientError(
                    f"costs-data returned {response.status}: {text[:200]}",
                )
            try:
                data = await response.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise QuattApiClientError(
                    f"costs-data returned non-JSON body: {err}",
                ) from err

        ean = _extract_first_electricity_ean(data)
        if not ean:
            _LOGGER.debug("costs-data response did not contain an EAN: %s", data)
            return False
        self._ean = ean
        return True


# ---------------------------------------------------------------------- #
# Parser helpers
# ---------------------------------------------------------------------- #


def _extract_csrf(html: str) -> str | None:
    """Return the ``content`` attribute of the ``csrf-token`` meta tag, if any."""
    match = _RE_CSRF_META.search(html)
    return match.group(1) if match else None


def _extract_session_id(html: str) -> str | None:
    """Return the value of the ``const sessionId = '...'`` JS literal."""
    match = _RE_SESSION_ID_CONST.search(html)
    return match.group(1) if match else None


def _validate_choice(name: str, value: str, allowed: tuple[str, ...]) -> None:
    """Raise if ``value`` is not in ``allowed`` (cheap defensive guard)."""
    if value not in allowed:
        raise QuattApiClientError(
            f"Invalid {name} '{value}'. Expected one of {', '.join(allowed)}.",
        )


def _build_date(
    today: date_cls,
    year: int | None,
    month: int | None,
    day: int | None,
) -> date_cls:
    """Build a date from optional year/month/day pieces, defaulting to today."""
    return date_cls(
        year if year is not None else today.year,
        month if month is not None else today.month,
        day if day is not None else today.day,
    )


def _extract_first_electricity_ean(payload: Any) -> str | None:
    """Pluck ``allEANs.e[0]`` out of the costs-data JSON safely.

    The portal returns the EAN as a JSON number (e.g. ``871687940005610202``)
    rather than a string, so we accept both and always normalise to ``str``.
    """
    if not isinstance(payload, dict):
        return None
    all_eans = payload.get("allEANs")
    if not isinstance(all_eans, dict):
        return None
    electricity = all_eans.get("e")
    if isinstance(electricity, list) and electricity:
        first = electricity[0]
        if isinstance(first, str) and first:
            return first
        if isinstance(first, int):
            return str(first)
    return None

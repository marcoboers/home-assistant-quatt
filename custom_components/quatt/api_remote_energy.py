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

from datetime import date as date_cls, datetime, timedelta
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
        include_vat: bool = True,
        include_tax: bool = True,
        include_markup: bool = True,
    ) -> None:
        """Initialize the Energy API client.

        The provided ``session`` MUST be an isolated client session (not the
        shared HA one) because the auth flow relies on the laravel session
        cookie surviving across requests for this user only.

        ``include_vat``/``include_tax``/``include_markup`` map directly to the
        ``vat``/``tax``/``markup`` query params on the prices endpoint; they
        control whether the returned prices include the corresponding
        surcharge. Defaults match the portal's "everything on" preset.
        """
        self._session = session
        self._username = username
        self._password = password
        self._store = store
        self._include_vat = include_vat
        self._include_tax = include_tax
        self._include_markup = include_markup

        self._csrf_token: str | None = None
        self._session_id: str | None = None
        self._ean: str | None = None
        # Today's raw prices payload, cached to avoid hammering the portal on
        # every coordinator tick - the API publishes new prices once a day.
        self._today_prices_cache: tuple[datetime, dict[str, Any]] | None = None

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

    @property
    def include_vat(self) -> bool:
        """Whether the portal should include VAT in returned prices."""
        return self._include_vat

    @property
    def include_tax(self) -> bool:
        """Whether the portal should include energy tax in returned prices."""
        return self._include_tax

    @property
    def include_markup(self) -> bool:
        """Whether the portal should include the supplier markup in prices."""
        return self._include_markup

    async def set_price_flags(
        self,
        include_vat: bool | None = None,
        include_tax: bool | None = None,
        include_markup: bool | None = None,
    ) -> bool:
        """Update one or more price-display flags.

        Returns True if any flag actually changed. On change the cached daily
        prices are dropped so the next coordinator tick fetches fresh prices
        with the new params, and the new flags are persisted to the per-hub
        store.
        """
        changed = False
        if include_vat is not None and include_vat != self._include_vat:
            self._include_vat = include_vat
            changed = True
        if include_tax is not None and include_tax != self._include_tax:
            self._include_tax = include_tax
            changed = True
        if include_markup is not None and include_markup != self._include_markup:
            self._include_markup = include_markup
            changed = True
        if changed:
            self._today_prices_cache = None
            await self._save_state()
        return changed

    def load_state(
        self,
        csrf_token: str | None,
        session_id: str | None,
        ean: str | None,
        include_vat: bool | None = None,
        include_tax: bool | None = None,
        include_markup: bool | None = None,
    ) -> None:
        """Restore previously persisted state from this hub's store.

        The ``include_*`` flags only override the in-memory defaults when
        non-None, so a fresh install (empty store) keeps the True/True/True
        defaults set by ``__init__``.
        """
        self._csrf_token = csrf_token
        self._session_id = session_id
        self._ean = ean
        if include_vat is not None:
            self._include_vat = bool(include_vat)
        if include_tax is not None:
            self._include_tax = bool(include_tax)
        if include_markup is not None:
            self._include_markup = bool(include_markup)

    async def _save_state(self) -> None:
        """Persist the current state to this hub's store.

        Cookies live in-memory only (the aiohttp cookie jar is not persisted),
        but storing csrf/session/ean/flags lets us survive restarts with the
        user's preferences intact.
        """
        if not self._store:
            return
        existing = await self._store.async_load() or {}
        existing["csrf_token"] = self._csrf_token
        existing["session_id"] = self._session_id
        existing["ean"] = self._ean
        existing["include_vat"] = self._include_vat
        existing["include_tax"] = self._include_tax
        existing["include_markup"] = self._include_markup
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

        Returns the rotating auth identifiers, the meter EAN, and (when
        available) a summary of today's quarter-hourly prices used by the
        price sensors. The raw prices response is cached - see
        :meth:`_get_today_prices_cached` - so the per-minute auth tick
        doesn't translate into per-minute price polling.
        """
        await self.refresh()
        data: dict[str, Any] = {
            "ean": self._ean,
            "csrfToken": self._csrf_token,
            "sessionId": self._session_id,
        }

        prices = await self._get_today_prices_cached()
        if prices:
            summary = _summarize_today_prices(prices)
            if summary is not None:
                data["prices"] = summary

        return data

    async def _get_today_prices_cached(self) -> dict[str, Any] | None:
        """Return today's prices payload, cached for ~60 minutes.

        Prices are published once per day so a long-lived cache is safe and
        much friendlier than the coordinator's 1-minute base cadence. If a
        fresh fetch fails we fall back to the last cached payload (even when
        it is past its TTL) so sensors don't go ``unavailable`` on a hiccup.

        Only proper dict payloads are cached - the portal sometimes responds
        with a JSON-encoded string on transient auth issues, and caching that
        would poison every subsequent tick.
        """
        now = datetime.now().astimezone()
        if self._today_prices_cache and self._today_prices_cache[0] > now:
            return self._today_prices_cache[1]

        try:
            response = await self.get_prices(period="day", product="electricity")
        except QuattApiClientError as err:
            _LOGGER.debug("Today prices fetch failed: %s", err)
            response = None

        if not isinstance(response, dict):
            if response is not None:
                _LOGGER.debug(
                    "Today prices response was not a dict (%s); discarding",
                    type(response).__name__,
                )
            if self._today_prices_cache is not None:
                return self._today_prices_cache[1]
            return None

        self._today_prices_cache = (now + timedelta(minutes=60), response)
        return response

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
        include_vat: bool | None = None,
        include_tax: bool | None = None,
        include_markup: bool | None = None,
    ) -> dict[str, Any] | None:
        """Fetch tariff price data from ``/webapp/api/get-prices-data``.

        ``period`` is one of ``day``/``month``/``year``. The API still wants a
        concrete ``date`` parameter on month/year queries; per the portal's
        convention it must be the first of the chosen month, so missing
        month/day default to ``01`` automatically. Day-period queries default
        to today.

        ``include_vat``/``include_tax``/``include_markup`` default to the
        client-level flags (set via :meth:`set_price_flags`) but can be
        overridden per-call - the service action passes explicit values so
        users can probe the API without touching their stored preferences.
        """
        _validate_choice("period", period, PRICES_PERIODS)
        _validate_choice("product", product, PRODUCTS)

        today = datetime.now().astimezone().date()
        if period == "day":
            target = _build_date(today, year, month, day)
        else:
            # Month/year queries: the portal expects the first of the month.
            target = _build_date(today, year, month, 1).replace(day=1)

        effective_vat = self._include_vat if include_vat is None else include_vat
        effective_tax = self._include_tax if include_tax is None else include_tax
        effective_markup = (
            self._include_markup if include_markup is None else include_markup
        )

        params = {
            "suppname": "quatt",
            "product": product,
            "date": target.strftime("%d-%m-%Y"),
            "period": period,
            "vat": _bool_param(effective_vat),
            "tax": _bool_param(effective_tax),
            "markup": _bool_param(effective_markup),
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
                        data = await response.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as err:
                        raise QuattApiClientError(
                            f"{path} returned non-JSON body: {err}",
                        ) from err

                    # The portal answers 200 OK with body "Token mismatch!"
                    # (literally a JSON-encoded string) when the CSRF or
                    # session is rejected, so handle it like a 401.
                    if _is_token_mismatch(data):
                        if attempt == 0:
                            _LOGGER.debug(
                                "Quatt Energy token rejected on %s (body=%r), "
                                "re-authenticating",
                                path,
                                data,
                            )
                            self._csrf_token = None
                            self._session_id = None
                            continue
                        raise QuattApiClientAuthenticationError(
                            f"Quatt Energy token still rejected after retry "
                            f"({path}, body={data!r})",
                        )

                    return data
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


def _summarize_today_prices(payload: Any) -> dict[str, Any] | None:
    """Reduce the day's quarter-hourly prices to current/min/max/avg.

    Input is the raw ``/webapp/api/get-prices-data?period=day`` response;
    entries are quarter-hour slots with ``y`` (EUR/kWh) and ``date``
    (``YYYY-MM-DD HH:MM:SS`` in local time). Slots run 00:00 through 23:45,
    each covering 15 minutes.

    The portal occasionally returns a JSON-encoded string instead of an
    object (transient auth state); we treat any non-dict payload as "no
    data available" rather than letting it crash the coordinator.
    """
    if not isinstance(payload, dict):
        return None
    prices_section = payload.get("prices")
    if not isinstance(prices_section, dict):
        return None
    raw = prices_section.get("data")
    if not isinstance(raw, list) or not raw:
        return None

    parsed: list[tuple[datetime, float, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        y = entry.get("y")
        date_str = entry.get("date")
        if not isinstance(y, int | float) or not isinstance(date_str, str):
            continue
        try:
            ts = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        label = entry.get("name") if isinstance(entry.get("name"), str) else None
        parsed.append((ts, float(y), label or ts.strftime("%H:%M")))

    if not parsed:
        return None

    parsed.sort(key=lambda item: item[0])

    cheapest = min(parsed, key=lambda item: item[1])
    most_expensive = max(parsed, key=lambda item: item[1])

    # Compare against a naive local "now" because the API timestamps are
    # naive local time (no timezone info attached).
    now = datetime.now().replace(microsecond=0)

    current: tuple[datetime, float, str] | None = None
    for index, item in enumerate(parsed):
        slot_start = item[0]
        slot_end = (
            parsed[index + 1][0]
            if index + 1 < len(parsed)
            else slot_start + timedelta(minutes=15)
        )
        if slot_start <= now < slot_end:
            current = item
            break
    if current is None:
        # Outside the day window (e.g. data is stale or we're between days):
        # use the closest past slot, falling back to the first slot.
        past = [item for item in parsed if item[0] <= now]
        current = past[-1] if past else parsed[0]

    cur_ts, cur_price, cur_name = current
    cur_end = cur_ts + timedelta(minutes=15)
    cheap_ts, cheap_price, cheap_name = cheapest
    cheap_end = cheap_ts + timedelta(minutes=15)
    exp_ts, exp_price, exp_name = most_expensive
    exp_end = exp_ts + timedelta(minutes=15)

    # Prefer the API-provided average; fall back to a computed mean.
    prices_avg_section = payload.get("pricesAvg") or {}
    day_average = prices_avg_section.get("priceAvg")
    if not isinstance(day_average, int | float):
        day_average = sum(item[1] for item in parsed) / len(parsed)

    return {
        "current": {
            "price": round(cur_price, 6),
            "periodStart": cur_ts.isoformat(),
            "periodEnd": cur_end.isoformat(),
            "name": cur_name,
            "window": f"{cur_name}-{cur_end.strftime('%H:%M')}",
        },
        "cheapest": {
            "price": round(cheap_price, 6),
            "time": cheap_ts.isoformat(),
            "timeEnd": cheap_end.isoformat(),
            "name": cheap_name,
            "window": f"{cheap_name}-{cheap_end.strftime('%H:%M')}",
        },
        "mostExpensive": {
            "price": round(exp_price, 6),
            "time": exp_ts.isoformat(),
            "timeEnd": exp_end.isoformat(),
            "name": exp_name,
            "window": f"{exp_name}-{exp_end.strftime('%H:%M')}",
        },
        "dayAverage": round(float(day_average), 6),
        "product": prices_section.get("product"),
        "date": prices_section.get("date"),
    }


def _bool_param(value: bool) -> str:
    """Serialise a boolean for the portal's query string (``true``/``false``)."""
    return "true" if value else "false"


def _is_token_mismatch(data: Any) -> bool:
    """Detect the portal's 200-OK-but-unauthorized response.

    Known shape so far is a bare JSON string ``"Token mismatch!"``. We also
    accept a dict carrying the same message (``error``/``message`` keys) in
    case the portal ever wraps it.
    """
    if isinstance(data, str):
        return "token mismatch" in data.strip().lower()
    if isinstance(data, dict):
        for key in ("error", "message", "msg"):
            value = data.get(key)
            if isinstance(value, str) and "token mismatch" in value.lower():
                return True
    return False


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

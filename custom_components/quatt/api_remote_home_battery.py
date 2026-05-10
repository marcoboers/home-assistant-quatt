"""Remote Quatt Home Battery API client.

Pair endpoint: POST /me/devices/homeBattery/pair
Status endpoint: GET /me/installation/{installation_id}/homeBattery/status

Authentication is delegated to :class:`QuattRemoteAuthClient`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from .api import QuattApiClient
from .api_remote_auth import QuattRemoteAuthClient
from .const import INSIGHTS_REMOTE_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

INSIGHTS_CACHE_TTL_MINUTES = INSIGHTS_REMOTE_SCAN_INTERVAL  # reuse CIC insights TTL


class QuattHomeBatteryApiClient(QuattApiClient):
    """Remote Quatt Home Battery API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        store=None,
        auth: QuattRemoteAuthClient | None = None,
        installation_id: str | None = None,
    ) -> None:
        """Initialize the home battery client."""
        self._session = session
        self._store = store
        self._auth = auth or QuattRemoteAuthClient(session)
        self._installation_id: str | None = installation_id
        # Cache for today's insights: (expires_at, payload). Avoids hammering
        # the insights endpoint on every short status-poll tick.
        self._today_insights_cache: tuple[datetime,
                                          dict[str, Any]] | None = None
        # Same idea for the day-level energy flow payload.
        self._today_energy_flow_cache: (
            tuple[datetime, dict[str, Any]] | None
        ) = None

    @property
    def auth(self) -> QuattRemoteAuthClient:
        """Return the shared auth client."""
        return self._auth

    @property
    def installation_id(self) -> str | None:
        """Return the paired home battery installation id."""
        return self._installation_id

    def load_installation_id(self, installation_id: str | None) -> None:
        """Load the paired installation id from storage.

        Auth tokens are loaded separately on the shared auth client.
        """
        self._installation_id = installation_id

    async def _save_installation_id(self) -> None:
        """Persist the paired installation id to this hub's store."""
        if self._store:
            existing = await self._store.async_load() or {}
            existing["installation_id"] = self._installation_id
            await self._store.async_save(existing)

    async def authenticate_and_pair(
        self,
        access_key_uuid: str,
        serial_number: str,
        check_code: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> bool:
        """Sign up (if needed) and pair a home battery."""
        try:
            if not self._auth.is_authenticated:
                if not await self._auth.ensure_authenticated(
                    first_name=first_name, last_name=last_name
                ):
                    return False

            installation_id = await self._pair_home_battery(
                access_key_uuid=access_key_uuid,
                serial_number=serial_number,
                check_code=check_code,
            )
            if not installation_id:
                return False

            self._installation_id = installation_id
            await self._save_installation_id()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("Home battery pairing failed: %s", err)
            return False
        else:
            _LOGGER.info(
                "Home battery paired, installation id: %s", installation_id
            )
            return True

    async def _pair_home_battery(
        self,
        access_key_uuid: str,
        serial_number: str,
        check_code: str,
    ) -> str | None:
        """Call the pair endpoint and return the installation id."""
        payload = {
            "accessKeyUuid": access_key_uuid,
            "serialNumber": serial_number,
            "checkCode": check_code,
        }
        status, data = await self._auth.request(
            "POST",
            "/me/devices/homeBattery/pair",
            json_body=payload,
            expected_statuses=(200, 201),
        )
        if status not in (200, 201) or not isinstance(data, dict):
            _LOGGER.error(
                "Home battery pair failed: status=%s body=%s", status, data
            )
            return None

        result = data.get("result") or {}
        installation_id = result.get("installationUuid")
        if not installation_id:
            _LOGGER.error(
                "Home battery pair returned no installationUuid: %s", data)
            return None
        return installation_id

    async def get_installation(self) -> dict[str, Any] | None:
        """Fetch the full installation record (includes ``solarCapacitykWp``)."""
        if not self._auth.is_authenticated or not self._installation_id:
            return None
        status, data = await self._auth.request(
            "GET", f"/me/installation/{self._installation_id}"
        )
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def update_solar_capacity(self, value: float) -> bool:
        """PATCH the installation's ``solarCapacitykWp`` field."""
        if not self._auth.is_authenticated or not self._installation_id:
            _LOGGER.error("Cannot update solar capacity: not authenticated")
            return False
        status, _data = await self._auth.request(
            "PATCH",
            f"/me/installation/{self._installation_id}/solarCapacitykWp",
            json_body={"solarCapacitykWp": value},
            expected_statuses=(200, 201, 204),
        )
        if status in (200, 201, 204):
            _LOGGER.debug("Updated solarCapacitykWp to %s", value)
            return True
        _LOGGER.error(
            "Failed to update solarCapacitykWp (status %s)", status
        )
        return False

    async def get_status(self) -> dict[str, Any] | None:
        """Fetch home battery status for the paired installation."""
        if not self._auth.is_authenticated or not self._installation_id:
            return None
        status, data = await self._auth.request(
            "GET",
            f"/me/installation/{self._installation_id}/homeBattery/status",
        )
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def get_home_battery_insights(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch home battery insights.

        Without a date, returns the default (today) payload. When all three of
        year/month/day are supplied the specific-date endpoint is used:
        ``/insights/homeBattery/{YYYY}/{MM}/{DD}``.
        """
        if not self._auth.is_authenticated or not self._installation_id:
            return None

        path = (
            f"/me/installation/{self._installation_id}/insights/homeBattery"
        )
        if year is not None and month is not None and day is not None:
            path = f"{path}/{year:04d}/{month:02d}/{day:02d}"

        status, data = await self._auth.request("GET", path)
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def _get_today_insights_cached(self) -> dict[str, Any] | None:
        """Return today's insights response, cached to avoid repeated polling."""
        now = datetime.now(timezone.utc)  # noqa: UP017
        if self._today_insights_cache and self._today_insights_cache[0] > now:
            return self._today_insights_cache[1]

        insights = await self.get_home_battery_insights()
        if insights is None:
            # On failure fall back to last cached payload, even if expired
            if self._today_insights_cache is not None:
                return self._today_insights_cache[1]
            return None

        expires_at = now + timedelta(minutes=INSIGHTS_CACHE_TTL_MINUTES)
        self._today_insights_cache = (expires_at, insights)
        return insights

    async def get_energy_flow(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch the energy-flow timeseries + daily/monthly/yearly aggregate.

        Endpoints:
          - day:   ``/insights/energyFlow/{YYYY}/{MM}/{DD}``
          - month: ``/insights/energyFlow/{YYYY}/{MM}``
          - year:  ``/insights/energyFlow/{YYYY}``

        Without any date argument, today's day-level response is returned.
        """
        if not self._auth.is_authenticated or not self._installation_id:
            return None

        # Guard invalid combinations before hitting the API
        if day is not None and (year is None or month is None):
            _LOGGER.error(
                "Energy flow day argument requires both year and month"
            )
            return None
        if month is not None and year is None:
            _LOGGER.error("Energy flow month argument requires year")
            return None

        # Default to today when nothing was provided
        if year is None and month is None and day is None:
            today = datetime.now().astimezone()
            year, month, day = today.year, today.month, today.day

        path = (
            f"/me/installation/{self._installation_id}/insights/energyFlow"
        )
        if year is not None:
            path += f"/{year:04d}"
        if month is not None:
            path += f"/{month:02d}"
        if day is not None:
            path += f"/{day:02d}"

        status, data = await self._auth.request("GET", path)
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def _get_today_energy_flow_cached(self) -> dict[str, Any] | None:
        """Return today's energy-flow payload, cached like the insights one."""
        now = datetime.now(timezone.utc)  # noqa: UP017
        if (
            self._today_energy_flow_cache
            and self._today_energy_flow_cache[0] > now
        ):
            return self._today_energy_flow_cache[1]

        flow = await self.get_energy_flow()  # today by default
        if flow is None:
            if self._today_energy_flow_cache is not None:
                return self._today_energy_flow_cache[1]
            return None

        expires_at = now + timedelta(minutes=INSIGHTS_CACHE_TTL_MINUTES)
        self._today_energy_flow_cache = (expires_at, flow)
        return flow

    async def get_savings_overview(self) -> dict[str, Any] | None:
        """Fetch the savings overview for the paired installation."""
        if not self._auth.is_authenticated or not self._installation_id:
            return None
        status, data = await self._auth.request(
            "GET",
            f"/me/installation/{self._installation_id}/insights/savings/overview",
        )
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def get_savings(
        self,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch the savings timeseries + aggregate for a month or year.

        Endpoints:
          - month: ``/insights/savings/{YYYY}/{MM}``
          - year:  ``/insights/savings/{YYYY}``

        Without arguments, the current year + current month is returned.
        """
        if not self._auth.is_authenticated or not self._installation_id:
            return None

        if month is not None and year is None:
            _LOGGER.error("Savings month argument requires year")
            return None

        if year is None and month is None:
            today = datetime.now().astimezone()
            year, month = today.year, today.month

        path = (
            f"/me/installation/{self._installation_id}/insights/savings"
        )
        if year is not None:
            path += f"/{year:04d}"
        if month is not None:
            path += f"/{month:02d}"

        status, data = await self._auth.request("GET", path)
        if status == 200 and isinstance(data, dict):
            return data
        return None

    async def async_get_data(self, retry_on_client_error: bool = False) -> Any:
        """Return merged status + savings data for the coordinator.

        Each endpoint is independent - a failure in one does not clear the
        other, so sensors remain available when only one side is degraded.
        """
        data: dict[str, Any] = {}

        status = await self.get_status()
        if status:
            status_result = status.get("result")
            if isinstance(status_result, dict):
                data.update(status_result)
        else:
            _LOGGER.warning(
                "Home battery status endpoint returned no data for installation %s",
                self._installation_id,
            )

        savings = await self.get_savings_overview()
        if savings:
            savings_result = savings.get("result")
            if isinstance(savings_result, dict):
                _add_euro_fields(savings_result.get("cumulative"))
                _add_euro_fields(savings_result.get("yesterday"))
                data["savings"] = savings_result
        else:
            _LOGGER.warning(
                "Home battery savings endpoint returned no data for installation %s",
                self._installation_id,
            )

        insights = await self._get_today_insights_cached()
        if insights:
            insights_result = insights.get("result")
            summary = _summarize_today_insights(insights_result)
            if summary is not None:
                data["insights"] = summary

        installation = await self.get_installation()
        if installation:
            inst_result = installation.get("result")
            if isinstance(inst_result, dict):
                # Pull specific top-level installation fields into coordinator
                # data so they can back sensors/number entities directly.
                if "solarCapacitykWp" in inst_result:
                    data["solarCapacitykWp"] = inst_result["solarCapacitykWp"]

        flow = await self._get_today_energy_flow_cached()
        if flow:
            flow_result = flow.get("result")
            if isinstance(flow_result, dict):
                aggregated = flow_result.get("aggregated")
                if isinstance(aggregated, dict):
                    flow_section = dict(aggregated)
                    period = flow_result.get("period")
                    if isinstance(period, dict):
                        flow_section["periodKey"] = period.get("key")
                        flow_section["periodFrom"] = period.get("from")
                        flow_section["periodTo"] = period.get("to")
                    data["energyFlow"] = flow_section

        return data or None


def _summarize_today_insights(raw: Any) -> dict[str, Any] | None:
    """Reduce today's quarter-hour timeseries to a small set of scalar fields.

    The default (today) endpoint returns a plain list of 15-minute entries with
    fields ``timestamp``, ``powerInKW``, ``chargeState``, ``controlAction`` and
    ``controlMode`` (newest first).
    """
    if not isinstance(raw, list) or not raw:
        return None

    total_charged_kwh = 0.0
    total_discharged_kwh = 0.0
    peak_charge_kw = 0.0
    peak_discharge_kw = 0.0
    charge_states: list[int] = []
    latest_timestamp: str | None = None

    for entry in raw:
        if not isinstance(entry, dict):
            continue
        power_kw = entry.get("powerInKW")
        if isinstance(power_kw, (int | float)):
            # Each entry covers 15 minutes = 0.25h
            energy_kwh = float(power_kw) * 0.25
            if energy_kwh > 0:
                total_charged_kwh += energy_kwh
                peak_charge_kw = max(peak_charge_kw, float(power_kw))
            elif energy_kwh < 0:
                total_discharged_kwh += -energy_kwh
                peak_discharge_kw = max(peak_discharge_kw, -float(power_kw))

        charge_state = entry.get("chargeState")
        if isinstance(charge_state, (int | float)):
            charge_states.append(int(charge_state))

        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str) and (
            latest_timestamp is None or timestamp > latest_timestamp
        ):
            latest_timestamp = timestamp

    summary: dict[str, Any] = {
        "totalChargedKwh": round(total_charged_kwh, 3),
        "totalDischargedKwh": round(total_discharged_kwh, 3),
        "peakChargeKw": round(peak_charge_kw, 3),
        "peakDischargeKw": round(peak_discharge_kw, 3),
        "dataPoints": len(raw),
    }
    if charge_states:
        summary["maxChargeStatePercent"] = max(charge_states)
        summary["minChargeStatePercent"] = min(charge_states)
    if latest_timestamp is not None:
        summary["latestTimestamp"] = latest_timestamp
    return summary


def _add_euro_fields(section: dict[str, Any] | None) -> None:
    """Expand *Cents* fields in a savings section into *Eur* float fields."""
    if not isinstance(section, dict):
        return
    for key in list(section.keys()):
        if "Cents" not in key:
            continue
        value = section[key]
        if value is None:
            continue
        try:
            section[key.replace("Cents", "Eur")] = float(value) / 100.0
        except (TypeError, ValueError):
            continue

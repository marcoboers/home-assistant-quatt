"""Tests for home battery API helpers and coordinator data assembly."""
# pylint: disable=import-error,wrong-import-position,protected-access

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.quatt.api_remote_home_battery import (
    QuattHomeBatteryApiClient,
    _add_euro_fields,
    _summarize_today_insights,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Load a JSON fixture by file name."""
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# _summarize_today_insights
# ---------------------------------------------------------------------------


def test_summarize_today_insights() -> None:
    """The quarter-hour list is reduced to totals, peaks and charge states."""
    entries = [
        {"timestamp": "2026-08-21T10:00:00Z", "powerInKW": 2.0, "chargeState": 40},
        {"timestamp": "2026-08-21T10:15:00Z", "powerInKW": -1.0, "chargeState": 35},
        {"timestamp": "2026-08-21T09:45:00Z", "powerInKW": 0, "chargeState": 38},
        {"timestamp": "2026-08-21T10:30:00Z", "powerInKW": 4.0, "chargeState": 50},
    ]
    summary = _summarize_today_insights(entries)

    assert summary == {
        "totalChargedKwh": 1.5,  # (2.0 + 4.0) * 0.25h
        "totalDischargedKwh": 0.25,  # 1.0 * 0.25h
        "peakChargeKw": 4.0,
        "peakDischargeKw": 1.0,
        "dataPoints": 4,
        "maxChargeStatePercent": 50,
        "minChargeStatePercent": 35,
        "latestTimestamp": "2026-08-21T10:30:00Z",
    }


def test_summarize_today_insights_skips_malformed_entries() -> None:
    """Non-dict entries and non-numeric powers are skipped but counted."""
    entries = [
        "garbage",
        {"powerInKW": "n/a", "chargeState": "high"},
        {"timestamp": "2026-08-21T10:00:00Z", "powerInKW": 1.0, "chargeState": 20},
    ]
    summary = _summarize_today_insights(entries)

    assert summary["dataPoints"] == 3
    assert summary["totalChargedKwh"] == 0.25
    assert summary["maxChargeStatePercent"] == 20
    assert summary["latestTimestamp"] == "2026-08-21T10:00:00Z"


def test_summarize_today_insights_no_optional_fields() -> None:
    """Without charge states or timestamps the optional keys are omitted."""
    summary = _summarize_today_insights([{"powerInKW": 1.0}])
    assert "maxChargeStatePercent" not in summary
    assert "minChargeStatePercent" not in summary
    assert "latestTimestamp" not in summary


@pytest.mark.parametrize("raw", [None, {}, [], "text", 42])
def test_summarize_today_insights_invalid_input(raw) -> None:
    """Anything but a non-empty list yields None."""
    assert _summarize_today_insights(raw) is None


def test_summarize_today_insights_rejects_periodized_payload() -> None:
    """The dated/periodized insights shape (a dict) is not summarized.

    The summarizer only handles the plain list returned by the today
    endpoint; the periodized endpoint result (period/timeseries dict, with
    powerKw/chargeStatePercent field names) must yield None.
    """
    periodized = load_fixture("home_battery_insights_day.json")["result"]
    assert _summarize_today_insights(periodized) is None


# ---------------------------------------------------------------------------
# _add_euro_fields
# ---------------------------------------------------------------------------


def test_add_euro_fields() -> None:
    """Every numeric *Cents field gets a *Eur sibling divided by 100."""
    section = {
        "totalSavedCents": 1234,
        "yesterdaySavedCents": "250",
        "skippedCents": None,
        "invalidCents": "n/a",
        "unrelated": 5,
    }
    _add_euro_fields(section)

    assert section["totalSavedEur"] == 12.34
    assert section["yesterdaySavedEur"] == 2.5
    assert "skippedEur" not in section
    assert "invalidEur" not in section
    assert "unrelatedEur" not in section


@pytest.mark.parametrize("section", [None, "text", 42, ["totalSavedCents"]])
def test_add_euro_fields_non_dict_noop(section) -> None:
    """Non-dict sections are left untouched without raising."""
    _add_euro_fields(section)


# ---------------------------------------------------------------------------
# async_get_data section merging
# ---------------------------------------------------------------------------


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    status: Any = None,
    savings: Any = None,
    insights: Any = None,
    installation: Any = None,
    energy_flow: Any = None,
) -> QuattHomeBatteryApiClient:
    """Create a client with every endpoint stubbed to a fixed payload."""
    client = QuattHomeBatteryApiClient(
        session=object(), auth=object(), installation_id="INS-test"
    )

    async def _return(value):
        return value

    monkeypatch.setattr(client, "get_status", lambda: _return(status))
    monkeypatch.setattr(
        client, "get_savings_overview", lambda: _return(savings)
    )
    monkeypatch.setattr(
        client, "_get_today_insights_cached", lambda: _return(insights)
    )
    monkeypatch.setattr(client, "get_installation", lambda: _return(installation))
    monkeypatch.setattr(
        client, "_get_today_energy_flow_cached", lambda: _return(energy_flow)
    )
    return client


@pytest.mark.asyncio
async def test_async_get_data_merges_sections(monkeypatch) -> None:
    """Status, installation and energy flow merge into one coordinator dict."""
    client = _make_client(
        monkeypatch,
        status=load_fixture("home_battery_status.json"),
        installation={"result": {"solarCapacitykWp": 5}},
        energy_flow=load_fixture("home_battery_energy_flow_day.json"),
    )

    data = await client.async_get_data()

    # Status result is merged at the top level
    assert data["uuid"] == "DEV-12345678-1234-5678-1234-567812345678"
    assert data["connected"] is True
    assert data["live"]["powerKw"] == 7.4312

    # Installation field is lifted into the coordinator data
    assert data["solarCapacitykWp"] == 5

    # Energy flow: aggregated values flattened with period metadata
    assert data["energyFlow"]["batteryChargedKWh"] == 21.9
    assert data["energyFlow"]["gridImportKWh"] == 25.75
    assert data["energyFlow"]["periodKey"] == "2026-08-21"
    assert data["energyFlow"]["periodFrom"] == "2026-08-20T22:00:00.000Z"


@pytest.mark.asyncio
async def test_async_get_data_savings_euro_expansion(monkeypatch) -> None:
    """Savings sections get *Eur fields derived from *Cents fields."""
    client = _make_client(
        monkeypatch,
        savings={
            "result": {
                "cumulative": {"savedCents": 12345},
                "yesterday": {"savedCents": 678},
            }
        },
    )

    data = await client.async_get_data()

    assert data["savings"]["cumulative"]["savedEur"] == 123.45
    assert data["savings"]["yesterday"]["savedEur"] == 6.78


@pytest.mark.asyncio
async def test_async_get_data_sections_are_independent(monkeypatch) -> None:
    """A failing status endpoint must not clear the other sections."""
    client = _make_client(
        monkeypatch,
        status=None,
        energy_flow=load_fixture("home_battery_energy_flow_day.json"),
    )

    data = await client.async_get_data()

    assert "uuid" not in data
    assert data["energyFlow"]["batteryChargedKWh"] == 21.9


@pytest.mark.asyncio
async def test_async_get_data_all_endpoints_down(monkeypatch) -> None:
    """When every endpoint fails the coordinator gets None, not {}."""
    client = _make_client(monkeypatch)
    assert await client.async_get_data() is None

"""Tests for pure config flow helpers."""
# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

import pytest

from custom_components.quatt.config_flow import (
    QuattFlowHandler,
    _parse_battery_qr_url,
)


# ---------------------------------------------------------------------------
# _parse_battery_qr_url
# ---------------------------------------------------------------------------


def test_parse_battery_qr_url_full() -> None:
    """A full QR URL yields uuid, serial and check code (mac is ignored)."""
    url = (
        "https://app.quatt.io/battery/"
        "DEV-12345678-1234-5678-1234-567812345678/QOD000000000000/1234/AA:BB:CC"
    )
    assert _parse_battery_qr_url(url) == (
        "DEV-12345678-1234-5678-1234-567812345678",
        "QOD000000000000",
        "1234",
    )


def test_parse_battery_qr_url_without_mac() -> None:
    """The mac address segment is optional."""
    url = "https://app.quatt.io/battery/uuid-1/serial-1/9876"
    assert _parse_battery_qr_url(url) == ("uuid-1", "serial-1", "9876")


def test_parse_battery_qr_url_strips_whitespace() -> None:
    """Leading/trailing whitespace from the QR scan is tolerated."""
    url = "  https://app.quatt.io/battery/uuid-1/serial-1/9876/AA \n"
    assert _parse_battery_qr_url(url) == ("uuid-1", "serial-1", "9876")


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("https://quatt.io/battery/a/b/c/d", id="wrong-host"),
        pytest.param("https://app.quatt.example/battery/a/b/c/d", id="spoofed-host"),
        pytest.param("https://app.quatt.io/other/a/b/c/d", id="wrong-path-prefix"),
        pytest.param("https://app.quatt.io/battery/uuid/serial", id="too-few-segments"),
        pytest.param("https://app.quatt.io/battery", id="missing-segments"),
        pytest.param("not a url", id="invalid-url"),
        pytest.param("", id="empty-url"),
    ],
)
def test_parse_battery_qr_url_invalid(url: str) -> None:
    """Anything that is not a valid battery QR URL yields None."""
    assert _parse_battery_qr_url(url) is None


def test_parse_battery_qr_url_non_string() -> None:
    """Non-string input is swallowed by the blanket except and yields None."""
    assert _parse_battery_qr_url(None) is None


# ---------------------------------------------------------------------------
# is_valid_ip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ip", "expected"),
    [
        pytest.param("192.168.1.10", True, id="private-ipv4-192"),
        pytest.param("10.0.0.1", True, id="private-ipv4-10"),
        pytest.param("::1", True, id="ipv6-loopback"),
        pytest.param("2001:db8::1", True, id="ipv6-documentation"),
        pytest.param("999.1.1.1", False, id="invalid-ipv4-octet"),
        pytest.param("192.168.1", False, id="incomplete-ipv4"),
        pytest.param("cic-hostname", False, id="hostname"),
        pytest.param("", False, id="empty"),
    ],
)
def test_is_valid_ip(ip: str, expected: bool) -> None:
    """IPv4 and IPv6 addresses validate; everything else does not."""
    flow = QuattFlowHandler()
    assert flow.is_valid_ip(ip) is expected

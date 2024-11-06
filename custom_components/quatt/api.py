"""Quatt API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout
import logging

_LOGGER = logging.getLogger(__name__)


class QuattApiClientError(Exception):
    """Exception to indicate a general API error."""


class QuattApiClientCommunicationError(QuattApiClientError):
    """Exception to indicate a communication error."""


class QuattApiClientAuthenticationError(QuattApiClientError):
    """Exception to indicate an authentication error."""


class QuattApiClient:
    """Quatt API Client."""

    def __init__(
        self,
        ip_address: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Quatt API Client."""
        self._ip_address = ip_address
        self._session = session

    async def async_get_data(self) -> any:
        """Get data from the API."""
        return await self._api_wrapper(method="get", path="/beta/feed/data.json")

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            url = "http://" + self._ip_address + ":8080" + path

            _LOGGER.debug("Fetching data from url: %s", url)
            async with async_timeout.timeout(20):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )

                if response.status in (401, 403):
                    raise QuattApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()

                return await response.json()

        except asyncio.TimeoutError as exception:
            _LOGGER.debug("Timeout error fetching information")
            raise QuattApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.debug("Error fetching information")
            raise QuattApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.debug("Something really wrong happened!")
            raise QuattApiClientError("Something really wrong happened!") from exception

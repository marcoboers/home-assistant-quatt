"""Local Quatt API Client."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any

import aiohttp

from .api import QuattApiClient, QuattApiClientCommunicationError, QuattApiClientError

RETRY_ATTEMPTS = 3  # Number of retries on ServerDisconnectedError

_LOGGER = logging.getLogger(__name__)


class QuattLocalApiClient(QuattApiClient):
    """Quatt Local API Client."""

    def __init__(
        self,
        ip_address: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Quatt Local API Client."""
        self._ip_address = ip_address
        self._session = session

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(method="get", path="/beta/feed/data.json")

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        url = "http://" + self._ip_address + ":8080" + path

        for attempt in range(RETRY_ATTEMPTS):
            try:
                _LOGGER.debug(
                    "Fetching data from url: %s (Attempt %d)", url, attempt + 1
                )
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
                _LOGGER.debug(
                    "Server disconnected error. Retrying... Attempt %d", attempt + 1
                )
                if attempt == RETRY_ATTEMPTS - 1:
                    raise QuattApiClientCommunicationError(
                        "Server disconnected after multiple attempts"
                    ) from exception
                await asyncio.sleep(0.1)

            except TimeoutError as exception:
                _LOGGER.error(
                    "Timeout error fetching information from %s: %s", url, exception
                )
                raise QuattApiClientCommunicationError(
                    "Timeout error fetching information",
                ) from exception

            except aiohttp.ClientError as exception:
                _LOGGER.debug(
                    "Client error fetching information from %s: %s. Retrying... Attempt %d",
                    url,
                    exception,
                    attempt + 1,
                )
                if attempt == RETRY_ATTEMPTS - 1:
                    raise QuattApiClientCommunicationError(
                        "Client error fetching information",
                    ) from exception
                # During startup the device might be busy, wait longer before retrying
                # This is especially true when a DHCP request is detected after startup
                await asyncio.sleep(60)

            except socket.gaierror as exception:
                _LOGGER.error(
                    "Socket error fetching information from %s: %s", url, exception
                )
                raise QuattApiClientCommunicationError(
                    "Socket error fetching information",
                ) from exception

            except json.JSONDecodeError as exception:
                _LOGGER.error("JSON decode error from %s: %s", url, exception)
                raise QuattApiClientError(
                    "JSON decode error",
                ) from exception

            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.error(
                    "Unexpected error in _api_wrapper. URL: %s, Exception: %s",
                    url,
                    exception,
                )
                raise QuattApiClientError(
                    "Unexpected error in _api_wrapper",
                ) from exception

        return None

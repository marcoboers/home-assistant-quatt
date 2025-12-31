"""Base Quatt API Client."""

from abc import ABC, abstractmethod
from typing import Any


class QuattApiClientError(Exception):
    """Exception to indicate a general API error."""


class QuattApiClientCommunicationError(QuattApiClientError):
    """Exception to indicate a communication error."""


class QuattApiClientAuthenticationError(QuattApiClientError):
    """Exception to indicate an authentication error."""


class QuattApiClient(ABC):
    """Abstract base class for Quatt data update coordinators."""

    @staticmethod
    def check_response_status(response):
        """Check the response status of the api response."""
        if response.status in (401, 403):
            raise QuattApiClientAuthenticationError("Invalid credentials")

    @abstractmethod
    async def async_get_data(self, retry_on_client_error: bool = False) -> Any:
        """Asynchronously fetch data from the Quatt API.

        Implementations must return the parsed data retrieved from the API.
        Raise:
            QuattApiClientCommunicationError: On communication issues
            QuattApiClientAuthenticationError: On authentication failures
        """
        raise NotImplementedError

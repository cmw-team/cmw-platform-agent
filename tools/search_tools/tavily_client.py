"""Minimal, validated HTTP client for Tavily Search.

The client owns the fixed Russian-region request contract. It does not read
environment variables, retry requests, log secrets, or expose provider error
details. The LangChain tool supplies the API key and maps typed client errors to
the public tool response.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any
from urllib.parse import urlsplit

import requests

SEARCH_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_SECONDS = 30
MAX_QUERY_CHARACTERS = 400


class TavilySearchError(RuntimeError):
    """Base error for a failed Tavily search."""


class TavilyInvalidRequestError(TavilySearchError):
    """Tavily rejected the request parameters."""


class TavilyAuthenticationError(TavilySearchError):
    """Tavily rejected the configured API key."""


class TavilyRateLimitError(TavilySearchError):
    """Tavily rejected the request because its rate limit was reached."""


class TavilyPlanLimitError(TavilySearchError):
    """The Tavily plan usage limit was reached."""


class TavilyPayGoLimitError(TavilySearchError):
    """The Tavily pay-as-you-go limit was reached."""


class TavilyUnavailableError(TavilySearchError):
    """Tavily or the network is temporarily unavailable."""


class TavilyInvalidResponseError(TavilySearchError):
    """Tavily returned an invalid successful response."""


@dataclass(frozen=True, slots=True)
class TavilySearchResult:
    """One normalized Tavily result exposed to the model."""

    title: str
    url: str
    content: str
    score: float

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON-compatible result contract."""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
        }


@dataclass(frozen=True, slots=True)
class TavilySearchResponse:
    """Normalized response for one Tavily request."""

    query: str
    results: tuple[TavilySearchResult, ...]
    response_time: float
    request_id: str
    credits: int

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON-compatible search contract."""
        return {
            "query": self.query,
            "results": [result.as_dict() for result in self.results],
            "response_time": self.response_time,
            "request_id": self.request_id,
            "credits": self.credits,
        }


def normalize_search_query(query: object) -> str:
    """Strip and validate a Tavily query without coercing other types."""
    if not isinstance(query, str):
        raise TypeError("Search query must be a string.")
    normalized = query.strip()
    if not normalized:
        raise ValueError("Search query must not be empty.")
    if len(normalized) > MAX_QUERY_CHARACTERS:
        message = (
            f"Search query must not exceed {MAX_QUERY_CHARACTERS} characters."
        )
        raise ValueError(message)
    return normalized


def _invalid_field_message(field_name: str) -> str:
    return f"Tavily returned an invalid {field_name} field."


def _number(value: object, *, field_name: str) -> float:
    invalid_message = _invalid_field_message(field_name)
    if isinstance(value, bool):
        raise TavilyInvalidResponseError(invalid_message)
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            raise TavilyInvalidResponseError(invalid_message) from None
    else:
        raise TavilyInvalidResponseError(invalid_message)
    if not math.isfinite(number) or number < 0:
        raise TavilyInvalidResponseError(invalid_message)
    return number


def _required_string(
    payload: dict[str, Any],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise TavilyInvalidResponseError(_invalid_field_message(field_name))
    return value


def _parse_result(payload: object) -> TavilySearchResult:
    if not isinstance(payload, dict):
        raise TavilyInvalidResponseError("Tavily returned an invalid result.")

    title = _required_string(payload, "title")
    url = _required_string(payload, "url")
    content = _required_string(payload, "content", allow_empty=True)
    try:
        parsed_url = urlsplit(url)
    except ValueError:
        raise TavilyInvalidResponseError(
            "Tavily returned an invalid result URL."
        ) from None
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise TavilyInvalidResponseError("Tavily returned an invalid result URL.")

    score = _number(payload.get("score"), field_name="score")
    if score > 1:
        raise TavilyInvalidResponseError("Tavily returned an invalid score field.")
    return TavilySearchResult(
        title=title,
        url=url,
        content=content,
        score=score,
    )


def _parse_response(
    response: requests.Response,
    *,
    query: str,
) -> TavilySearchResponse:
    try:
        payload = response.json()
    except (TypeError, ValueError):
        raise TavilyInvalidResponseError(
            "Tavily returned a non-JSON response."
        ) from None
    if not isinstance(payload, dict):
        raise TavilyInvalidResponseError("Tavily returned an invalid response.")

    response_query = payload.get("query")
    if not isinstance(response_query, str) or not response_query.strip():
        raise TavilyInvalidResponseError("Tavily returned an invalid query field.")

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raise TavilyInvalidResponseError("Tavily returned an invalid results field.")
    results = tuple(_parse_result(item) for item in raw_results)

    response_time = _number(payload.get("response_time"), field_name="response_time")
    request_id = _required_string(payload, "request_id")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        raise TavilyInvalidResponseError("Tavily returned an invalid usage field.")
    credit_count = usage.get("credits")
    if (
        isinstance(credit_count, bool)
        or not isinstance(credit_count, int)
        or credit_count < 0
    ):
        raise TavilyInvalidResponseError("Tavily returned an invalid credits field.")

    return TavilySearchResponse(
        query=query,
        results=results,
        response_time=response_time,
        request_id=request_id,
        credits=credit_count,
    )


def _raise_for_http_status(status_code: int) -> None:
    if 200 <= status_code < 300:
        return
    if 300 <= status_code < 400:
        raise TavilyInvalidResponseError("Tavily returned an invalid response.")
    if status_code == 400:
        raise TavilyInvalidRequestError("Tavily rejected the search request.")
    if status_code in {401, 403}:
        raise TavilyAuthenticationError("Tavily rejected the configured API key.")
    if status_code == 429:
        raise TavilyRateLimitError("Tavily rate limit reached.")
    if status_code == 432:
        raise TavilyPlanLimitError("Tavily plan usage limit reached.")
    if status_code == 433:
        raise TavilyPayGoLimitError("Tavily pay-as-you-go limit reached.")
    if status_code >= 500:
        raise TavilyUnavailableError("Tavily is temporarily unavailable.")
    if 400 <= status_code < 500:
        raise TavilyInvalidRequestError("Tavily rejected the search request.")
    raise TavilyInvalidResponseError("Tavily returned an invalid response.")


class TavilySearchClient:
    """Execute the fixed, one-credit Tavily search contract."""

    def __init__(self, api_key: str) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Tavily API key must not be empty.")
        self._api_key = api_key.strip()

    def search(self, query: object) -> TavilySearchResponse:
        """Search once without retrying or exposing provider error details."""
        normalized_query = normalize_search_query(query)
        body = {
            "query": normalized_query,
            "topic": "general",
            "country": "russia",
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_image_descriptions": False,
            "include_favicon": False,
            "include_usage": True,
            "auto_parameters": False,
            "exact_match": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = requests.post(
                SEARCH_URL,
                headers=headers,
                json=body,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise TavilyUnavailableError(
                "Tavily is temporarily unavailable."
            ) from None

        _raise_for_http_status(response.status_code)
        return _parse_response(response, query=normalized_query)

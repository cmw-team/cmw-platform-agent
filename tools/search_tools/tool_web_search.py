"""LangChain tool for safe, region-boosted Tavily web search."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from .tavily_client import (
    TavilyAuthenticationError,
    TavilyInvalidRequestError,
    TavilyInvalidResponseError,
    TavilyPayGoLimitError,
    TavilyPlanLimitError,
    TavilyRateLimitError,
    TavilySearchClient,
    TavilySearchError,
    TavilyUnavailableError,
    normalize_search_query,
)

_ERROR_MESSAGES = {
    "tavily_api_key_missing": "Tavily web search is not configured.",
    "invalid_query": "Provide a non-empty search query of at most 400 characters.",
    "invalid_request": "Tavily rejected the search request.",
    "authentication_failed": "Tavily authentication failed.",
    "rate_limit": "Tavily rate limit reached.",
    "plan_limit": "Tavily plan usage limit reached.",
    "paygo_limit": "Tavily pay-as-you-go limit reached.",
    "service_unavailable": "Tavily web search is temporarily unavailable.",
    "invalid_response": "Tavily returned an invalid response.",
}

_CLIENT_ERROR_CODES: tuple[tuple[type[TavilySearchError], str], ...] = (
    (TavilyInvalidRequestError, "invalid_request"),
    (TavilyAuthenticationError, "authentication_failed"),
    (TavilyRateLimitError, "rate_limit"),
    (TavilyPlanLimitError, "plan_limit"),
    (TavilyPayGoLimitError, "paygo_limit"),
    (TavilyUnavailableError, "service_unavailable"),
    (TavilyInvalidResponseError, "invalid_response"),
)


class WebSearchInput(BaseModel):
    """Arguments visible to the model."""

    model_config = ConfigDict(extra="forbid")

    query: StrictStr = Field(
        description=(
            "Concise web search query. Russian queries receive Russian-region "
            "ranking priority. Maximum 400 characters."
        )
    )


def _error(code: str) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": _ERROR_MESSAGES[code]},
    }


def _code_for_client_error(error: TavilySearchError) -> str:
    return next(
        (
            code
            for error_type, code in _CLIENT_ERROR_CODES
            if isinstance(error, error_type)
        ),
        "service_unavailable",
    )


@tool(
    "web_search",
    args_schema=WebSearchInput,
    return_direct=False,
)
def web_search(query: str) -> dict[str, Any]:
    """Search the current web with Russian-region ranking priority.

    Use for recent facts, current events, public sources, and information that
    may have changed since the model was trained. The result contains concise
    snippets and source URLs. It does not return full page contents.
    """
    try:
        normalized_query = normalize_search_query(query)
    except ValueError:
        return _error("invalid_query")

    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return _error("tavily_api_key_missing")

    try:
        response = TavilySearchClient(api_key).search(normalized_query)
    except TavilySearchError as error:
        return _error(_code_for_client_error(error))

    return {
        "success": True,
        "data": response.as_dict(),
        "error": None,
    }

"""Contract tests for the model-facing Tavily ``web_search`` tool."""

from __future__ import annotations

import importlib
from typing import Any, ClassVar

from pydantic import ValidationError
import pytest

API_KEY = "tvly-test-secret"


def _client_module() -> Any:
    return importlib.import_module("tools.search_tools.tavily_client")


def _tool_module() -> Any:
    return importlib.import_module("tools.search_tools.tool_web_search")


def _successful_response() -> Any:
    client = _client_module()
    return client.TavilySearchResponse(
        query="Python release",
        results=(
            client.TavilySearchResult(
                title="Download Python",
                url="https://www.python.org/downloads/",
                content="Latest stable Python release.",
                score=0.95,
            ),
        ),
        response_time=1.0,
        request_id="request-123",
        credits=1,
    )


class FakeClient:
    response: Any = None
    error: Exception | None = None
    constructed_keys: ClassVar[list[str]] = []
    queries: ClassVar[list[str]] = []

    def __init__(self, api_key: str) -> None:
        self.constructed_keys.append(api_key)

    def search(self, query: str) -> Any:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture(autouse=True)
def _reset_fake_client() -> None:
    FakeClient.response = None
    FakeClient.error = None
    FakeClient.constructed_keys = []
    FakeClient.queries = []


def test_tool_schema_exposes_only_query() -> None:
    from langchain_core.utils.function_calling import convert_to_openai_tool

    tool = _tool_module().web_search

    specification = convert_to_openai_tool(tool)

    assert tool.name == "web_search"
    assert set(specification["function"]["parameters"]["properties"]) == {"query"}


@pytest.mark.parametrize(
    "tool_input",
    [
        {},
        {"query": None},
        {"query": 123},
        {"query": "Python", "time_range": "week"},
    ],
)
def test_schema_rejects_missing_non_string_and_unknown_arguments(
    tool_input: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        _tool_module().web_search.invoke(tool_input)


def test_missing_api_key_returns_safe_error_without_constructing_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _tool_module()
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(module, "TavilySearchClient", FakeClient)

    result = module.web_search.invoke({"query": "Python release"})

    assert result == {
        "success": False,
        "data": None,
        "error": {
            "code": "tavily_api_key_missing",
            "message": "Tavily web search is not configured.",
        },
    }
    assert FakeClient.constructed_keys == []


@pytest.mark.parametrize("query", ["", "   ", "x" * 401])
def test_invalid_query_is_rejected_before_constructing_client(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
) -> None:
    module = _tool_module()
    monkeypatch.setenv("TAVILY_API_KEY", API_KEY)
    monkeypatch.setattr(module, "TavilySearchClient", FakeClient)

    result = module.web_search.invoke({"query": query})

    assert result["success"] is False
    assert result["error"]["code"] == "invalid_query"
    assert FakeClient.constructed_keys == []


def test_success_uses_trimmed_query_and_returns_stable_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _tool_module()
    monkeypatch.setenv("TAVILY_API_KEY", f"  {API_KEY}  ")
    monkeypatch.setattr(module, "TavilySearchClient", FakeClient)
    FakeClient.response = _successful_response()

    result = module.web_search.invoke({"query": "  Python release  "})

    assert FakeClient.constructed_keys == [API_KEY]
    assert FakeClient.queries == ["Python release"]
    assert result == {
        "success": True,
        "data": {
            "query": "Python release",
            "results": [
                {
                    "title": "Download Python",
                    "url": "https://www.python.org/downloads/",
                    "content": "Latest stable Python release.",
                    "score": 0.95,
                }
            ],
            "response_time": 1.0,
            "request_id": "request-123",
            "credits": 1,
        },
        "error": None,
    }
    assert API_KEY not in str(result)


@pytest.mark.parametrize(
    ("error_name", "expected_code"),
    [
        ("TavilyInvalidRequestError", "invalid_request"),
        ("TavilyAuthenticationError", "authentication_failed"),
        ("TavilyRateLimitError", "rate_limit"),
        ("TavilyPlanLimitError", "plan_limit"),
        ("TavilyPayGoLimitError", "paygo_limit"),
        ("TavilyUnavailableError", "service_unavailable"),
        ("TavilyInvalidResponseError", "invalid_response"),
    ],
)
def test_client_errors_are_mapped_to_stable_public_codes(
    monkeypatch: pytest.MonkeyPatch,
    error_name: str,
    expected_code: str,
) -> None:
    client = _client_module()
    module = _tool_module()
    monkeypatch.setenv("TAVILY_API_KEY", API_KEY)
    monkeypatch.setattr(module, "TavilySearchClient", FakeClient)
    FakeClient.error = getattr(client, error_name)("unsafe provider detail")

    result = module.web_search.invoke({"query": "Python release"})

    assert result["success"] is False
    assert result["data"] is None
    assert result["error"]["code"] == expected_code
    assert "unsafe provider detail" not in result["error"]["message"]
    assert API_KEY not in str(result)


def test_unknown_client_error_uses_safe_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client_module()
    module = _tool_module()
    monkeypatch.setenv("TAVILY_API_KEY", API_KEY)
    monkeypatch.setattr(module, "TavilySearchClient", FakeClient)
    FakeClient.error = client.TavilySearchError("unsafe provider detail")

    result = module.web_search.invoke({"query": "Python release"})

    assert result["success"] is False
    assert result["error"]["code"] == "service_unavailable"
    assert "unsafe provider detail" not in result["error"]["message"]

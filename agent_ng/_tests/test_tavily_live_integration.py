"""Opt-in smoke test for Tavily from the current runtime environment."""

from __future__ import annotations

import math
import os
from typing import Any

import pytest

_LIVE_QUERY = "официальная документация Python"


def _integration_enabled() -> bool:
    return os.getenv("CMW_TAVILY_INTEGRATION_TESTS", "").strip() == "1"


@pytest.mark.skipif(
    not _integration_enabled(),
    reason="Set CMW_TAVILY_INTEGRATION_TESTS=1 to run the live Tavily smoke test",
)
def test_registered_web_search_reaches_tavily_from_current_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Make exactly one real basic search through the registered runtime tool."""
    api_key = (os.getenv("TAVILY_API_KEY") or "").strip()
    if not api_key:
        pytest.skip("TAVILY_API_KEY is not configured")

    from agent_ng.llm_manager import LLMManager
    from agent_ng.tool_invocation import invoke_agent_tool_blocking

    monkeypatch.setenv("CMW_WEB_SEARCH_ENABLED", "true")
    monkeypatch.setenv("CMW_MCP_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_FETCH_PRICING_AT_STARTUP", "false")
    monkeypatch.setattr(
        LLMManager,
        "_update_openrouter_pricing",
        lambda _manager: None,
    )

    manager = LLMManager()
    search_tools = [
        tool
        for tool in manager.get_tools()
        if getattr(tool, "name", None) == "web_search"
    ]
    assert len(search_tools) == 1

    result = invoke_agent_tool_blocking(
        search_tools[0],
        {"query": _LIVE_QUERY},
    )
    captured = capsys.readouterr()

    assert api_key not in captured.out
    assert api_key not in captured.err
    assert api_key not in repr(result)
    assert isinstance(result, dict)
    assert result["success"] is True, result["error"]
    assert result["error"] is None

    data = result["data"]
    assert isinstance(data, dict)
    assert data["query"] == _LIVE_QUERY
    assert isinstance(data["request_id"], str)
    assert data["request_id"].strip()
    assert _is_nonnegative_finite_number(data["response_time"])
    assert data["credits"] == 1

    results = data["results"]
    assert isinstance(results, list)
    assert 1 <= len(results) <= 5
    for item in results:
        _assert_search_result(item)


def _is_nonnegative_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and value >= 0
    )


def _assert_search_result(item: Any) -> None:
    assert isinstance(item, dict)
    assert set(item) == {"title", "url", "content", "score"}
    assert isinstance(item["title"], str)
    assert item["title"].strip()
    assert isinstance(item["url"], str)
    assert item["url"].startswith(("http://", "https://"))
    assert isinstance(item["content"], str)
    assert _is_nonnegative_finite_number(item["score"])
    assert item["score"] <= 1

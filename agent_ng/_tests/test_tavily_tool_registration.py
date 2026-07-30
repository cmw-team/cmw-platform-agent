"""Contract tests for conditional Tavily tool registration in LLMManager."""

from __future__ import annotations

import os
from typing import Any

import pytest

os.environ["OPENROUTER_FETCH_PRICING_AT_STARTUP"] = "false"
os.environ["CMW_MCP_ENABLED"] = "false"

from agent_ng.llm_manager import LLMManager


def _manager(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: str | None,
    api_key: str | None,
) -> LLMManager:
    import agent_ng.llm_manager as llm_manager_module

    monkeypatch.setattr(llm_manager_module, "load_dotenv", lambda: False)
    monkeypatch.setattr(
        LLMManager,
        "_update_openrouter_pricing",
        lambda _manager: None,
    )
    monkeypatch.setenv("CMW_MCP_ENABLED", "false")
    if enabled is None:
        monkeypatch.delenv("CMW_WEB_SEARCH_ENABLED", raising=False)
    else:
        monkeypatch.setenv("CMW_WEB_SEARCH_ENABLED", enabled)
    if api_key is None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TAVILY_API_KEY", api_key)
    return LLMManager()


def _tool_names(manager: LLMManager) -> list[str]:
    return [
        name
        for tool in manager.get_tools()
        if isinstance(name := getattr(tool, "name", None), str)
    ]


@pytest.mark.parametrize("enabled", [None, "", "false", "0", "no", "off"])
def test_web_search_is_absent_when_feature_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
    enabled: str | None,
) -> None:
    manager = _manager(
        monkeypatch,
        enabled=enabled,
        api_key="tvly-test-secret",
    )

    assert "web_search" not in _tool_names(manager)


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_web_search_is_absent_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
) -> None:
    manager = _manager(monkeypatch, enabled="true", api_key=api_key)

    assert "web_search" not in _tool_names(manager)


def test_enabled_configured_web_search_is_registered_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.search_tools import web_search

    manager = _manager(
        monkeypatch,
        enabled="true",
        api_key="tvly-test-secret",
    )

    first = manager.get_tools()
    second = manager.get_tools()
    names = _tool_names(manager)
    registered = [tool for tool in first if getattr(tool, "name", None) == "web_search"]

    assert first is second
    assert registered == [web_search]
    assert names.count("web_search") == 1
    assert len(names) == len(set(names))


def test_enabling_web_search_preserves_existing_native_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(
        monkeypatch,
        enabled="true",
        api_key="tvly-test-secret",
    )

    assert {
        "get_record_values",
        "extract_presentation_slides",
        "transcribe_uploaded_media",
        "save_meeting_markdown",
        "web_search",
    } <= set(_tool_names(manager))


def test_registered_web_search_schema_exposes_only_required_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from langchain_core.utils.function_calling import convert_to_openai_tool

    manager = _manager(
        monkeypatch,
        enabled="true",
        api_key="tvly-test-secret",
    )
    search_tool = next(
        tool for tool in manager.get_tools() if getattr(tool, "name", None) == "web_search"
    )

    specification: dict[str, Any] = convert_to_openai_tool(search_tool)
    parameters = specification["function"]["parameters"]

    assert set(parameters["properties"]) == {"query"}
    assert parameters["required"] == ["query"]

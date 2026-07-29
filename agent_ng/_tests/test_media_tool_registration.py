"""Contract tests for registering native media tools in LLMManager."""

from __future__ import annotations

import os
from typing import Any

# Тесты регистрации не должны запускать фоновые HTTP-запросы или MCP-клиенты.
os.environ["OPENROUTER_FETCH_PRICING_AT_STARTUP"] = "false"
os.environ["CMW_MCP_ENABLED"] = "false"


def _manager() -> Any:
    from agent_ng.llm_manager import LLMManager

    manager = LLMManager()
    manager._invalidate_tools_cache()
    return manager


def test_get_tools_registers_media_tool_once() -> None:
    names = [getattr(tool, "name", None) for tool in _manager().get_tools()]

    assert names.count("transcribe_uploaded_media") == 1
    assert names.count("save_meeting_markdown") == 1


def test_repeated_get_tools_has_no_media_tool_duplicates() -> None:
    manager = _manager()

    first = manager.get_tools()
    second = manager.get_tools()
    first_names = [getattr(tool, "name", None) for tool in first]
    second_names = [getattr(tool, "name", None) for tool in second]

    assert first is second
    assert first_names == second_names
    assert first_names.count("transcribe_uploaded_media") == 1
    assert first_names.count("save_meeting_markdown") == 1
    assert len(first_names) == len(set(first_names))

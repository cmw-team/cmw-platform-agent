"""Tests for the ``extract_presentation_slides`` LangChain tool registration.

These tests cover stage 3 of
``.scratch/presentation-feature-implementation-handoff.md``:

* the tool is registered in :class:`agent_ng.llm_manager.LLMManager.get_tools`
  alongside the existing ``tools.templates_tools`` surface;
* the existing ``get_record_values`` tool remains available;
* tool names are unique;
* the model-facing tool schema exposes only ``source``;
* the same tool can be invoked through the standard runtime paths
  (:func:`agent_ng.tool_invocation.invoke_agent_tool_blocking` and
  :func:`agent_ng.tool_invocation.ainvoke_agent_tool`) with the agent
  injected as a runtime-only argument.

The full GenAI declaration round-trip is already covered by
``test_google_genai_tool_bind.py``.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import TYPE_CHECKING, Any
import zipfile

import pytest

if TYPE_CHECKING:
    from pathlib import Path

os.environ.setdefault("OPENROUTER_FETCH_PRICING_AT_STARTUP", "false")
os.environ.setdefault("CMW_MCP_ENABLED", "false")


def _payload_from_result(result: Any) -> dict[str, Any]:
    raw = result.content if hasattr(result, "content") else result
    return json.loads(raw) if isinstance(raw, str) else raw


def _build_minimal_pptx(path: Path, *, title: str) -> Path:
    slide = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        f"<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' "
        "xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'>"
        f"<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id='1' name=''/>"
        "<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>"
        "<p:sp><p:nvSpPr><p:cNvPr id='2' name='Shape'/>"
        "<p:cNvSpPr/><p:nvPr><p:ph type='title'/></p:nvPr></p:nvSpPr>"
        "<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>"
        f"<a:p><a:r><a:t>{title}</a:t></a:r></a:p></p:txBody></p:sp>"
        "</p:spTree></p:cSld></p:sld>"
    )
    presentation = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        "<p:sldIdLst><p:sldId id='256' r:id='rId1'/></p:sldIdLst></p:presentation>"
    )
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        'Target="slides/slide1.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ppt/presentation.xml", presentation)
        archive.writestr("ppt/_rels/presentation.xml.rels", rels)
        archive.writestr("ppt/slides/slide1.xml", slide)
    return path


class _FakeAgent:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def get_file_path(self, original_filename: str) -> str | None:
        return self.files.get(original_filename)


def _manager() -> Any:
    from agent_ng.llm_manager import LLMManager

    return LLMManager()


def _invalidate_cache(mgr: Any) -> None:
    mgr._invalidate_tools_cache()


def test_get_tools_contains_extract_presentation_slides() -> None:
    mgr = _manager()
    _invalidate_cache(mgr)
    tools = mgr.get_tools()
    names = [getattr(t, "name", None) for t in tools]
    assert names.count("extract_presentation_slides") == 1


def test_get_tools_keeps_get_record_values() -> None:
    mgr = _manager()
    _invalidate_cache(mgr)
    tools = mgr.get_tools()
    names = [getattr(t, "name", None) for t in tools]
    assert "get_record_values" in names
    assert "extract_presentation_slides" in names


def test_get_tools_has_no_duplicate_tool_names() -> None:
    mgr = _manager()
    _invalidate_cache(mgr)
    names = [
        n for n in (getattr(t, "name", None) for t in mgr.get_tools()) if n
    ]
    assert len(names) == len(set(names)), names


def test_extract_presentation_slides_openai_schema_only_exposes_source() -> None:
    from langchain_core.utils.function_calling import convert_to_openai_tool

    mgr = _manager()
    _invalidate_cache(mgr)

    presentation_tool = next(
        t for t in mgr.get_tools() if getattr(t, "name", None) ==
        "extract_presentation_slides"
    )
    spec = convert_to_openai_tool(presentation_tool)
    params = spec["function"]["parameters"]
    assert set(params["properties"].keys()) == {"source"}


def test_repeated_get_tools_returns_cached_list_without_duplication() -> None:
    mgr = _manager()
    _invalidate_cache(mgr)

    first = mgr.get_tools()
    second = mgr.get_tools()

    assert first is not second
    assert all(left is right for left, right in zip(first, second, strict=True))

    first_names = [getattr(t, "name", None) for t in first]
    second_names = [getattr(t, "name", None) for t in second]
    assert first_names == second_names
    assert len(first_names) == len(set(first_names))


@pytest.mark.asyncio
async def test_ainvoke_extract_presentation_slides_runs_with_injected_agent(
    tmp_path: Path,
) -> None:
    from agent_ng.tool_invocation import ainvoke_agent_tool

    upload = _build_minimal_pptx(tmp_path / "client.pptx", title="Client deck")
    agent = _FakeAgent({"client.pptx": str(upload)})

    mgr = _manager()
    _invalidate_cache(mgr)
    presentation_tool = next(
        t for t in mgr.get_tools() if getattr(t, "name", None) ==
        "extract_presentation_slides"
    )

    result = await ainvoke_agent_tool(
        presentation_tool, {"source": "client.pptx", "agent": agent}
    )
    payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source"] == {
        "requested": "client.pptx",
        "resolved_name": "client.pptx",
        "source_type": "uploaded",
    }
    assert payload["data"]["slide_count"] == 1


def test_invoke_blocking_extract_presentation_slides_runs_with_injected_agent(
    tmp_path: Path,
) -> None:
    from agent_ng.tool_invocation import invoke_agent_tool_blocking

    upload = _build_minimal_pptx(tmp_path / "client.pptx", title="Client deck")
    agent = _FakeAgent({"client.pptx": str(upload)})

    mgr = _manager()
    _invalidate_cache(mgr)
    presentation_tool = next(
        t for t in mgr.get_tools() if getattr(t, "name", None) ==
        "extract_presentation_slides"
    )

    result = invoke_agent_tool_blocking(
        presentation_tool, {"source": "client.pptx", "agent": agent}
    )
    payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source_type" if False else "source"] == {
        "requested": "client.pptx",
        "resolved_name": "client.pptx",
        "source_type": "uploaded",
    }


def test_invoke_blocking_extract_presentation_slides_default_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_ng.tool_invocation import invoke_agent_tool_blocking

    target = tmp_path / "default_presentations"
    target.mkdir()
    _build_minimal_pptx(target / "Comindware Platform 6.pptx", title="Product")
    _build_minimal_pptx(target / "Comindware Кейсы_1.7.pptx", title="Cases")

    from tools.presentation_tools import tool_extract_presentation_slides as mod

    monkeypatch.setattr(mod, "DEFAULT_PRESENTATIONS_DIR", target)

    mgr = _manager()
    _invalidate_cache(mgr)
    presentation_tool = next(
        t for t in mgr.get_tools() if getattr(t, "name", None) ==
        "extract_presentation_slides"
    )

    result = invoke_agent_tool_blocking(
        presentation_tool,
        {"source": "default-product-deck", "agent": _FakeAgent({})},
    )
    payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source"]["source_type"] == "default"


def test_invoke_blocking_extract_presentation_slides_file_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_ng.tool_invocation import invoke_agent_tool_blocking

    monkeypatch.setattr(
        sys.modules["tools.presentation_tools.tool_extract_presentation_slides"],
        "DEFAULT_PRESENTATIONS_DIR",
        tmp_path,
    )

    mgr = _manager()
    _invalidate_cache(mgr)
    presentation_tool = next(
        t for t in mgr.get_tools() if getattr(t, "name", None) ==
        "extract_presentation_slides"
    )

    result = invoke_agent_tool_blocking(
        presentation_tool,
        {"source": "missing.pptx", "agent": _FakeAgent({})},
    )
    payload = _payload_from_result(result)

    assert payload["success"] is False
    assert payload["error"]["code"] == "file_not_found"

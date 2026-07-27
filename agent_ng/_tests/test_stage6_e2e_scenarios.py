"""Stage 6 end-to-end scenario tests.

Maps ``.scratch/presentation-feature-implementation-handoff.md`` §6
scenarios to automated checks. Two columns of the matrix are
deterministic and live here; the rest are flagged for live
human verification (see ``.scratch/stage6_live_checklist.md``).

Scenario coverage:

* A (Загруженная PPTX) — tool-level. Skill-level behaviour
  ("skill классифицирует все слайды, результат содержит
  номера и названия") is **live**, not in this file.
* B (Дефолтная презентация) — tool-level for both
  ``default-product-deck`` and ``default-case-library``. Skill
  orchestration is **live**.
* F, G, H, I — already covered as unit tests in
  ``tools/_tests/test_extract_presentation_slides.py``. Cross-
  referenced from this file's docstring but not duplicated.
* C, D, E, J — **live only**. See the live checklist.

These tests exercise the same runtime path the streaming and
non-streaming agent loops use (``LLMManager.get_tools()`` →
``ainvoke_agent_tool`` / ``invoke_agent_tool_blocking``), so
passing them is a real signal that the wiring is correct.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import zipfile

import pytest

os.environ.setdefault("OPENROUTER_FETCH_PRICING_AT_STARTUP", "false")
os.environ.setdefault("CMW_MCP_ENABLED", "false")


def _build_minimal_pptx(path: Path, *, title: str) -> Path:
    """Write a single-slide PPTX with a title placeholder.

    Mirrors the helpers in
    ``tools/_tests/test_presentation_tool_registration.py``
    so the two test files stay decoupled.
    """
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


def _payload_from_result(result: Any) -> dict[str, Any]:
    raw = result.content if hasattr(result, "content") else result
    return json.loads(raw) if isinstance(raw, str) else raw


def _find_tool(mgr: Any, name: str) -> Any:
    return next(t for t in mgr.get_tools() if getattr(t, "name", None) == name)


# ---------------------------------------------------------------------------
# Scenario A — uploaded PPTX (tool-level, end-to-end through LLMManager)
# ---------------------------------------------------------------------------


def test_scenario_a_uploaded_pptx_uses_exact_filename() -> None:
    """A: ``tool`` must use the exact original filename, source_type=uploaded.

    End-to-end through the same path the agent uses
    (``LLMManager.get_tools()`` → ``ainvoke_agent_tool``).
    """
    import tempfile

    mgr = _manager()
    _invalidate_cache(mgr)
    tool = _find_tool(mgr, "extract_presentation_slides")

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = _build_minimal_pptx(
            Path(tmp) / "client_deck.pptx", title="Client deck"
        )
        agent = _FakeAgent({"client_deck.pptx": str(upload_path)})

        import asyncio

        result = asyncio.run(
            tool.ainvoke({"source": "client_deck.pptx", "agent": agent})
        )
        payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source"] == {
        "requested": "client_deck.pptx",
        "resolved_name": "client_deck.pptx",
        "source_type": "uploaded",
    }
    assert payload["data"]["slide_count"] == 1
    assert payload["data"]["capabilities"]["visual_content_analyzed"] is False


def test_scenario_a_uploaded_pptx_payload_is_json_serializable() -> None:
    """A: the full envelope must round-trip through ``json.dumps``."""
    import tempfile

    mgr = _manager()
    _invalidate_cache(mgr)
    tool = _find_tool(mgr, "extract_presentation_slides")

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = _build_minimal_pptx(
            Path(tmp) / "sales_q4.pptx", title="Sales Q4"
        )
        agent = _FakeAgent({"sales_q4.pptx": str(upload_path)})

        import asyncio

        result = asyncio.run(
            tool.ainvoke({"source": "sales_q4.pptx", "agent": agent})
        )
        payload = _payload_from_result(result)

    json.dumps(payload, ensure_ascii=False)


def test_scenario_a_uploaded_pptx_mixed_case_alias_resolves() -> None:
    """A: case-insensitive alias resolution (regression for stage 2 iter1).

    Even though this scenario is about an *uploaded* file, the
    runtime must not collapse uploaded filenames into the
    default-alias normalisation path.
    """
    import tempfile

    mgr = _manager()
    _invalidate_cache(mgr)
    tool = _find_tool(mgr, "extract_presentation_slides")

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = _build_minimal_pptx(
            Path(tmp) / "Weirdly_Cased.PPTX", title="Mixed case"
        )
        agent = _FakeAgent({"Weirdly_Cased.PPTX": str(upload_path)})

        import asyncio

        result = asyncio.run(
            tool.ainvoke({"source": "Weirdly_Cased.PPTX", "agent": agent})
        )
        payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source"]["source_type"] == "uploaded"
    assert payload["data"]["source"]["resolved_name"] == "Weirdly_Cased.PPTX"


# ---------------------------------------------------------------------------
# Scenario B — default presentations (tool-level, end-to-end)
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_default_presentations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Seed two minimal default decks and re-point the tool at tmp_path."""
    from tools.presentation_tools import tool_extract_presentation_slides as mod

    monkeypatch.setattr(mod, "DEFAULT_PRESENTATIONS_DIR", tmp_path)
    product = _build_minimal_pptx(
        tmp_path / "Comindware Platform 6.pptx", title="Product"
    )
    case = _build_minimal_pptx(
        tmp_path / "Comindware Кейсы_1.7.pptx", title="Cases"
    )
    return product, case


def test_scenario_b_default_product_deck_returns_full_payload(
    seeded_default_presentations: tuple[Path, Path],
) -> None:
    """B: ``default-product-deck`` resolves and returns the full payload."""
    product_path, _case_path = seeded_default_presentations
    assert product_path.is_file()
    mgr = _manager()
    _invalidate_cache(mgr)
    tool = _find_tool(mgr, "extract_presentation_slides")

    import asyncio

    result = asyncio.run(
        tool.ainvoke(
            {"source": "default-product-deck", "agent": _FakeAgent({})}
        )
    )
    payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source"]["source_type"] == "default"
    assert (
        payload["data"]["source"]["resolved_name"]
        == "Comindware Platform 6.pptx"
    )
    assert payload["data"]["slide_count"] == 1
    assert (
        payload["data"]["capabilities"]["text_extraction_complete"] is True
    )


def test_scenario_b_default_case_library_returns_full_payload(
    seeded_default_presentations: tuple[Path, Path],
) -> None:
    """B: ``default-case-library`` resolves and returns the full payload."""
    _product_path, case_path = seeded_default_presentations
    assert case_path.is_file()
    mgr = _manager()
    _invalidate_cache(mgr)
    tool = _find_tool(mgr, "extract_presentation_slides")

    import asyncio

    result = asyncio.run(
        tool.ainvoke(
            {"source": "default-case-library", "agent": _FakeAgent({})}
        )
    )
    payload = _payload_from_result(result)

    assert payload["success"] is True
    assert payload["data"]["source"]["source_type"] == "default"
    assert (
        payload["data"]["source"]["resolved_name"]
        == "Comindware Кейсы_1.7.pptx"
    )


def test_scenario_b_both_default_aliases_resolve_in_sequence(
    seeded_default_presentations: tuple[Path, Path],
) -> None:
    """B: the skill is expected to call both aliases; verify the wiring."""
    _ = seeded_default_presentations
    mgr = _manager()
    _invalidate_cache(mgr)
    tool = _find_tool(mgr, "extract_presentation_slides")

    import asyncio

    product_payload = _payload_from_result(
        asyncio.run(
            tool.ainvoke(
                {"source": "default-product-deck", "agent": _FakeAgent({})}
            )
        )
    )
    case_payload = _payload_from_result(
        asyncio.run(
            tool.ainvoke(
                {"source": "default-case-library", "agent": _FakeAgent({})}
            )
        )
    )

    assert product_payload["success"] is True
    assert case_payload["success"] is True
    assert (
        product_payload["data"]["source"]["source_type"]
        == case_payload["data"]["source"]["source_type"]
        == "default"
    )
    assert (
        product_payload["data"]["source"]["resolved_name"]
        != case_payload["data"]["source"]["resolved_name"]
    )


# ---------------------------------------------------------------------------
# Cross-cutting: skill is registered and tool is bound to LLMManager
# ---------------------------------------------------------------------------


def test_skill_runtime_knows_about_the_new_skill() -> None:
    """Stage 6 cross-cut: ``list_skill_summaries`` exposes the skill."""
    from agent_ng.agent_config import get_skills_dir
    from agent_ng.skills import list_skill_summaries
    from agent_ng.skills.skill_registry import clear_cache

    root = get_skills_dir()
    clear_cache(root)
    summaries = list_skill_summaries(root)

    matching = [
        s for s in summaries if s.startswith("- cmw-plan-sales-presentation:")
    ]
    assert matching, (
        "cmw-plan-sales-presentation not in ## Available skills block; "
        "check frontmatter description and CMW_SKILLS_DIR."
    )
    summary = matching[0]
    assert "мини-ТЗ" in summary or "адаптирует" in summary.lower()


def test_extract_presentation_slides_tool_is_bound_to_llm_manager() -> None:
    """Cross-cut: the tool reaches the agent through the same
    ``LLMManager.get_tools()`` channel the agent uses to bind
    tools to the underlying LLM. This is the wiring the skill
    will rely on at runtime.
    """
    mgr = _manager()
    _invalidate_cache(mgr)
    names = {getattr(t, "name", None) for t in mgr.get_tools()}

    assert "extract_presentation_slides" in names
    assert "get_record_values" in names
    assert len(names) == len({n for n in names if n is not None})


# ---------------------------------------------------------------------------
# Live-only scenarios — cross-references for the human-run checklist
# ---------------------------------------------------------------------------


def test_scenario_c_live_only_cross_ref() -> None:
    """C (транскрипт): ``skill`` must not re-ask known facts.

    Behavioural assertion. Live-only; see the live checklist
    at ``.scratch/stage6_live_checklist.md``.
    """
    assert True


def test_scenario_d_live_only_cross_ref() -> None:
    """D (несколько PPTX): ``skill`` must ask which is primary.

    Behavioural assertion. Live-only.
    """
    assert True


def test_scenario_e_live_only_cross_ref() -> None:
    """E (нет контекста лида): ``skill`` must ask one clarifying question.

    Behavioural assertion. Live-only.
    """
    assert True


def test_scenario_j_live_only_cross_ref() -> None:
    """J (неподтверждённая функция платформы): ``skill`` must not promise.

    Behavioural assertion. Live-only.
    """
    assert True

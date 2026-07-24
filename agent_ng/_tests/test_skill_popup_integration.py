"""Tests for the slash-command popup integration in chat_tab."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(
    root: Path,
    folder: str,
    *,
    name: str | None = None,
    description: str = "",
) -> None:
    skill_dir = root / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    parts = ["---"]
    if name is not None:
        parts.append(f"name: {name}")
    if description:
        parts.append(f"description: {description}")
    parts.append("---")
    parts.append("body")
    (skill_dir / "SKILL.md").write_text("\n".join(parts) + "\n", encoding="utf-8")


def _multimodal_data(text: str = "", files: list | None = None):
    """Build a real ``MultimodalData`` like Gradio's preprocess produces."""
    from gradio.components.multimodal_textbox import (
        FileData,
        MultimodalData,
    )

    return MultimodalData(
        text=text,
        files=[FileData(path=p) if isinstance(p, str) else p for p in (files or [])],
    )


def test_get_popup_initial_choices_returns_pairs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform skill")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_initial_choices

    choices = _skill_popup_initial_choices()
    assert ("cmw — CMW Platform skill", "cmw") in choices


def test_get_popup_initial_choices_empty_when_no_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    from agent_ng.tabs.chat_tab import _skill_popup_initial_choices

    assert _skill_popup_initial_choices() == []


def test_extract_text_handles_multimodal_data() -> None:
    """Real Gradio preprocess produces a ``MultimodalData`` Pydantic model."""
    from agent_ng.tabs.chat_tab import _extract_text

    md = _multimodal_data(text="/cmw")
    assert _extract_text(md) == "/cmw"


def test_extract_text_handles_empty_multimodal_data() -> None:
    from agent_ng.tabs.chat_tab import _extract_text

    md = _multimodal_data(text="")
    assert _extract_text(md) == ""


def test_extract_text_handles_dict() -> None:
    from agent_ng.tabs.chat_tab import _extract_text

    assert _extract_text({"text": "/cmw", "files": []}) == "/cmw"
    assert _extract_text({"text": "", "files": ["x"]}) == ""
    assert _extract_text({"files": []}) == ""


def test_extract_text_handles_str() -> None:
    from agent_ng.tabs.chat_tab import _extract_text

    assert _extract_text("/cmw") == "/cmw"
    assert _extract_text("hello") == "hello"


def test_extract_text_handles_none() -> None:
    from agent_ng.tabs.chat_tab import _extract_text

    assert _extract_text(None) == ""


def test_popup_input_handler_shows_when_slash_multimodal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler(_multimodal_data(text="/"))
    assert isinstance(out, dict)
    assert out["visible"] is True
    labels = [c[0] for c in out["choices"]]
    assert any("cmw" in label for label in labels)


def test_popup_input_handler_shows_when_slash_str(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler("/")
    assert out["visible"] is True


def test_popup_input_handler_shows_when_slash_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler({"text": "/", "files": []})
    assert out["visible"] is True


def test_popup_input_handler_filters_by_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform")
    _write_skill(tmp_path, "docs", description="Documentation")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler(_multimodal_data(text="/cmw"))
    assert out["visible"] is True
    values = {c[1] for c in out["choices"]}
    assert values == {"cmw"}


def test_popup_input_handler_hides_when_no_slash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler(_multimodal_data(text="hello world"))
    assert out["visible"] is False


def test_popup_input_handler_hides_for_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler(_multimodal_data(text="/api/v1/foo"))
    assert out["visible"] is False


def test_popup_input_handler_hides_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    monkeypatch.setenv("CMW_SKILLS_ENABLED", "false")

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler(_multimodal_data(text="/"))
    assert out["visible"] is False


def test_popup_input_handler_handles_none_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler(None)
    assert out["visible"] is False


def test_popup_input_handler_returns_gr_update_dict() -> None:
    """Return value is a ``gr.update`` dict, never a new ``Dropdown`` instance.

    Gradio routes the return through ``postprocess``, which expects either a
    raw value (str/int/float) or an update dict. Returning a new
    ``Dropdown`` instance silently fails.
    """
    import gradio as gr

    from agent_ng.tabs.chat_tab import _skill_popup_input_handler

    out = _skill_popup_input_handler("/")
    assert isinstance(out, dict)
    assert out.get("__type__") == "update"
    assert "choices" in out
    assert "visible" in out


def test_popup_select_handler_inserts_value_and_hides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.tabs.chat_tab import _skill_popup_select_handler

    textbox_update, popup_update = _skill_popup_select_handler("cmw")
    assert textbox_update["value"] == {"text": "/cmw ", "files": []}
    assert popup_update["visible"] is False
    # Both must be gr.update dicts.
    assert textbox_update.get("__type__") == "update"
    assert popup_update.get("__type__") == "update"


def test_popup_select_handler_empty_value_passes_through() -> None:
    from agent_ng.tabs.chat_tab import _skill_popup_select_handler

    textbox_update, popup_update = _skill_popup_select_handler("")
    assert textbox_update["value"] == {"text": "", "files": []}
    assert popup_update["visible"] is False


def test_chat_tab_has_create_chat_interface() -> None:
    from agent_ng.tabs.chat_tab import ChatTab

    tab = ChatTab(event_handlers={}, language="en")
    assert hasattr(tab, "_create_chat_interface")

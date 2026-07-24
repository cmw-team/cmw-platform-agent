"""Tests for the chat input slash-command preprocessor."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_ng.skills.chat_preprocessor import preprocess_chat_input


def _write_skill(
    root: Path, folder: str, *, name: str | None = None, description: str = "", body: str = "body"
) -> None:
    skill_dir = root / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    parts = ["---"]
    if name is not None:
        parts.append(f"name: {name}")
    if description:
        parts.append(f"description: {description}")
    parts.append("---")
    parts.append(body)
    (skill_dir / "SKILL.md").write_text("\n".join(parts) + "\n", encoding="utf-8")


def test_passthrough_when_no_slash(tmp_path: Path) -> None:
    out = preprocess_chat_input("hello world", tmp_path)
    assert out.passthrough is True
    assert out.user_text == "hello world"
    assert out.skill_activated is None
    assert out.error is None


def test_passthrough_for_url_like_input(tmp_path: Path) -> None:
    out = preprocess_chat_input("/api/v1/chat", tmp_path)
    assert out.passthrough is True
    assert out.user_text == "/api/v1/chat"


def test_known_skill_loads_and_strips_prefix(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", body="cmw body content")
    out = preprocess_chat_input("/cmw list apps", tmp_path)
    assert out.passthrough is False
    assert out.skill_activated == "cmw"
    assert out.user_text == "list apps"
    assert out.error is None


def test_known_skill_with_empty_suffix(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", body="cmw body")
    out = preprocess_chat_input("/cmw", tmp_path)
    assert out.passthrough is False
    assert out.skill_activated == "cmw"
    assert out.user_text == ""


def test_unknown_skill_yields_inline_error(tmp_path: Path) -> None:
    out = preprocess_chat_input("/ghost list", tmp_path)
    assert out.passthrough is False
    assert out.error is not None
    assert "Unknown skill" in out.error
    assert "'ghost'" in out.error
    assert out.skill_activated is None
    assert out.user_text == ""  # no LLM call


def test_unknown_skill_error_lists_available(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", description="cmw desc")
    _write_skill(tmp_path, "other", description="other desc")
    out = preprocess_chat_input("/ghost list", tmp_path)
    assert "cmw" in out.error
    assert "other" in out.error


def test_skill_load_truncation_message(tmp_path: Path) -> None:
    _write_skill(tmp_path, "huge", body="x" * 200_000)
    out = preprocess_chat_input(
        "/huge do something", tmp_path, max_chars=1000
    )
    assert out.skill_activated == "huge"
    assert out.user_text == "do something"


def test_missing_skills_dir_returns_passthrough() -> None:
    out = preprocess_chat_input("hello", Path("/does/not/exist"))
    assert out.passthrough is True
    assert out.user_text == "hello"


def test_disabled_flag_returns_passthrough(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", body="body")
    out = preprocess_chat_input("/cmw hi", tmp_path, enabled=False)
    assert out.passthrough is True
    assert out.user_text == "/cmw hi"  # not stripped

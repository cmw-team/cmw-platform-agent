"""Tests for the system-prompt skill section builder."""

from __future__ import annotations

from pathlib import Path

from agent_ng.prompts import build_skill_prompt_section


def _write_skill(
    root: Path, folder: str, *, name: str | None = None, description: str = ""
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


def test_empty_when_no_skills(tmp_path: Path) -> None:
    section = build_skill_prompt_section(tmp_path)
    assert section == ""


def test_lists_one_skill_per_line(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw-platform", description="Use with CMW Platform.")
    section = build_skill_prompt_section(tmp_path)
    assert "## Available skills" in section
    assert "- cmw-platform: Use with CMW Platform." in section
    assert "load_skill" in section
    assert "/" in section  # slash command hint


def test_lists_multiple_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", description="first")
    _write_skill(tmp_path, "beta", description="second")
    section = build_skill_prompt_section(tmp_path)
    assert "- alpha: first" in section
    assert "- beta: second" in section


def test_missing_skill_dir_returns_empty(tmp_path: Path) -> None:
    section = build_skill_prompt_section(tmp_path / "does-not-exist")
    assert section == ""


def test_skill_with_blank_description_still_listed(tmp_path: Path) -> None:
    _write_skill(tmp_path, "no-desc", description="")
    section = build_skill_prompt_section(tmp_path)
    assert "## Available skills" in section
    assert "- no-desc" in section

"""Tests for the skill registry that discovers SKILL.md files on disk."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_ng.skills.skill_registry import (
    SkillEntry,
    discover_skills,
    find_skill,
    list_skill_summaries,
)


def _write_skill(
    root: Path,
    folder: str,
    *,
    name: str | None = None,
    description: str = "",
    body: str = "body",
    with_references: bool = False,
) -> Path:
    skill_dir = root / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    if with_references:
        (skill_dir / "references").mkdir(exist_ok=True)
        (skill_dir / "references" / "guide.md").write_text("ref body", encoding="utf-8")
    parts = ["---"]
    if name is not None:
        parts.append(f"name: {name}")
    if description:
        parts.append(f"description: {description}")
    parts.append("---")
    parts.append(body)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return skill_md


def test_discovers_one_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw-platform", description="Use with CMW Platform.")
    skills = discover_skills(tmp_path)
    assert len(skills) == 1
    s = skills[0]
    assert isinstance(s, SkillEntry)
    assert s.name == "cmw-platform"
    assert s.description == "Use with CMW Platform."
    assert s.path == tmp_path / "cmw-platform" / "SKILL.md"


def test_discovers_multiple_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", description="Alpha skill.")
    _write_skill(tmp_path, "beta", description="Beta skill.")
    names = {s.name for s in discover_skills(tmp_path)}
    assert names == {"alpha", "beta"}


def test_empty_or_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert discover_skills(tmp_path) == []
    missing = tmp_path / "does-not-exist"
    assert discover_skills(missing) == []


def test_falls_back_to_folder_name_when_no_frontmatter(tmp_path: Path) -> None:
    (tmp_path / "no-frontmatter").mkdir()
    (tmp_path / "no-frontmatter" / "SKILL.md").write_text(
        "no frontmatter at all\n", encoding="utf-8"
    )
    skills = discover_skills(tmp_path)
    assert len(skills) == 1
    assert skills[0].name == "no-frontmatter"
    assert skills[0].description == ""


def test_falls_back_to_folder_name_when_name_missing(tmp_path: Path) -> None:
    _write_skill(tmp_path, "folder-name", description="only desc")
    skills = discover_skills(tmp_path)
    assert skills[0].name == "folder-name"


def test_finds_references_dir(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    s = discover_skills(tmp_path)[0]
    assert list(s.references) == ["guide.md"]


def test_ignores_dirs_without_skill_md(tmp_path: Path) -> None:
    (tmp_path / "junk").mkdir()
    (tmp_path / "junk" / "README.md").write_text("not a skill", encoding="utf-8")
    _write_skill(tmp_path, "real", description="real skill")
    names = {s.name for s in discover_skills(tmp_path)}
    assert names == {"real"}


def test_ignores_hidden_directories(tmp_path: Path) -> None:
    _write_skill(tmp_path, ".hidden", description="hidden skill")
    _write_skill(tmp_path, "visible", description="visible skill")
    names = {s.name for s in discover_skills(tmp_path)}
    assert names == {"visible"}


def test_find_skill_returns_entry_or_none(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw-platform", description="d")
    s = find_skill(tmp_path, "cmw-platform")
    assert s is not None
    assert s.name == "cmw-platform"
    assert find_skill(tmp_path, "nope") is None


def test_list_skill_summaries_one_line_per_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", description="first")
    _write_skill(tmp_path, "beta", description="second")
    lines = list_skill_summaries(tmp_path)
    assert "- alpha: first" in lines
    assert "- beta: second" in lines
    assert len(lines) == 2


def test_list_skill_summaries_skips_blank_descriptions(tmp_path: Path) -> None:
    _write_skill(tmp_path, "no-desc", description="")
    _write_skill(tmp_path, "with-desc", description="here")
    lines = list_skill_summaries(tmp_path)
    assert "- no-desc:" in lines
    assert "- with-desc: here" in lines


def test_duplicate_name_logs_and_keeps_first(tmp_path: Path, caplog) -> None:
    import logging

    _write_skill(tmp_path, "a", name="dup", description="first")
    _write_skill(tmp_path, "b", name="dup", description="second")
    with caplog.at_level(logging.WARNING, logger="agent_ng.skills.skill_registry"):
        skills = discover_skills(tmp_path)
    assert len(skills) == 1
    assert skills[0].description == "first"
    assert any("duplicate" in rec.message.lower() for rec in caplog.records)

"""Tests for the slash-command popup choice list."""

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


def test_build_choices_empty_when_dir_missing(tmp_path: Path) -> None:
    from agent_ng.skills.skill_popup import build_popup_choices

    assert build_popup_choices(tmp_path / "missing") == []


def test_build_choices_empty_when_no_skills(tmp_path: Path) -> None:
    from agent_ng.skills.skill_popup import build_popup_choices

    assert build_popup_choices(tmp_path) == []


def test_build_choices_one_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform skill")
    from agent_ng.skills.skill_popup import build_popup_choices

    choices = build_popup_choices(tmp_path)
    assert choices == [("cmw — CMW Platform skill", "cmw")]


def test_build_choices_includes_description(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", description="first skill")
    _write_skill(tmp_path, "beta", description="second skill")
    from agent_ng.skills.skill_popup import build_popup_choices

    choices = build_popup_choices(tmp_path)
    by_value = {v: lbl for lbl, v in choices}
    assert by_value["alpha"] == "alpha — first skill"
    assert by_value["beta"] == "beta — second skill"


def test_build_choices_truncates_long_descriptions(tmp_path: Path) -> None:
    long_desc = "x" * 200
    _write_skill(tmp_path, "cmw", description=long_desc)
    from agent_ng.skills.skill_popup import build_popup_choices

    choices = build_popup_choices(tmp_path)
    label, _ = choices[0]
    # Truncated to ~60 chars + ellipsis.
    assert "..." in label
    assert len(label) < 100


def test_build_choices_blank_description(tmp_path: Path) -> None:
    _write_skill(tmp_path, "no-desc", description="")
    from agent_ng.skills.skill_popup import build_popup_choices

    choices = build_popup_choices(tmp_path)
    assert choices == [("no-desc", "no-desc")]


def test_filter_empty_query_returns_all() -> None:
    from agent_ng.skills.skill_popup import filter_popup_choices

    choices = [("alpha — a", "alpha"), ("beta — b", "beta")]
    assert filter_popup_choices(choices, "") == choices
    assert filter_popup_choices(choices, "   ") == choices


def test_filter_strips_leading_slash() -> None:
    from agent_ng.skills.skill_popup import filter_popup_choices

    choices = [("cmw-platform — CMW", "cmw-platform"), ("other — o", "other")]
    filtered = filter_popup_choices(choices, "/cmw")
    assert filtered == [("cmw-platform — CMW", "cmw-platform")]


def test_filter_substring_case_insensitive() -> None:
    from agent_ng.skills.skill_popup import filter_popup_choices

    choices = [
        ("cmw-platform — CMW Platform skill", "cmw-platform"),
        ("cmw-rag — Retrieval Augmented", "cmw-rag"),
        ("other — something else", "other"),
    ]
    filtered = filter_popup_choices(choices, "CMW")
    assert {v for _, v in filtered} == {"cmw-platform", "cmw-rag"}


def test_filter_matches_description() -> None:
    from agent_ng.skills.skill_popup import filter_popup_choices

    choices = [
        ("alpha — documentation", "alpha"),
        ("beta — research", "beta"),
    ]
    filtered = filter_popup_choices(choices, "doc")
    assert filtered == [("alpha — documentation", "alpha")]


def test_filter_no_matches_returns_empty() -> None:
    from agent_ng.skills.skill_popup import filter_popup_choices

    choices = [("alpha — a", "alpha"), ("beta — b", "beta")]
    assert filter_popup_choices(choices, "/xyz") == []


def test_should_show_popup_only_when_starts_with_slash() -> None:
    from agent_ng.skills.skill_popup import should_show_popup

    assert should_show_popup("/cmw") is True
    assert should_show_popup("/") is True
    assert should_show_popup("  /cmw") is True
    assert should_show_popup("/api/v1/foo") is False
    assert should_show_popup("hello") is False
    assert should_show_popup("") is False
    assert should_show_popup("see /etc/hosts") is False


def test_format_label_truncation() -> None:
    from agent_ng.skills.skill_popup import _format_label

    # 100 chars > 60, kept to 57 + "..." = 60 total.
    assert _format_label("a", "x" * 100) == "a — " + "x" * 57 + "..."
    assert _format_label("a", "short") == "a — short"
    assert _format_label("a", "") == "a"


def test_should_show_popup_strict_path_rule() -> None:
    """``/api/v1/foo`` should NOT show the popup because the next char after
    the name is a ``/`` not a whitespace — same rule as the slash parser."""
    from agent_ng.skills.skill_popup import should_show_popup

    assert should_show_popup("/api/v1/foo") is False  # path-like
    assert should_show_popup("/etc/hosts") is False  # path-like
    assert should_show_popup("/2024/r") is False  # digit-start
    assert should_show_popup("/cmw") is True  # valid skill command
    assert should_show_popup("/cmw list") is True  # valid skill command with suffix
    assert should_show_popup("see /etc/hosts") is False  # not at start
    assert should_show_popup("hello") is False  # no slash


def test_format_label_handles_normal_length() -> None:
    from agent_ng.skills.skill_popup import _format_label

    label = _format_label("cmw", "Use CMW Platform tools")
    assert label == "cmw — Use CMW Platform tools"

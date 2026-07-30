"""Tests for the LangChain ``StructuredTool`` factory in ``skill_tool.py``."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool
import pytest

from agent_ng.skills.skill_tool import build_skill_tools, get_active_skills

pytestmark = pytest.mark.usefixtures("clear_skill_state")


@pytest.fixture
def clear_skill_state() -> None:
    """Per-test reset of the in-process active-skill state."""
    from agent_ng.skills import skill_tool

    skill_tool._active_skills.clear()
    yield
    skill_tool._active_skills.clear()


def _write_skill(
    root: Path,
    folder: str,
    *,
    name: str | None = None,
    description: str = "",
    body: str = "default body",
    with_references: bool = False,
) -> None:
    skill_dir = root / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    if with_references:
        refs = skill_dir / "references"
        refs.mkdir(exist_ok=True)
        (refs / "guide.md").write_text("ref body here", encoding="utf-8")
        (refs / "deep.md").write_text("deeper", encoding="utf-8")
    parts = ["---"]
    if name is not None:
        parts.append(f"name: {name}")
    if description:
        parts.append(f"description: {description}")
    parts.append("---")
    parts.append(body)
    (skill_dir / "SKILL.md").write_text("\n".join(parts) + "\n", encoding="utf-8")


def _invoke(tool: BaseTool, **kwargs):
    return tool.invoke(kwargs)


def test_returns_three_tools(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", description="d")
    tools = build_skill_tools(tmp_path)
    names = {t.name for t in tools}
    assert names == {"load_skill", "load_skill_reference", "deactivate_skill"}


def test_load_skill_returns_body_and_activates(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", description="d", body="hello body")
    tools = build_skill_tools(tmp_path)
    load_skill = next(t for t in tools if t.name == "load_skill")

    result = _invoke(load_skill, name="cmw")

    assert "hello body" in result
    assert "# Active skill: cmw" in result
    assert "cmw" in get_active_skills()


def test_load_skill_unknown_returns_error_string(tmp_path: Path) -> None:
    tools = build_skill_tools(tmp_path)
    load_skill = next(t for t in tools if t.name == "load_skill")

    result = _invoke(load_skill, name="does-not-exist")

    assert "Unknown skill" in result
    assert "does-not-exist" in result
    assert get_active_skills() == set()


def test_load_skill_is_idempotent(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", body="body content")
    tools = build_skill_tools(tmp_path)
    load_skill = next(t for t in tools if t.name == "load_skill")

    _invoke(load_skill, name="cmw")
    _invoke(load_skill, name="cmw")

    # Only one entry in the active set.
    assert get_active_skills() == {"cmw"}


def test_load_skill_two_skills_both_active(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", body="alpha body")
    _write_skill(tmp_path, "beta", body="beta body")
    tools = build_skill_tools(tmp_path)
    load_skill = next(t for t in tools if t.name == "load_skill")

    _invoke(load_skill, name="alpha")
    _invoke(load_skill, name="beta")

    assert get_active_skills() == {"alpha", "beta"}


def test_load_skill_truncates_large_body(tmp_path: Path) -> None:
    long_body = "x" * 200_000
    _write_skill(tmp_path, "huge", body=long_body, with_references=True)
    tools = build_skill_tools(tmp_path, max_chars=1000)
    load_skill = next(t for t in tools if t.name == "load_skill")

    result = _invoke(load_skill, name="huge")

    assert "x" * 1000 not in result  # body was truncated
    assert "guide.md" in result
    assert "load_skill_reference" in result
    assert "huge" in get_active_skills()  # still considered active


def test_load_skill_reference_returns_file(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    tools = build_skill_tools(tmp_path)
    load_ref = next(t for t in tools if t.name == "load_skill_reference")

    result = _invoke(load_ref, skill_name="cmw", reference_path="guide.md")

    assert "ref body here" in result


def test_load_skill_reference_unknown_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    tools = build_skill_tools(tmp_path)
    load_ref = next(t for t in tools if t.name == "load_skill_reference")

    result = _invoke(load_ref, skill_name="nope", reference_path="guide.md")

    assert "Unknown skill" in result


def test_load_skill_reference_missing_file(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    tools = build_skill_tools(tmp_path)
    load_ref = next(t for t in tools if t.name == "load_skill_reference")

    result = _invoke(load_ref, skill_name="cmw", reference_path="missing.md")

    assert "not found" in result.lower() or "missing" in result.lower()


def test_load_skill_reference_path_traversal_blocked(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    tools = build_skill_tools(tmp_path)
    load_ref = next(t for t in tools if t.name == "load_skill_reference")

    result = _invoke(
        load_ref, skill_name="cmw", reference_path="../../some_secret.txt"
    )

    assert "escapes" in result.lower() or "not found" in result.lower()


def test_deactivate_skill_removes_from_active(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha", body="alpha body")
    _write_skill(tmp_path, "beta", body="beta body")
    tools = build_skill_tools(tmp_path)
    load_skill = next(t for t in tools if t.name == "load_skill")
    deactivate = next(t for t in tools if t.name == "deactivate_skill")

    _invoke(load_skill, name="alpha")
    _invoke(load_skill, name="beta")
    assert get_active_skills() == {"alpha", "beta"}

    result = _invoke(deactivate, name="alpha")

    assert get_active_skills() == {"beta"}
    assert "alpha" in result


def test_deactivate_unknown_skill_returns_message(tmp_path: Path) -> None:
    tools = build_skill_tools(tmp_path)
    deactivate = next(t for t in tools if t.name == "deactivate_skill")

    result = _invoke(deactivate, name="ghost")

    assert "ghost" in result
    assert "not active" in result.lower() or "no" in result.lower()


def test_tools_have_pydantic_schemas(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    tools = build_skill_tools(tmp_path)
    by_name = {t.name: t for t in tools}
    assert "name" in by_name["load_skill"].args
    assert "skill_name" in by_name["load_skill_reference"].args
    assert "reference_path" in by_name["load_skill_reference"].args
    assert "name" in by_name["deactivate_skill"].args


def test_tools_have_descriptions(tmp_path: Path) -> None:
    _write_skill(tmp_path, "cmw", with_references=True)
    tools = build_skill_tools(tmp_path)
    for tool in tools:
        assert tool.description
        assert len(tool.description) > 20


def test_load_skill_description_requires_separate_model_turn() -> None:
    tools = build_skill_tools(Path(__file__).parent)
    load_skill = next(t for t in tools if t.name == "load_skill")

    assert "call this tool by itself" in load_skill.description.lower()
    assert "wait for the result" in load_skill.description.lower()

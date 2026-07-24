"""Tests for the SKILL.md frontmatter parser (stdlib-only, no PyYAML)."""

from __future__ import annotations

import pytest

from agent_ng.skills.frontmatter import parse_frontmatter


def test_no_frontmatter_returns_empty_meta_full_body() -> None:
    body = "# Just a title\n\nSome content here.\n"
    meta, parsed = parse_frontmatter(body)
    assert meta == {}
    assert parsed == body


def test_parses_simple_key_value_pairs() -> None:
    text = (
        "---\n"
        "name: cmw-platform\n"
        "description: Use when working with CMW Platform.\n"
        "---\n"
        "# CMW Platform Skill\n\nBody text.\n"
    )
    meta, body = parse_frontmatter(text)
    assert meta["name"] == "cmw-platform"
    assert meta["description"] == "Use when working with CMW Platform."
    assert body.startswith("# CMW Platform Skill")
    assert "Body text." in body


def test_parses_list_value() -> None:
    text = (
        "---\n"
        "name: x\n"
        "tags:\n"
        "  - alpha\n"
        "  - beta\n"
        "---\n"
        "body\n"
    )
    meta, body = parse_frontmatter(text)
    assert meta["tags"] == ["alpha", "beta"]
    assert body == "body\n"


def test_quoted_values_are_unquoted() -> None:
    text = (
        "---\n"
        "name: 'cmw-platform'\n"
        'description: "double quoted"\n'
        "---\n"
        "body\n"
    )
    meta, _ = parse_frontmatter(text)
    assert meta["name"] == "cmw-platform"
    assert meta["description"] == "double quoted"


def test_comments_in_frontmatter_are_ignored() -> None:
    text = (
        "---\n"
        "# this is a comment\n"
        "name: a\n"
        "# another comment\n"
        "description: b\n"
        "---\n"
        "body\n"
    )
    meta, _ = parse_frontmatter(text)
    assert meta == {"name": "a", "description": "b"}


def test_unclosed_frontmatter_falls_back_to_full_body() -> None:
    text = "name: x\ndescription: y\n# body but no closing ---\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_empty_frontmatter_block() -> None:
    text = "---\n---\n# body\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == "# body\n"


def test_blank_lines_inside_frontmatter_are_skipped() -> None:
    text = (
        "---\n"
        "name: a\n"
        "\n"
        "description: b\n"
        "---\n"
        "body\n"
    )
    meta, _ = parse_frontmatter(text)
    assert meta == {"name": "a", "description": "b"}


def test_trailing_whitespace_stripped_from_keys_and_values() -> None:
    text = "---\n  name  :   spaced  \n---\nbody\n"
    meta, _ = parse_frontmatter(text)
    assert meta == {"name": "spaced"}


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n",
        "---\n",
        "---\n---\n",
    ],
)
def test_empty_or_minimal_inputs(text: str) -> None:
    meta, body = parse_frontmatter(text)
    assert isinstance(meta, dict)
    assert isinstance(body, str)

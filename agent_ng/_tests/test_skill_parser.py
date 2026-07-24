"""Tests for the ``/<skill-name>`` slash-command parser."""

from __future__ import annotations

import pytest

from agent_ng.skills.skill_parser import SlashCommand, parse_slash_command


def test_simple_command_with_suffix() -> None:
    cmd = parse_slash_command("/cmw-platform list my apps")
    assert isinstance(cmd, SlashCommand)
    assert cmd.name == "cmw-platform"
    assert cmd.suffix == "list my apps"
    assert cmd.full == "/cmw-platform list my apps"


def test_command_with_empty_suffix() -> None:
    cmd = parse_slash_command("/cmw-platform")
    assert cmd is not None
    assert cmd.name == "cmw-platform"
    assert cmd.suffix == ""


def test_command_with_leading_whitespace() -> None:
    cmd = parse_slash_command("  /cmw-platform hi")
    assert cmd is not None
    assert cmd.name == "cmw-platform"
    assert cmd.suffix == "hi"


def test_no_leading_slash_returns_none() -> None:
    assert parse_slash_command("hello world") is None
    assert parse_slash_command("cmw-platform list apps") is None


def test_empty_or_whitespace_only_input_returns_none() -> None:
    assert parse_slash_command("") is None
    assert parse_slash_command("   ") is None
    assert parse_slash_command("\n\t") is None


def test_url_like_input_is_not_a_command() -> None:
    # Second char must be a letter to be treated as a skill command.
    assert parse_slash_command("/api/v1/chat") is None
    assert parse_slash_command("/v1/something") is None


def test_posix_absolute_path_is_not_a_command() -> None:
    assert parse_slash_command("/usr/bin/python") is None
    assert parse_slash_command("/etc/hosts") is None


def test_single_letter_skill_name() -> None:
    cmd = parse_slash_command("/a hi")
    assert cmd is not None
    assert cmd.name == "a"
    assert cmd.suffix == "hi"


def test_dots_and_underscores_in_name() -> None:
    cmd = parse_slash_command("/foo.bar_baz-1 hi")
    assert cmd is not None
    assert cmd.name == "foo.bar_baz-1"


def test_command_at_start_of_multiline() -> None:
    text = "/cmw-platform first line\nsecond line"
    cmd = parse_slash_command(text)
    assert cmd is not None
    assert cmd.name == "cmw-platform"
    assert cmd.suffix == "first line\nsecond line"


def test_command_in_middle_of_text_is_not_detected() -> None:
    # Only a slash at the start (after trim) counts; "/foo" mid-sentence is body.
    assert parse_slash_command("please run /cmw-platform now") is None


def test_digit_start_is_not_a_command() -> None:
    # Avoid matching things like "/2024/report".
    assert parse_slash_command("/2024/report") is None


def test_suffix_preserves_unicode() -> None:
    cmd = parse_slash_command("/cmw-platform покажи заявки")
    assert cmd is not None
    assert cmd.suffix == "покажи заявки"


@pytest.mark.parametrize(
    "raw,expected_name,expected_suffix",
    [
        ("/x", "x", ""),
        ("/x ", "x", ""),
        ("/x y z", "x", "y z"),
    ],
)
def test_parametrized_simple_cases(
    raw: str, expected_name: str, expected_suffix: str
) -> None:
    cmd = parse_slash_command(raw)
    assert cmd is not None
    assert cmd.name == expected_name
    assert cmd.suffix == expected_suffix

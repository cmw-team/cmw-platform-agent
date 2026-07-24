"""Tests for the skill-related helpers in ``agent_config``."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_get_skills_dir_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CMW_SKILLS_DIR", raising=False)
    from agent_ng.agent_config import get_skills_dir

    d = get_skills_dir()
    # Default is <repo>/.agents/skills — i.e. parent of agent_ng/ then .agents/skills.
    assert d.name == "skills"
    assert d.parent.name == ".agents"
    assert d.exists()  # the repo has this directory


def test_get_skills_dir_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    from agent_ng.agent_config import get_skills_dir

    assert get_skills_dir() == tmp_path.resolve()


def test_get_skills_dir_env_override_expands_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CMW_SKILLS_DIR", "~/_skills_test")
    from agent_ng.agent_config import get_skills_dir

    assert get_skills_dir() == Path.home() / "_skills_test"


def test_get_skills_enabled_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CMW_SKILLS_ENABLED", raising=False)
    from agent_ng.agent_config import get_skills_enabled

    assert get_skills_enabled() is True


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0", False),
        ("false", False),
        ("False", False),
        ("no", False),
        ("off", False),
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
    ],
)
def test_get_skills_enabled_env_values(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("CMW_SKILLS_ENABLED", raw)
    from agent_ng.agent_config import get_skills_enabled

    assert get_skills_enabled() is expected


def test_get_skill_max_body_chars_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CMW_SKILL_MAX_BODY_CHARS", raising=False)
    from agent_ng.agent_config import get_skill_max_body_chars

    assert get_skill_max_body_chars() == 60_000


def test_get_skill_max_body_chars_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CMW_SKILL_MAX_BODY_CHARS", "12345")
    from agent_ng.agent_config import get_skill_max_body_chars

    assert get_skill_max_body_chars() == 12_345


def test_get_skill_max_body_chars_invalid_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CMW_SKILL_MAX_BODY_CHARS", "not-a-number")
    from agent_ng.agent_config import get_skill_max_body_chars

    assert get_skill_max_body_chars() == 60_000

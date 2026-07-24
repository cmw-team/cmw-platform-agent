"""Tests for the per-session active-skill state."""

from __future__ import annotations

from agent_ng.skills.skill_session import SkillSession


def test_new_session_is_empty() -> None:
    s = SkillSession()
    assert s.active_names() == ()
    assert not s.is_active("cmw")


def test_activate_records_body() -> None:
    s = SkillSession()
    s.activate("cmw", "body here")
    assert s.is_active("cmw")
    assert s.active_names() == ("cmw",)
    assert s.active["cmw"] == "body here"


def test_activate_replaces_existing_body() -> None:
    s = SkillSession()
    s.activate("cmw", "old")
    s.activate("cmw", "new")
    assert s.active["cmw"] == "new"
    assert s.active_names() == ("cmw",)


def test_deactivate_removes_skill() -> None:
    s = SkillSession()
    s.activate("cmw", "body")
    assert s.deactivate("cmw") is True
    assert not s.is_active("cmw")
    assert s.deactivate("cmw") is False  # already gone


def test_active_names_preserves_insertion_order() -> None:
    s = SkillSession()
    s.activate("alpha", "a")
    s.activate("beta", "b")
    s.activate("gamma", "c")
    assert s.active_names() == ("alpha", "beta", "gamma")


def test_as_system_messages_uses_active_skill_header() -> None:
    s = SkillSession()
    s.activate("cmw", "body content")
    msgs = s.as_system_messages()
    assert len(msgs) == 1
    role, content = msgs[0]
    assert role == "system"
    assert content.startswith("# Active skill: cmw")
    assert "body content" in content


def test_as_system_messages_is_empty_when_no_active_skills() -> None:
    s = SkillSession()
    assert s.as_system_messages() == []


def test_clear_removes_everything() -> None:
    s = SkillSession()
    s.activate("cmw", "body")
    s.clear()
    assert s.active_names() == ()


def test_active_entries_keeps_only_known_in_order() -> None:
    from pathlib import Path

    from agent_ng.skills.skill_registry import SkillEntry

    entries = [
        SkillEntry(name="alpha", description="a", path=Path("/tmp/alpha"), references=()),  # noqa: S108
        SkillEntry(name="beta", description="b", path=Path("/tmp/beta"), references=()),  # noqa: S108
        SkillEntry(name="gamma", description="c", path=Path("/tmp/gamma"), references=()),  # noqa: S108
    ]
    s = SkillSession()
    s.activate("beta", "b body")
    s.activate("gamma", "g body")
    out = s.active_entries(entries)
    assert [e.name for e in out] == ["beta", "gamma"]

"""Tests for skill integration on the LangChain agent (no LLM call)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def _write_skill(
    root: Path,
    folder: str,
    *,
    name: str | None = None,
    description: str = "",
    body: str = "skill body",
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


@pytest.fixture
def skills_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _write_skill(tmp_path, "cmw", description="CMW skill")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    return tmp_path


def _build_agent_without_init(skills_dir: Path) -> Any:
    """Build a CmwAgent instance without running its async init.

    We override ``_initialize_async`` to a no-op so we can exercise skill-only
    methods without touching the LLM or MCP tool loaders.
    """
    from agent_ng.langchain_agent import CmwAgent

    agent = CmwAgent(
        system_prompt="base system prompt",
        session_id="test-session",
        language="en",
    )
    # Skip the heavy async init that the constructor spawns.
    agent._init_done_for_test = True
    return agent


def test_agent_has_skill_session(skills_dir: Path) -> None:
    agent = _build_agent_without_init(skills_dir)
    from agent_ng.skills.skill_session import SkillSession

    assert hasattr(agent, "skill_session")
    assert isinstance(agent.skill_session, SkillSession)
    assert agent.skill_session.active_names() == ()


def test_agent_skill_session_is_per_instance(skills_dir: Path) -> None:
    a = _build_agent_without_init(skills_dir)
    b = _build_agent_without_init(skills_dir)
    a.skill_session.activate("cmw", "body")
    assert a.skill_session.is_active("cmw")
    assert not b.skill_session.is_active("cmw")


def test_activate_skill_loads_body(skills_dir: Path) -> None:
    agent = _build_agent_without_init(skills_dir)
    result = agent.activate_skill("cmw")
    assert "cmw body content" in result or "skill body" in result
    assert agent.skill_session.is_active("cmw")


def test_activate_unknown_skill_returns_error(skills_dir: Path) -> None:
    agent = _build_agent_without_init(skills_dir)
    result = agent.activate_skill("ghost")
    assert "Unknown skill" in result
    assert not agent.skill_session.is_active("ghost")


def test_deactivate_skill_removes_active(skills_dir: Path) -> None:
    agent = _build_agent_without_init(skills_dir)
    agent.activate_skill("cmw")
    assert agent.skill_session.is_active("cmw")
    result = agent.deactivate_skill("cmw")
    assert not agent.skill_session.is_active("cmw")
    assert "cmw" in result


def test_get_skill_system_messages_returns_active_blocks(
    skills_dir: Path,
) -> None:
    agent = _build_agent_without_init(skills_dir)
    agent.activate_skill("cmw")
    msgs = agent.get_skill_system_messages()
    assert len(msgs) == 1
    role, content = msgs[0]
    assert role == "system"
    assert "cmw" in content
    assert "skill body" in content


def test_get_skill_system_messages_empty_when_no_active(
    skills_dir: Path,
) -> None:
    agent = _build_agent_without_init(skills_dir)
    assert agent.get_skill_system_messages() == []


def test_skill_tools_in_tool_list_after_init(
    skills_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After async init, the three skill tools are present in self.tools."""
    import sys
    import time

    from agent_ng.langchain_agent import CmwAgent

    class _FakeLLMInstance:
        provider = "fake"
        model_name = "fake-model"
        config = None

    class _FakeLLMManager:
        def get_agent_llm(self):
            return _FakeLLMInstance()

        async def load_mcp_tools_if_enabled(self):
            return None

        def get_tools(self):
            return []

    # The agent imported get_llm_manager by name; rebind in its module namespace.
    la_mod = sys.modules["agent_ng.langchain_agent"]
    monkeypatch.setattr(la_mod, "get_llm_manager", lambda: _FakeLLMManager())

    agent = CmwAgent(
        system_prompt="x",
        session_id="t",
        language="en",
    )
    # init runs in a background thread because no event loop; give it a moment.
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if any(t.name == "load_skill" for t in agent.tools):
            break
        time.sleep(0.05)
    tool_names = {t.name for t in agent.tools}
    assert "load_skill" in tool_names
    assert "load_skill_reference" in tool_names
    assert "deactivate_skill" in tool_names


def test_system_prompt_includes_skill_section(skills_dir: Path) -> None:
    agent = _build_agent_without_init(skills_dir)
    # System prompt was set to "base system prompt" at construction; the
    # agent appends the skill section lazily.
    prompt = agent.get_effective_system_prompt()
    assert "base system prompt" in prompt
    assert "## Available skills" in prompt
    assert "- cmw: CMW skill" in prompt

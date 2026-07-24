"""End-to-end tests for the skill runtime.

These tests exercise the full path: a user types ``/<skill> <message>`` in
the chat, the preprocessor strips the prefix and loads the skill, and the
agent's ``stream_message`` invocation receives the skill body as a system
message — without making any real LLM call.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(
    root: Path, folder: str, *, name: str | None = None, description: str = "", body: str = "skill body"
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


def test_slash_command_strips_prefix_and_activates_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", body="cmw body content here")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.skills.chat_preprocessor import preprocess_chat_input

    verdict = preprocess_chat_input("/cmw list apps", tmp_path)
    assert not verdict.passthrough
    assert verdict.skill_activated == "cmw"
    assert verdict.user_text == "list apps"
    assert verdict.error is None


def test_unknown_skill_renders_inline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="cmw skill")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.skills.chat_preprocessor import preprocess_chat_input

    verdict = preprocess_chat_input("/ghost list apps", tmp_path)
    assert not verdict.passthrough
    assert verdict.error is not None
    assert "Unknown skill" in verdict.error
    assert "'ghost'" in verdict.error
    assert "cmw" in verdict.error  # listed as available


def test_session_block_re_attaches_active_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", body="cmw body content")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.skills.skill_session import SkillSession

    session = SkillSession()
    # Simulate the preprocessor activating the skill.
    from agent_ng.skills.skill_loader import load_skill_body

    loaded = load_skill_body(tmp_path, "cmw")
    session.activate(loaded.name, loaded.body)

    # Now simulate the agent re-attaching for the next turn.
    msgs = session.as_system_messages()
    assert len(msgs) == 1
    role, content = msgs[0]
    assert role == "system"
    assert "cmw body content" in content


def test_load_skill_tool_call_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate the LLM calling ``load_skill`` then ``deactivate_skill``."""
    import sys
    import time

    from agent_ng.langchain_agent import CmwAgent

    _write_skill(tmp_path, "cmw", body="cmw body content")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

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

    la_mod = sys.modules["agent_ng.langchain_agent"]
    monkeypatch.setattr(la_mod, "get_llm_manager", lambda: _FakeLLMManager())

    agent = CmwAgent(
        system_prompt="base",
        session_id="t",
        language="en",
    )

    deadline = time.time() + 10.0
    while time.time() < deadline:
        if any(t.name == "load_skill" for t in agent.tools):
            break
        time.sleep(0.05)
    tool_by_name = {t.name: t for t in agent.tools}

    # Simulate the LLM calling load_skill.
    result = tool_by_name["load_skill"].invoke({"name": "cmw"})
    assert "cmw body content" in result
    assert agent.skill_session.is_active("cmw")

    # Re-attach the session block — the model continues to see the skill.
    msgs = agent.get_skill_system_messages()
    assert any("cmw body content" in c for _, c in msgs)

    # Simulate the LLM calling deactivate_skill.
    result = tool_by_name["deactivate_skill"].invoke({"name": "cmw"})
    assert "cmw" in result
    assert not agent.skill_session.is_active("cmw")
    assert agent.get_skill_system_messages() == []


def test_two_sessions_are_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two agents in the same process must not share active-skill state."""
    import sys
    import time

    from agent_ng.langchain_agent import CmwAgent

    _write_skill(tmp_path, "cmw", body="cmw body")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

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

    la_mod = sys.modules["agent_ng.langchain_agent"]
    monkeypatch.setattr(la_mod, "get_llm_manager", lambda: _FakeLLMManager())

    a = CmwAgent(system_prompt="x", session_id="a", language="en")
    b = CmwAgent(system_prompt="x", session_id="b", language="en")

    deadline = time.time() + 10.0
    while time.time() < deadline:
        if all(any(t.name == "load_skill" for t in ag.tools) for ag in (a, b)):
            break
        time.sleep(0.05)

    a.activate_skill("cmw")
    assert a.skill_session.is_active("cmw")
    assert not b.skill_session.is_active("cmw")


def test_system_prompt_lists_discovered_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform skill")
    _write_skill(tmp_path, "docs", description="Documentation skill")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))

    from agent_ng.langchain_agent import CmwAgent

    a = CmwAgent(
        system_prompt="base prompt",
        session_id="t",
        language="en",
    )
    prompt = a.get_effective_system_prompt()
    assert "base prompt" in prompt
    assert "## Available skills" in prompt
    assert "- cmw: CMW Platform skill" in prompt
    assert "- docs: Documentation skill" in prompt
    assert "load_skill" in prompt


def test_disabled_skills_yield_no_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", description="CMW Platform skill")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    monkeypatch.setenv("CMW_SKILLS_ENABLED", "false")

    from agent_ng.langchain_agent import CmwAgent

    a = CmwAgent(
        system_prompt="base prompt",
        session_id="t",
        language="en",
    )
    prompt = a.get_effective_system_prompt()
    assert "## Available skills" not in prompt
    assert "base prompt" in prompt


def test_disabled_skills_yield_passthrough_in_chat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "cmw", body="body")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    monkeypatch.setenv("CMW_SKILLS_ENABLED", "false")

    from agent_ng.skills.chat_preprocessor import preprocess_chat_input

    verdict = preprocess_chat_input("/cmw list apps", tmp_path, enabled=False)
    assert verdict.passthrough
    assert verdict.user_text == "/cmw list apps"  # unchanged

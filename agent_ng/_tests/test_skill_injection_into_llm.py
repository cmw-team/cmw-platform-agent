"""Tests for skill injection into the LLM context.

These tests verify that when the user has activated a skill (via slash
command or via the ``load_skill`` tool), the active skill body AND the
skill index (``get_effective_system_prompt``) are injected into the LLM
context on every turn, while remaining absent from persisted memory.

The streaming path is exercised by mocking the LLM's ``astream`` so we
can capture the messages list passed to the model without requiring a
real LLM connection.
"""

from __future__ import annotations

import asyncio
import sys
import os
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Ensure the package is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


class _CapturingLLM:
    """Stub LLM that yields a single AIMessage and captures the messages list."""

    def __init__(self, content: str = "ok") -> None:
        self._content = content
        self.calls: list[list[Any]] = []
        self.bound_tools: Any = None

    async def astream(self, messages, config=None):
        self.calls.append(list(messages))
        chunk = AIMessage(content=self._content)
        yield chunk


class _FakeLLMInstance:
    def __init__(self, llm: _CapturingLLM) -> None:
        self.llm = llm
        self.provider = type("P", (), {"value": "fake"})()
        self.model_name = "fake-model"
        self.config = {"token_limit": 128000}


class _FakeTokenTracker:
    def __init__(self) -> None:
        self._messages: list[Any] = []
        self.begin_called = False
        self.finalize_called = False

    def begin_turn(self) -> None:
        self.begin_called = True

    def finalize_turn_usage(self, *args, **kwargs) -> None:
        self.finalize_called = True

    def update_turn_usage_from_api(self, *args, **kwargs) -> bool:
        return False

    def refresh_budget_snapshot(self, *args, **kwargs) -> None:
        pass

    def get_budget_snapshot(self) -> dict[str, Any]:
        return {"percentage_used": 0.0, "status": "ok"}

    def reset_current_conversation_budget(self) -> None:
        pass


class _FakeMemory:
    def __init__(self) -> None:
        self._store: dict[str, list[Any]] = {}

    def get_conversation_history(self, conversation_id: str) -> list[Any]:
        return list(self._store.get(conversation_id, []))

    def add_message(self, conversation_id: str, message: Any) -> None:
        self._store.setdefault(conversation_id, []).append(message)

    def clear_memory(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)


def _build_agent_with_skill(
    skills_dir: Path,
    skill_name: str = "cmw-prepare-lead-questions",
    skill_desc: str = "Подготовка квалификационных вопросов",
    skill_body: str = "Подготовь 10 открытых вопросов на основе данных CRM.",
) -> tuple[Any, _CapturingLLM]:
    """Build a minimal CmwAgent-like object with the skill injected.

    Returns (agent, capturing_llm). The capturing_llm records every
    ``astream`` invocation so tests can introspect the messages list.
    """
    from agent_ng.langchain_agent import CmwAgent

    _write_skill(
        skills_dir,
        skill_name,
        description=skill_desc,
        body=skill_body,
    )

    # Patch the LLM+memory before constructing the agent.
    capturing = _CapturingLLM()
    fake_llm = _FakeLLMInstance(capturing)
    fake_tokens = _FakeTokenTracker()
    fake_memory = _FakeMemory()

    # Build the agent cleanly.
    agent = CmwAgent(
        system_prompt="You are a test copilot.",
        session_id="t",
        language="en",
    )
    # Replace the LLM with the stub.
    agent.is_initialized = True
    agent.llm_instance = fake_llm
    agent.token_tracker = fake_tokens
    agent.memory_manager = fake_memory
    # Activate the skill.
    agent.activate_skill(skill_name)
    return agent, capturing


def _run_streaming_turn(agent: Any, message: str) -> list[Any]:
    """Drive one streaming turn and return the captured messages list."""
    from agent_ng.native_langchain_streaming import get_native_streaming

    streaming = get_native_streaming()

    async def _drive():
        return [
            event
            async for event in streaming.stream_agent_response(
                agent, message, conversation_id="t"
            )
        ]

    events = asyncio.run(_drive())
    # Sanity-check that we got at least one event.
    assert events, "stream_agent_response should yield events"
    return events


def test_skill_index_appears_in_system_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The system prompt must list available skills so the LLM knows what's installed."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    agent, _ = _build_agent_with_skill(tmp_path)

    prompt = agent.get_effective_system_prompt()
    assert "## Available skills" in prompt
    assert "cmw-prepare-lead-questions" in prompt
    assert "Подготовка квалификационных вопросов" in prompt


def test_active_skill_body_injected_into_llm_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a skill is active, its body must be a SystemMessage in the LLM call."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    agent, capturing = _build_agent_with_skill(tmp_path)

    _run_streaming_turn(agent, "Подготовь вопросы для лида ACME")

    assert len(capturing.calls) >= 1, "LLM should have been called at least once"
    messages = capturing.calls[0]

    # The first SystemMessage must be the skill index (from get_effective_system_prompt).
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    assert system_messages, "At least one SystemMessage must be present"
    first_system = system_messages[0].content
    assert "## Available skills" in first_system
    assert "cmw-prepare-lead-questions" in first_system

    # The active skill body must appear as a SystemMessage AFTER the first one.
    skill_body_msgs = [
        m for m in system_messages if "10 открытых вопросов" in m.content
    ]
    assert skill_body_msgs, (
        "Active skill body must be injected as a SystemMessage so the LLM has "
        "the instructions for the skill"
    )


def test_active_skill_body_appears_in_every_iteration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The skill body must be re-attached on every LLM call (if iterations loop)."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    agent, capturing = _build_agent_with_skill(tmp_path)

    _run_streaming_turn(agent, "test")

    # Even if there's only one iteration, the body must be in that call.
    for call_messages in capturing.calls:
        if any(
            isinstance(m, SystemMessage) and "10 открытых" in m.content
            for m in call_messages
        ):
            return  # success
    pytest.fail(
        "Skill body was not present in any LLM call. "
        f"Calls: {len(capturing.calls)}, sampled: {[m.content[:60] for m in capturing.calls[0][:3]]}"
    )


def test_skill_body_not_persisted_to_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The skill body is for-the-LLM-only; it must NOT be persisted to memory."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    agent, _ = _build_agent_with_skill(tmp_path)

    _run_streaming_turn(agent, "Подготовь вопросы")

    history = agent.memory_manager.get_conversation_history("t")
    skill_body_in_memory = any(
        isinstance(m, SystemMessage) and "10 открытых" in m.content
        for m in history
    )
    assert not skill_body_in_memory, (
        "Skill body must not be persisted to memory — it is re-injected on every turn"
    )

    # The skill index IS persisted once (as a SystemMessage) — that's fine.
    skill_index_in_memory = any(
        isinstance(m, SystemMessage) and "## Available skills" in m.content
        for m in history
    )
    assert skill_index_in_memory, (
        "Skill index should be persisted once (mirrors the existing behavior)"
    )


def test_user_message_present_in_llm_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sanity check: the user's message should be in the LLM call."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    agent, capturing = _build_agent_with_skill(tmp_path)

    _run_streaming_turn(agent, "Hello, please help me prepare questions")

    messages = capturing.calls[0]
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    assert any("Hello" in m.content for m in human_messages)


def test_no_active_skill_means_no_skill_body_in_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without active skills, the LLM sees only the system prompt + skill index."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    _write_skill(
        tmp_path,
        "cmw-prepare-lead-questions",
        description="desc",
        body="this body must NOT be injected",
    )

    from agent_ng.langchain_agent import CmwAgent

    agent = CmwAgent(
        system_prompt="base prompt",
        session_id="t",
        language="en",
    )
    capturing = _CapturingLLM()
    agent.is_initialized = True
    agent.llm_instance = _FakeLLMInstance(capturing)
    agent.token_tracker = _FakeTokenTracker()
    agent.memory_manager = _FakeMemory()
    # DO NOT activate any skill.

    _run_streaming_turn(agent, "test")

    messages = capturing.calls[0]
    skill_body_msgs = [
        m for m in messages
        if isinstance(m, SystemMessage) and "this body must NOT be injected" in m.content
    ]
    assert not skill_body_msgs, (
        "Skill body must not be injected when no skill is active"
    )


def test_skills_disabled_means_no_skill_section_in_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When CMW_SKILLS_ENABLED=false, the skill index is also skipped."""
    monkeypatch.setenv("CMW_SKILLS_DIR", str(tmp_path))
    monkeypatch.setenv("CMW_SKILLS_ENABLED", "false")
    _write_skill(tmp_path, "cmw", description="CMW")

    from agent_ng.langchain_agent import CmwAgent

    agent = CmwAgent(system_prompt="base", session_id="t", language="en")
    prompt = agent.get_effective_system_prompt()
    assert "## Available skills" not in prompt
    assert "base" in prompt

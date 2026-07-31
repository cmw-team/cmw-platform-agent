"""Tests for skill integration on the LangChain agent (no LLM call)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
import time

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


_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_SKILLS_ROOT = _REPO_ROOT / ".agents" / "skills"
_KNOWN_REAL_SKILL = "cmw-prepare-lead-questions"
_SKILL_TOOL_NAMES = (
    "load_skill",
    "load_skill_reference",
    "deactivate_skill",
)


class _SharedToolListManager:
    """Offline manager that exposes one shared mutable base-tool list."""

    def __init__(self) -> None:
        self.base_tools = [SimpleNamespace(name="base_tool")]

    def get_agent_llm(self):
        return SimpleNamespace(
            provider="fake",
            model_name="fake-model",
            config=None,
        )

    async def load_mcp_tools_if_enabled(self) -> None:
        return None

    def get_tools(self):
        return self.base_tools


@pytest.fixture
def shared_tool_list_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> _SharedToolListManager:
    """Install the shared-list manager without touching external services."""

    import agent_ng.langchain_agent as langchain_agent_module
    from agent_ng.skills.skill_tool import clear_active_skills

    clear_active_skills()
    monkeypatch.setenv("CMW_SKILLS_ENABLED", "true")
    monkeypatch.setenv("CMW_SKILLS_DIR", str(_REAL_SKILLS_ROOT))

    manager = _SharedToolListManager()
    monkeypatch.setattr(
        langchain_agent_module,
        "get_llm_manager",
        lambda: manager,
    )
    yield manager
    clear_active_skills()


def _new_initialized_agent(session_id: str):
    """Create a real agent; its synchronous test path waits for async init."""

    from agent_ng.langchain_agent import CmwAgent

    agent = CmwAgent(
        system_prompt="test",
        session_id=session_id,
        language="ru",
    )
    assert agent.is_initialized
    return agent


def _agent_tool_names(agent) -> list[str]:
    return [tool.name for tool in agent.tools]


def test_agent_initialization_does_not_mutate_manager_base_tools(
    shared_tool_list_manager: _SharedToolListManager,
) -> None:
    _new_initialized_agent("session-a")

    assert [
        tool.name for tool in shared_tool_list_manager.base_tools
    ] == ["base_tool"]


def test_get_tools_returns_snapshot_of_cached_base_tools() -> None:
    """A caller must not be able to mutate the manager's cached catalog."""

    from agent_ng.llm_manager import LLMManager

    manager = LLMManager.__new__(LLMManager)
    manager._cached_tools = [SimpleNamespace(name="base_tool")]

    caller_tools = manager.get_tools()
    caller_tools.append(SimpleNamespace(name="session_tool"))

    assert caller_tools is not manager._cached_tools
    assert [tool.name for tool in manager.get_tools()] == ["base_tool"]


def test_two_agents_receive_distinct_unique_tool_lists(
    shared_tool_list_manager: _SharedToolListManager,
) -> None:
    first = _new_initialized_agent("session-a")
    second = _new_initialized_agent("session-b")

    assert first.tools is not second.tools
    assert _agent_tool_names(first) == [
        "base_tool",
        *_SKILL_TOOL_NAMES,
    ]
    assert _agent_tool_names(second) == [
        "base_tool",
        *_SKILL_TOOL_NAMES,
    ]


def test_load_skill_tool_activates_only_its_own_agent_session(
    shared_tool_list_manager: _SharedToolListManager,
) -> None:
    first = _new_initialized_agent("session-a")
    second = _new_initialized_agent("session-b")

    load_skill = next(
        tool for tool in second.tools if tool.name == "load_skill"
    )
    result = load_skill.invoke({"name": _KNOWN_REAL_SKILL})

    assert "# Active skill:" in result
    assert second.skill_session.is_active(_KNOWN_REAL_SKILL)
    assert not first.skill_session.is_active(_KNOWN_REAL_SKILL)


class _BindingChatModel:
    """Minimal external-model substitute that records the bound tool list."""

    def __init__(self) -> None:
        self.bound_tools = None
        self.kwargs = {}

    def bind_tools(self, tools):
        self.bound_tools = tools
        self.kwargs["tools"] = tools
        return self


def test_new_llm_instance_binds_explicit_session_tools() -> None:
    """The LLM factory must prefer the agent's final session tool list."""

    from agent_ng.llm_manager import LLMInstance, LLMManager, LLMProvider

    manager = LLMManager.__new__(LLMManager)
    manager._allowed_providers = None
    manager.LLM_CONFIGS = {
        LLMProvider.POLZA: SimpleNamespace(tool_support=True),
    }
    manager._log_initialization = lambda *args, **kwargs: None

    chat_model = _BindingChatModel()
    instance = LLMInstance(
        llm=chat_model,
        provider=LLMProvider.POLZA,
        model_name="fake-model",
        config={},
        initialized_at=time.time(),
        last_used=time.time(),
    )
    manager._initialize_llm_instance = lambda *args, **kwargs: instance
    manager.get_tools = lambda: [SimpleNamespace(name="global_tool")]

    session_tools = [SimpleNamespace(name="session_tool")]
    try:
        result = manager.create_new_llm_instance(
            "polza",
            tools=session_tools,
        )
    except TypeError as exc:
        pytest.fail(
            "create_new_llm_instance must accept an explicit session tool "
            f"list: {exc}"
        )

    assert result is instance
    assert chat_model.bound_tools is session_tools
    assert instance.bound_tools


class _RecordingSessionManager:
    """Records which tools a session/model-switch path asks it to bind."""

    def __init__(self) -> None:
        self.received_tools = None

    def _get_configured_provider_and_model_index(self):
        from agent_ng.llm_manager import LLMProvider

        return LLMProvider.POLZA, 0

    def _find_model_index(self, provider, model):
        return 0

    def get_provider_config(self, provider):
        return SimpleNamespace(models=[{"model": "fake-model"}])

    def create_new_llm_instance(self, provider, model_index=0, **kwargs):
        self.received_tools = kwargs.get("tools")
        from agent_ng.llm_manager import LLMProvider

        return SimpleNamespace(
            provider=LLMProvider.POLZA,
            model_name="fake-model",
        )


def test_initial_session_llm_receives_agent_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SessionData must bind the list already assembled by its CmwAgent."""

    import agent_ng.session_manager as session_manager_module
    from agent_ng.session_manager import SessionData

    manager = _RecordingSessionManager()
    session_tools = [SimpleNamespace(name="session_tool")]
    agent = SimpleNamespace(
        llm_manager=manager,
        tools=session_tools,
    )
    data = SessionData.__new__(SessionData)
    data.agent = agent
    data.session_id = "session-a"
    data._session_llm_choice = None
    data.llm_provider = ""
    monkeypatch.setattr(
        session_manager_module,
        "get_session_config",
        lambda session_id: {},
    )

    data._initialize_session_agent()

    assert manager.received_tools is session_tools


def test_manual_model_switch_preserves_agent_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing the selected model must not drop session-bound skill tools."""

    import agent_ng.session_manager as session_manager_module
    from agent_ng.session_manager import SessionManager

    manager = _RecordingSessionManager()
    session_tools = [SimpleNamespace(name="session_tool")]
    agent = SimpleNamespace(
        llm_manager=manager,
        tools=session_tools,
        token_tracker=None,
    )
    session_data = SimpleNamespace(
        agent=agent,
        llm_provider="polza",
        _session_llm_choice=None,
    )
    sessions = SessionManager(language="ru")
    sessions.sessions["session-a"] = session_data
    monkeypatch.setattr(
        session_manager_module,
        "get_session_config",
        lambda session_id: {},
    )

    assert sessions.update_llm_provider(
        "session-a",
        "polza",
        "fake-model",
    )
    assert manager.received_tools is session_tools


def test_fallback_model_switch_preserves_agent_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Automatic fallback must bind the same session-specific tool list."""

    from agent_ng.llm_manager import LLMProvider
    from agent_ng.native_langchain_streaming import NativeLangChainStreaming

    manager = _RecordingSessionManager()
    session_tools = [SimpleNamespace(name="session_tool")]
    agent = SimpleNamespace(
        use_fallback_model=True,
        llm_instance=SimpleNamespace(provider=LLMProvider.POLZA),
        llm_manager=manager,
        tools=session_tools,
        token_tracker=None,
        fallback_model_name=None,
    )
    streaming = NativeLangChainStreaming()
    monkeypatch.setattr(
        streaming,
        "_select_fallback_model_for_agent",
        lambda current_agent: ("fake-model", 0),
    )

    assert streaming._try_switch_to_fallback_model(
        agent,
        "session-a",
        "context_limit",
    )
    assert manager.received_tools is session_tools

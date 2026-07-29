"""Контрактные тесты Markdown-артефактов разбора встреч."""

from __future__ import annotations

import importlib
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any
import uuid

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Использовать workspace-local каталог из-за ограничений Windows ACL."""
    base = (Path.cwd() / ".scratch" / "pytest-meeting-markdown").resolve()
    base.mkdir(parents=True, exist_ok=True)
    path = base / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        assert path.resolve().parent == base
        shutil.rmtree(path)


class FakeAgent:
    """Минимальный реестр UI-сессии, имитирующий поведение CmwAgent."""

    def __init__(self, root: Path, session_id: str = "session-1") -> None:
        self.root = root
        self.session_id = session_id
        self.files: dict[str, str] = {}
        self.generated_registrations: list[str] = []

    def register_file(self, name: str, path: str) -> None:
        destination = self.root / name
        shutil.move(path, destination)
        self.files[name] = str(destination)

    def register_generated_file(self, name: str, path: str) -> None:
        self.generated_registrations.append(name)
        self.register_file(name, path)

    def get_file_path(self, name: str) -> str | None:
        return self.files.get(name)


def _cache_module() -> Any:
    return importlib.import_module("tools.media_tools.meeting_transcript_cache")


def _tool_module() -> Any:
    return importlib.import_module(
        "tools.media_tools.tool_save_meeting_markdown"
    )


def _invoke(
    *,
    artifact_type: str,
    source_names: list[str],
    content: str | None,
    agent: FakeAgent,
) -> dict[str, Any]:
    return _tool_module().save_meeting_markdown.func(
        artifact_type=artifact_type,
        source_names=source_names,
        content=content,
        agent=agent,
    )


def test_openai_schema_contains_only_model_facing_fields() -> None:
    from langchain_core.utils.function_calling import convert_to_openai_tool

    parameters = convert_to_openai_tool(
        _tool_module().save_meeting_markdown
    )["function"]["parameters"]

    assert set(parameters["properties"]) == {
        "artifact_type",
        "source_names",
        "content",
    }
    assert "agent" not in parameters["properties"]


def test_cache_is_isolated_by_session_and_source(tmp_path: Path) -> None:
    cache = _cache_module()
    agent = FakeAgent(tmp_path, session_id="session-a")

    cache.store_transcript(agent, "first.mp4", "Первый текст")

    assert cache.get_transcript(agent, "first.mp4") == "Первый текст"
    assert cache.get_transcript(agent, "second.mp4") is None
    agent.session_id = "session-b"
    assert cache.get_transcript(agent, "first.mp4") is None


def test_summary_is_saved_as_registered_markdown(tmp_path: Path) -> None:
    agent = FakeAgent(tmp_path)

    result = _invoke(
        artifact_type="summary",
        source_names=["client-call.mp4"],
        content="# Итоги встречи\n\nОбсудили процесс.",
        agent=agent,
    )

    assert result["success"] is True
    assert result["generated_filename"] == "client-call_summary.md"
    assert agent.generated_registrations == ["client-call_summary.md"]
    saved = Path(agent.get_file_path("client-call_summary.md") or "")
    assert saved.read_text(encoding="utf-8") == (
        "# Итоги встречи\n\nОбсудили процесс.\n"
    )


def test_single_transcript_is_saved_from_cache_without_model_copy(
    tmp_path: Path,
) -> None:
    cache = _cache_module()
    agent = FakeAgent(tmp_path)
    cache.store_transcript(
        agent,
        "client-call.mp4",
        "Первая тема разговора. Вторая тема разговора.",
    )

    result = _invoke(
        artifact_type="transcript",
        source_names=["client-call.mp4"],
        content=None,
        agent=agent,
    )

    assert result["success"] is True
    assert result["generated_filename"] == "client-call_transcript.md"
    saved = Path(agent.get_file_path("client-call_transcript.md") or "")
    rendered = saved.read_text(encoding="utf-8")
    assert "Первая тема разговора. Вторая тема разговора." in rendered


def test_combined_transcript_preserves_declared_source_order(
    tmp_path: Path,
) -> None:
    cache = _cache_module()
    agent = FakeAgent(tmp_path)
    cache.store_transcript(agent, "part-1.mp4", "Первая часть.")
    cache.store_transcript(agent, "part-2.mp4", "Вторая часть.")

    result = _invoke(
        artifact_type="transcript",
        source_names=["part-1.mp4", "part-2.mp4"],
        content=None,
        agent=agent,
    )

    assert result["success"] is True
    assert result["generated_filename"] == "combined_meeting_transcript.md"
    saved = Path(agent.get_file_path("combined_meeting_transcript.md") or "")
    rendered = saved.read_text(encoding="utf-8")
    assert rendered.index("Первая часть.") < rendered.index("Вторая часть.")


def test_uploaded_transcript_ignores_model_content_and_uses_cached_text(
    tmp_path: Path,
) -> None:
    cache = _cache_module()
    agent = FakeAgent(tmp_path)
    cache.store_transcript(agent, "client-call.mp4", "Первый текст.")

    result = _invoke(
        artifact_type="transcript",
        source_names=["client-call.mp4"],
        content="Изменённый моделью текст.",
        agent=agent,
    )

    assert result["success"] is True
    saved = Path(agent.get_file_path("client-call_transcript.md") or "")
    rendered = saved.read_text(encoding="utf-8")
    assert "Первый текст." in rendered
    assert "Изменённый моделью текст." not in rendered


def test_uploaded_transcript_does_not_require_content(
    tmp_path: Path,
) -> None:
    cache = _cache_module()
    agent = FakeAgent(tmp_path)
    cache.store_transcript(agent, "client-call.mp4", "Полный текст.")

    result = _invoke(
        artifact_type="transcript",
        source_names=["client-call.mp4"],
        content=None,
        agent=agent,
    )

    assert result["success"] is True
    assert result["generated_filename"] == "client-call_transcript.md"


def test_missing_cached_transcript_returns_safe_error(tmp_path: Path) -> None:
    agent = FakeAgent(tmp_path)

    result = _invoke(
        artifact_type="transcript",
        source_names=["missing.mp4"],
        content=None,
        agent=agent,
    )

    assert result["success"] is False
    assert result["generated_filename"] is None
    assert result["error"]["code"] == "transcript_not_cached"


def test_pasted_transcript_can_be_saved_without_media_source(
    tmp_path: Path,
) -> None:
    agent = FakeAgent(tmp_path)

    result = _invoke(
        artifact_type="transcript",
        source_names=[],
        content="Готовый транскрипт пользователя.",
        agent=agent,
    )

    assert result["success"] is True
    assert result["generated_filename"] == "meeting_transcript.md"
    saved = Path(agent.get_file_path("meeting_transcript.md") or "")
    assert "Готовый транскрипт пользователя." in saved.read_text(encoding="utf-8")


def test_registered_markdown_resolves_to_ui_file_attachment(
    tmp_path: Path,
) -> None:
    from agent_ng._file_attachment import build_file_attachment
    from agent_ng.tool_invocation import invoke_agent_tool_blocking

    agent = FakeAgent(tmp_path)
    result = invoke_agent_tool_blocking(
        _tool_module().save_meeting_markdown,
        {
            "artifact_type": "summary",
            "source_names": ["client-call.mp4"],
            "content": "# Итоги встречи\n\nГотово.",
            "agent": agent,
        },
    )

    attachment = build_file_attachment(result, agent)

    assert attachment is not None
    assert attachment["display_name"] == "client-call_summary.md"
    assert Path(attachment["path"]).read_text(encoding="utf-8").startswith(
        "# Итоги встречи"
    )

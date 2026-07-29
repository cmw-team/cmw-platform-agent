# ruff: noqa: RUF002, RUF003
"""LangChain tool для сохранения результатов разбора встречи в Markdown.

Tool создаёт ровно один файл за вызов. Для каждой встречи модель вызывает его
дважды: сначала с готовым summary, затем для полного транскрипта. Транскрипт
загруженного медиа берётся из сессионного кэша, поэтому большой текст не нужно
повторно помещать в аргументы tool.
"""

from __future__ import annotations

from contextlib import suppress
import os
from pathlib import Path
import re
import tempfile
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

from tools.media_tools.meeting_transcript_cache import get_transcript

ArtifactType = Literal["summary", "transcript"]

_ERROR_MESSAGES = {
    "invalid_agent": "Не удалось получить файловый реестр текущей UI-сессии.",
    "invalid_artifact_type": "Тип файла должен быть summary или transcript.",
    "invalid_source": "Передайте точные исходные имена файлов без путей и URL.",
    "content_missing": "Для создаваемого файла отсутствует обязательный текст.",
    "transcript_not_cached": (
        "Полный транскрипт не найден в текущей сессии. "
        "Сначала повторно вызовите transcribe_uploaded_media для этого файла."
    ),
    "file_write_failed": "Не удалось записать Markdown-файл.",
    "file_registration_failed": (
        "Не удалось зарегистрировать Markdown-файл в текущей UI-сессии."
    ),
}

_WINDOWS_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class SaveMeetingMarkdownSchema(BaseModel):
    """Публичные аргументы модели и скрытый runtime-контекст."""

    artifact_type: ArtifactType = Field(
        description=(
            "Which Markdown artifact to create: 'summary' or 'transcript'."
        )
    )
    source_names: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered exact filenames of transcribed media. Pass one filename "
            "for one meeting, all ordered parts for a combined meeting, or an "
            "empty list when the user supplied a ready text transcript."
        ),
    )
    content: str | None = Field(
        default=None,
        description=(
            "Complete Markdown summary when artifact_type='summary'. For a "
            "transcript of uploaded media, pass null because the full text is "
            "read from the session cache. For a transcript pasted directly by "
            "the user, pass the full text."
        ),
    )
    agent: Annotated[Any | None, InjectedToolArg] = Field(
        default=None,
        description="Runtime-injected agent; never supplied by the model.",
    )


def _error(code: str) -> dict[str, Any]:
    """Вернуть стабильный JSON-совместимый ответ без внутренних деталей."""
    return {
        "success": False,
        "generated_filename": None,
        "error": {"code": code, "message": _ERROR_MESSAGES[code]},
    }


def _success(filename: str) -> dict[str, Any]:
    """Вернуть имя зарегистрированного файла для отображения в UI."""
    return {
        "success": True,
        "generated_filename": filename,
        "error": None,
    }


def _is_valid_source_name(value: object) -> bool:
    """Проверить, что модель передала имя вложения, а не путь или URL."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if "/" in value or "\\" in value or value in {".", ".."}:
        return False
    parsed = urlsplit(value)
    return not parsed.scheme and not parsed.netloc


def _normalize_sources(source_names: object) -> list[str] | None:
    """Проверить список имён и сохранить заявленный пользователем порядок."""
    if not isinstance(source_names, list):
        return None
    if any(not _is_valid_source_name(name) for name in source_names):
        return None
    if len(set(source_names)) != len(source_names):
        return None
    return source_names


def _safe_stem(source_name: str) -> str:
    """Получить безопасную основу выходного имени из имени медиафайла."""
    stem = Path(source_name).stem
    sanitized = _WINDOWS_UNSAFE_FILENAME_CHARS.sub("_", stem)
    sanitized = sanitized.strip().rstrip(". ")
    return sanitized[:120] or "meeting"


def _output_filename(
    artifact_type: ArtifactType,
    source_names: list[str],
) -> str:
    """Сформировать предсказуемое логическое имя Markdown-файла."""
    if len(source_names) > 1:
        stem = "combined_meeting"
    elif source_names:
        stem = _safe_stem(source_names[0])
    else:
        stem = "meeting"
    return f"{stem}_{artifact_type}.md"


def _one_trailing_newline(text: str) -> str:
    """Нормализовать только конец файла, не переписывая его содержимое."""
    return text.rstrip("\r\n") + "\n"


def _render_cached_transcript(
    source_names: list[str],
    agent: Any,
) -> str | None:
    """Собрать Markdown из полных кэшированных транскриптов в заданном порядке."""
    transcripts: list[str] = []
    for source_name in source_names:
        transcript = get_transcript(agent, source_name)
        if transcript is None:
            return None
        transcripts.append(transcript)

    if len(source_names) == 1:
        return (
            "# Полный транскрипт\n\n"
            f"Источник: `{source_names[0]}`\n\n"
            f"{transcripts[0]}"
        )

    # Для нескольких частей заголовки позволяют проверить порядок и источник,
    # а сам текст каждой части помещается без сокращений и исправлений.
    sections = ["# Полный транскрипт"]
    for index, (source_name, transcript) in enumerate(
        zip(source_names, transcripts, strict=True),
        start=1,
    ):
        sections.append(
            f"## Часть {index} — `{source_name}`\n\n{transcript}"
        )
    return "\n\n".join(sections)


def _render_pasted_transcript(content: str) -> str:
    """Оформить полный текст, который пользователь передал прямо в чат."""
    return (
        "# Полный транскрипт\n\n"
        "Источник: `транскрипт пользователя`\n\n"
        f"{content}"
    )


def _write_and_register(
    *,
    filename: str,
    text: str,
    agent: Any,
) -> dict[str, Any]:
    """Записать UTF-8 Markdown во временный файл и передать его UI-реестру."""
    temp_path: str | None = None
    try:
        # mkstemp создаёт уникальный файл без гонки имён. Дескриптор сразу
        # закрывается, чтобы Windows разрешил последующую запись и перемещение.
        descriptor, temp_path = tempfile.mkstemp(suffix=".md")
        os.close(descriptor)
        Path(temp_path).write_text(
            _one_trailing_newline(text),
            encoding="utf-8",
        )
    except OSError:
        if temp_path:
            with suppress(OSError):
                Path(temp_path).unlink(missing_ok=True)
        return _error("file_write_failed")

    try:
        # register_file перемещает файл в Gradio cache и связывает логическое
        # имя с текущей сессией. Именно generated_filename затем показывает UI.
        agent.register_file(filename, temp_path)
    except Exception:
        with suppress(OSError):
            Path(temp_path).unlink(missing_ok=True)
        return _error("file_registration_failed")

    return _success(filename)


@tool(
    "save_meeting_markdown",
    args_schema=SaveMeetingMarkdownSchema,
    return_direct=False,
)
def save_meeting_markdown(
    artifact_type: ArtifactType,
    source_names: list[str],
    content: str | None = None,
    agent: Annotated[Any | None, InjectedToolArg] = None,
) -> dict[str, Any]:
    """Create one downloadable Markdown artifact for a processed meeting.

    Call once with ``artifact_type='summary'`` and the complete structured
    summary. Call again with ``artifact_type='transcript'``. For uploaded
    media, provide ordered ``source_names`` and leave ``content`` null; the
    exact full transcript is read from the current session cache.
    """
    if artifact_type not in {"summary", "transcript"}:
        return _error("invalid_artifact_type")
    if agent is None or not callable(getattr(agent, "register_file", None)):
        return _error("invalid_agent")

    normalized_sources = _normalize_sources(source_names)
    if normalized_sources is None:
        return _error("invalid_source")

    if artifact_type == "summary":
        if not isinstance(content, str) or not content.strip():
            return _error("content_missing")
        rendered = content
    elif normalized_sources:
        rendered = _render_cached_transcript(normalized_sources, agent)
        if rendered is None:
            return _error("transcript_not_cached")
    else:
        if not isinstance(content, str) or not content.strip():
            return _error("content_missing")
        rendered = _render_pasted_transcript(content)

    filename = _output_filename(artifact_type, normalized_sources)
    return _write_and_register(
        filename=filename,
        text=rendered,
        agent=agent,
    )


__all__ = ["SaveMeetingMarkdownSchema", "save_meeting_markdown"]

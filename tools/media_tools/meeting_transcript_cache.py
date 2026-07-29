# ruff: noqa: RUF002
"""Сессионное хранилище полных транскриптов в памяти агента.

Кэш нужен только как технический мост между двумя LangChain tools:
``transcribe_uploaded_media`` сохраняет полученный текст, а
``save_meeting_markdown`` забирает его для записи Markdown-файла. Благодаря
этому основная модель не должна повторно передавать большой транскрипт в
аргументах второго tool.

Данные хранятся на объекте текущего агента и не записываются на диск этим
модулем. Ключ включает ID UI-сессии и точное исходное имя файла, поэтому
транскрипты разных сессий и вложений не смешиваются.
"""

from __future__ import annotations

from typing import Any

_CACHE_ATTRIBUTE = "_cmw_meeting_transcript_cache"


def _session_id(agent: Any) -> str | None:
    """Вернуть непустой ID текущей UI-сессии либо ``None``.

    Отсутствие session_id означает, что надёжно изолировать данные разных
    пользователей невозможно. В таком случае кэш намеренно не используется.
    """
    value = getattr(agent, "session_id", None)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _cache(agent: Any, *, create: bool) -> dict[tuple[str, str], str] | None:
    """Получить приватный словарь кэша с объекта агента.

    Словарь создаётся лениво только при первой успешной транскрибации. Такое
    размещение связывает жизненный цикл текстов с жизненным циклом агента и не
    создаёт глобальное хранилище данных всех пользователей процесса.
    """
    if agent is None:
        return None

    existing = getattr(agent, _CACHE_ATTRIBUTE, None)
    if isinstance(existing, dict):
        return existing
    if not create:
        return None

    created: dict[tuple[str, str], str] = {}
    try:
        setattr(agent, _CACHE_ATTRIBUTE, created)
    except (AttributeError, TypeError):
        return None
    return created


def store_transcript(agent: Any, source: str, transcript: str) -> bool:
    """Сохранить полный транскрипт для файла в текущей сессии.

    Возвращает ``True`` только когда все части ключа валидны и текст удалось
    разместить на объекте агента. Текст сохраняется без редактирования.
    """
    session_id = _session_id(agent)
    if session_id is None or not isinstance(source, str) or not source:
        return False
    if not isinstance(transcript, str):
        return False

    cache = _cache(agent, create=True)
    if cache is None:
        return False
    cache[(session_id, source)] = transcript
    return True


def get_transcript(agent: Any, source: str) -> str | None:
    """Получить транскрипт только для указанной сессии и исходного файла."""
    session_id = _session_id(agent)
    if session_id is None or not isinstance(source, str) or not source:
        return None

    cache = _cache(agent, create=False)
    if cache is None:
        return None
    value = cache.get((session_id, source))
    return value if isinstance(value, str) else None


def remove_transcript(agent: Any, source: str) -> None:
    """Удалить старый транскрипт файла перед новой попыткой распознавания.

    Это не позволяет ошибочной повторной транскрибации оставить в кэше текст
    от предыдущего успешного запуска с тем же именем файла.
    """
    session_id = _session_id(agent)
    if session_id is None or not isinstance(source, str) or not source:
        return

    cache = _cache(agent, create=False)
    if cache is not None:
        cache.pop((session_id, source), None)


__all__ = ["get_transcript", "remove_transcript", "store_transcript"]

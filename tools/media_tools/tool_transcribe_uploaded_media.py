# ruff: noqa: RUF002, RUF003
"""LangChain tool для полной транскрибации вложенного аудио или видео.

Основная модель передаёт только исходное имя вложения. Физический путь и ключ
Polza берутся из текущей UI-сессии, не входят в schema и никогда не возвращаются
в результате. Модуль координирует локальные и внешние операции, но не выполняет
summary и не изменяет текст транскрибации.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Annotated, Any
from urllib.parse import urlsplit
from uuid import uuid4

from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

from agent_ng.openrouter_usage_accounting import normalize_polza_usage
from agent_ng.session_manager import get_session_config
from tools.media_tools.media_converter import (
    AudioStreamNotFoundError,
    ConversionFailedError,
    FFmpegNotFoundError,
    InvalidMediaError,
    convert_to_mp3_chunks,
    probe_media,
    split_mp3_chunk,
)
from tools.media_tools.meeting_transcript_cache import (
    remove_transcript,
    store_transcript,
)
from tools.media_tools.polza_transcription_client import (
    ChunkTranscription,
    PayloadTooLargeError,
    PolzaAuthenticationError,
    PolzaInsufficientFundsError,
    PolzaInvalidRequestError,
    PolzaInvalidResponseError,
    PolzaRateLimitError,
    PolzaTranscriptionClient,
    PolzaTranscriptionError,
    PolzaUnavailableError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

DEFAULT_POLZA_BASE_URL = "https://polza.ai/api/v1"
DEFAULT_TRANSCRIPTION_MODEL = "openai/whisper-large-v3-turbo"

_ERROR_MESSAGES = {
    "invalid_source": "Укажите точное исходное имя вложенного аудио- или видеофайла.",
    "file_not_found": "Файл не найден среди вложений текущей сессии.",
    "ffmpeg_not_found": "FFmpeg или ffprobe не установлены на сервере.",
    "invalid_media": "Файл не является поддерживаемым аудио или видео.",
    "audio_stream_not_found": "В файле отсутствует аудиодорожка.",
    "conversion_failed": "Не удалось подготовить MP3-фрагменты.",
    "payload_too_large": "Не удалось уменьшить аудио до допустимого размера запроса.",
    "polza_api_key_missing": "Введите API key Polza в настройках текущей сессии.",
    "polza_authentication_failed": "Polza отклонила API key текущей сессии.",
    "polza_insufficient_funds": "На балансе Polza недостаточно средств.",
    "polza_invalid_request": "Polza отклонила запрос транскрибации.",
    "polza_rate_limit": "Polza не выполнила запрос из-за ограничения частоты.",
    "polza_unavailable": "Сервис транскрибации Polza временно недоступен.",
    "polza_invalid_response": "Polza вернула некорректный ответ транскрибации.",
    "transcription_failed": "Не удалось выполнить транскрибацию.",
}


class TranscribeUploadedMediaSchema(BaseModel):
    """Публичный аргумент модели и скрытый runtime-контекст инструмента."""

    source: str = Field(
        description=(
            "Exact original filename of an audio or video file uploaded in "
            "the current UI session. Do not pass a path or URL."
        )
    )
    agent: Annotated[Any | None, InjectedToolArg] = Field(
        default=None,
        description="Runtime-injected agent; never supplied by the model.",
    )


def _error(code: str) -> dict[str, Any]:
    """Сформировать единый JSON-совместимый ответ без внутренних деталей."""
    return {
        "success": False,
        "data": None,
        "cost_rub": None,
        "cost": None,
        "error": {"code": code, "message": _ERROR_MESSAGES[code]},
    }


def _success(
    *,
    source: str,
    transcript: str,
    duration_seconds: float,
    cost_rub: float | None,
    chunk_count: int,
    model: str,
) -> dict[str, Any]:
    """Сформировать полный результат и стоимость в единице общей статистики."""
    cost: float | None = None
    if cost_rub is not None:
        try:
            normalized = normalize_polza_usage({"cost_rub": cost_rub})
            normalized_cost = normalized.get("cost")
            if isinstance(normalized_cost, (int, float)):
                cost = float(normalized_cost)
        except Exception:
            # Ошибка преобразования курса не должна уничтожать уже оплаченную
            # транскрибацию; фактический cost_rub остаётся в ответе.
            cost = None

    return {
        "success": True,
        "data": {
            "source": {"requested": source, "source_type": "uploaded"},
            "transcript": transcript,
            "language": "ru",
            "duration_seconds": duration_seconds,
            "model": model,
            "chunk_count": chunk_count,
        },
        "cost_rub": cost_rub,
        "cost": cost,
        "error": None,
    }


def _is_valid_source(source: object) -> bool:
    """Разрешить только точное имя вложения без URL и компонентов пути."""
    if not isinstance(source, str) or not source or source != source.strip():
        return False
    if "/" in source or "\\" in source or source in {".", ".."}:
        return False
    parsed = urlsplit(source)
    return not parsed.scheme and not parsed.netloc


def _resolve_uploaded_path(source: str, agent: Any) -> Path | None:
    """Получить физический путь исключительно из реестра текущей сессии."""
    if agent is None or not hasattr(agent, "get_file_path"):
        return None
    try:
        registered = agent.get_file_path(source)
    except Exception:
        return None
    if not isinstance(registered, (str, Path)) or not registered:
        return None
    path = Path(registered)
    return path if path.is_file() else None


def _session_polza_key(agent: Any) -> str | None:
    """Прочитать Polza key только из конфигурации указанной UI-сессии.

    Здесь намеренно не используется общий ``get_provider_api_key``, потому что
    он допускает fallback на environment, запрещённый контрактом этого tool.
    """
    session_id = getattr(agent, "session_id", None)
    if not isinstance(session_id, str) or not session_id:
        return None
    try:
        config = get_session_config(session_id)
    except Exception:
        return None
    if not isinstance(config, dict):
        return None
    keys = config.get("llm_provider_api_keys")
    if not isinstance(keys, dict):
        return None
    key = keys.get("polza")
    return key.strip() if isinstance(key, str) and key.strip() else None


@contextmanager
def _temporary_workspace(source_path: Path) -> Iterator[Path]:
    """Создать отдельную рабочую папку вызова и удалить её при любом исходе.

    Стандартный ``TemporaryDirectory`` не используется: в некоторых
    корпоративных Windows-средах Python создаёт его с ACL, который затем не
    позволяет тому же процессу выполнить очистку. Обычный ``Path.mkdir``
    наследует рабочие права каталога загрузки текущей UI-сессии.
    """
    workspace = source_path.parent / f".cmw-transcription-{uuid4().hex}"
    workspace.mkdir()
    try:
        yield workspace
    finally:
        # Все фрагменты принадлежат только текущему вызову. ``rmtree`` нужен,
        # потому что внутри может находиться несколько MP3 и подпапок FFmpeg.
        shutil.rmtree(workspace)


def _transcribe_with_fallback_split(
    client: PolzaTranscriptionClient,
    chunk_path: Path,
    workspace: Path,
) -> list[ChunkTranscription]:
    """Транскрибировать chunk либо заменить его уменьшенными MP3-частями.

    Само деление реализовано конвертером этапа 2. Здесь находится только
    координация: первый ``PayloadTooLargeError`` включает fallback, а повторное
    превышение уже передаётся вызывающему коду как общий отказ без partial text.
    """
    try:
        return [client.transcribe_chunk(chunk_path)]
    except PayloadTooLargeError:
        smaller_parts = split_mp3_chunk(chunk_path, workspace)
        return [client.transcribe_chunk(part) for part in smaller_parts]


def _map_known_error(error: Exception) -> str:
    """Сопоставить тип внутреннего исключения с публичным кодом ошибки."""
    mappings: tuple[tuple[type[Exception], str], ...] = (
        (FFmpegNotFoundError, "ffmpeg_not_found"),
        (InvalidMediaError, "invalid_media"),
        (AudioStreamNotFoundError, "audio_stream_not_found"),
        (ConversionFailedError, "conversion_failed"),
        (PayloadTooLargeError, "payload_too_large"),
        (PolzaAuthenticationError, "polza_authentication_failed"),
        (PolzaInsufficientFundsError, "polza_insufficient_funds"),
        (PolzaInvalidRequestError, "polza_invalid_request"),
        (PolzaRateLimitError, "polza_rate_limit"),
        (PolzaUnavailableError, "polza_unavailable"),
        (PolzaInvalidResponseError, "polza_invalid_response"),
        (PolzaTranscriptionError, "transcription_failed"),
    )
    for error_type, code in mappings:
        if isinstance(error, error_type):
            return code
    return "transcription_failed"


@tool(
    "transcribe_uploaded_media",
    args_schema=TranscribeUploadedMediaSchema,
    return_direct=False,
)
def transcribe_uploaded_media(
    source: str,
    agent: Annotated[Any | None, InjectedToolArg] = None,
) -> dict[str, Any]:
    """Convert an uploaded audio/video file and return its full transcription.

    ``source`` must be the exact original filename registered in the current UI
    session. The tool returns the full Russian transcription and does not
    summarise, interpret, translate, or permanently store the media.
    """
    if not _is_valid_source(source):
        return _error("invalid_source")

    # Новая попытка не должна оставить доступным старый текст файла с тем же
    # именем, если текущая конвертация или внешний запрос завершатся ошибкой.
    remove_transcript(agent, source)

    source_path = _resolve_uploaded_path(source, agent)
    if source_path is None:
        return _error("file_not_found")

    api_key = _session_polza_key(agent)
    if api_key is None:
        return _error("polza_api_key_missing")

    base_url = os.getenv("POLZA_BASE_URL", DEFAULT_POLZA_BASE_URL).strip()
    model = os.getenv(
        "POLZA_TRANSCRIPTION_MODEL",
        DEFAULT_TRANSCRIPTION_MODEL,
    ).strip() or DEFAULT_TRANSCRIPTION_MODEL
    client = PolzaTranscriptionClient(api_key, base_url, model)

    try:
        # Контекстный менеджер гарантирует очистку MP3 при обычном завершении
        # и при исключении; исходный upload находится за его пределами.
        with _temporary_workspace(source_path) as workspace:
            probe_media(source_path)
            chunks = convert_to_mp3_chunks(source_path, workspace)

            results: list[ChunkTranscription] = []
            for chunk in chunks:
                results.extend(
                    _transcribe_with_fallback_split(client, chunk, workspace)
                )
    except Exception as exc:
        return _error(_map_known_error(exc))

    transcript = "\n\n".join(result.text for result in results)
    duration_seconds = sum(result.duration_seconds for result in results)

    # Сессионный кэш позволяет следующему tool сохранить полный транскрипт в
    # Markdown, не заставляя основную модель повторять большой текст в аргументе.
    store_transcript(agent, source, transcript)

    # Если стоимость отсутствует хотя бы у одной части, итог остаётся unknown:
    # локально рассчитывать фактическое списание по каталожной цене запрещено.
    has_complete_cost = all(result.cost_rub is not None for result in results)
    cost_rub = (
        sum(float(result.cost_rub) for result in results if result.cost_rub is not None)
        if has_complete_cost
        else None
    )
    return _success(
        source=source,
        transcript=transcript,
        duration_seconds=duration_seconds,
        cost_rub=cost_rub,
        chunk_count=len(results),
        model=model,
    )

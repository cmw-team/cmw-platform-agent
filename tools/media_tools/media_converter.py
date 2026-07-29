# ruff: noqa: RUF002, RUF003
"""Проверка медиа и преобразование первой аудиодорожки в MP3-фрагменты.

Модуль является локальной границей будущего LangChain tool: он работает только
с файлами на сервере и ничего не отправляет внешним сервисам. Все команды
передаются ``subprocess`` списком аргументов, поэтому имя пользовательского
файла не интерпретируется командной оболочкой.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


FFPROBE_BINARY = "ffprobe"
FFMPEG_BINARY = "ffmpeg"
PRIMARY_CHUNK_SECONDS = 20 * 60
FALLBACK_CHUNK_SECONDS = 10 * 60


class FFmpegNotFoundError(RuntimeError):
    """FFmpeg или ffprobe отсутствует в PATH процесса агента."""


class InvalidMediaError(RuntimeError):
    """FFprobe не смог прочитать файл как поддерживаемое медиа."""


class AudioStreamNotFoundError(RuntimeError):
    """FFprobe прочитал медиа, но не обнаружил в нём аудиодорожку."""


class ConversionFailedError(RuntimeError):
    """FFmpeg не смог создать непустые самостоятельные MP3-фрагменты."""


def _run_checked(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Запустить FFmpeg-команду без shell и вернуть захваченный результат.

    ``FileNotFoundError`` нормализуется здесь, поскольку отсутствие обоих
    бинарных файлов одинаково исправляется на уровне развёртывания. Ошибку
    самого медиа вызывающая функция преобразует в более точное исключение.
    """
    try:
        return subprocess.run(  # noqa: S603
            arguments,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError(
            "FFmpeg или ffprobe не найдены на сервере."
        ) from exc


def _load_probe_payload(stdout: str) -> dict[str, Any]:
    """Проверить, что stdout FFprobe содержит JSON-объект ожидаемого уровня."""
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise InvalidMediaError("Не удалось прочитать структуру медиафайла.") from exc
    if not isinstance(payload, dict):
        raise InvalidMediaError("Не удалось прочитать структуру медиафайла.")
    return payload


def probe_media(source_path: Path) -> None:
    """Проверить читаемость файла и наличие хотя бы одной аудиодорожки.

    Расширению файла доверять нельзя, поэтому FFprobe читает фактический
    контейнер. Успешный возврат ``None`` означает, что файл пригоден для
    последующей конвертации; физический путь не включается в тексты ошибок.
    """
    arguments = [
        FFPROBE_BINARY,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        str(source_path),
    ]
    try:
        result = _run_checked(arguments)
    except subprocess.CalledProcessError as exc:
        raise InvalidMediaError("Файл не является поддерживаемым медиа.") from exc

    payload = _load_probe_payload(result.stdout)
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise InvalidMediaError("FFprobe вернул некорректное описание медиа.")

    # Наличие video-потока не компенсирует отсутствие звука: для будущей
    # транскрибации нужна хотя бы одна дорожка с codec_type=audio.
    if not any(
        isinstance(stream, dict) and stream.get("codec_type") == "audio"
        for stream in streams
    ):
        raise AudioStreamNotFoundError("В медиафайле отсутствует аудиодорожка.")


def _ordered_mp3_files(directory: Path, pattern: str) -> list[Path]:
    """Вернуть созданные FFmpeg MP3 в порядке их числовых имён.

    Segment muxer подставляет в ``%03d`` нули слева, поэтому сортировка имени
    совпадает с хронологическим порядком. Пустые файлы не считаются корректным
    результатом конвертации.
    """
    paths = sorted(directory.glob(pattern), key=lambda path: path.name)
    valid = [path for path in paths if path.is_file() and path.stat().st_size > 0]
    if not valid or len(valid) != len(paths):
        raise ConversionFailedError("Не удалось создать корректные MP3-фрагменты.")
    return valid


def _convert_to_segments(
    source_path: Path,
    output_dir: Path,
    *,
    segment_seconds: int,
    filename_pattern: str,
) -> list[Path]:
    """Перекодировать первую аудиодорожку в упорядоченные MP3-сегменты.

    Перекодирование, а не разрезание байтов, гарантирует, что каждая часть имеет
    собственную корректную MP3-структуру. Видео явно исключается, параметры
    mono/16 kHz/64 kbit/s фиксированы контрактом и не приходят от модели.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / filename_pattern
    arguments = [
        FFMPEG_BINARY,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        "-codec:a",
        "libmp3lame",
        "-f",
        "segment",
        "-segment_format",
        "mp3",
        "-segment_time",
        str(segment_seconds),
        "-reset_timestamps",
        "1",
        str(output_pattern),
    ]
    try:
        _run_checked(arguments)
    except subprocess.CalledProcessError as exc:
        raise ConversionFailedError("Не удалось преобразовать аудиодорожку.") from exc

    glob_pattern = filename_pattern.replace("%03d", "*")
    return _ordered_mp3_files(output_dir, glob_pattern)


def convert_to_mp3_chunks(source_path: Path, output_dir: Path) -> list[Path]:
    """Создать MP3-фрагменты длительностью до базовых двадцати минут.

    Исходный пользовательский файл передаётся FFmpeg только как input и не
    удаляется. Временным каталогом владеет вызывающий tool, поэтому здесь
    создаются только выходные фрагменты без управления жизненным циклом source.
    """
    return _convert_to_segments(
        source_path,
        output_dir,
        segment_seconds=PRIMARY_CHUNK_SECONDS,
        filename_pattern="chunk_%03d.mp3",
    )


def split_mp3_chunk(chunk_path: Path, output_dir: Path) -> list[Path]:
    """Повторно разделить крупный MP3 на самостоятельные десятиминутные части.

    Отдельный подкаталог на исходный chunk предотвращает перезапись частей,
    когда в одном вызове tool уменьшить приходится несколько фрагментов.
    Повторное кодирование сохраняет параметры контракта и не режет MP3 байтами.
    """
    split_dir = output_dir / f"{chunk_path.stem}_split"
    return _convert_to_segments(
        chunk_path,
        split_dir,
        segment_seconds=FALLBACK_CHUNK_SECONDS,
        filename_pattern="part_%03d.mp3",
    )

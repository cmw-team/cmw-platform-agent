"""RED tests for the FFprobe/FFmpeg media conversion boundary."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING, Any
import uuid

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Use a workspace-local temp dir because the system pytest dir is locked."""
    base = (Path.cwd() / ".scratch" / "pytest-stage1-fixtures").resolve()
    base.mkdir(parents=True, exist_ok=True)
    path = base / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        assert path.resolve().parent == base
        shutil.rmtree(path)


def _module() -> Any:
    return importlib.import_module("tools.media_tools.media_converter")


def _completed(args: list[str], *, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")


def test_ffprobe_command_uses_argument_list_without_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"media")
    calls: list[tuple[Any, dict[str, Any]]] = []

    def fake_run(args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        payload = json.dumps({"streams": [{"codec_type": "audio"}]})
        return _completed(args, stdout=payload)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.probe_media(source)

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert isinstance(args, list)
    assert Path(args[0]).name.lower() in {"ffprobe", "ffprobe.exe"}
    assert kwargs.get("shell", False) is False


def test_missing_ffprobe_raises_ffmpeg_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"media")

    def missing(*_args: Any, **_kwargs: Any) -> Any:
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(module.subprocess, "run", missing)

    with pytest.raises(module.FFmpegNotFoundError):
        module.probe_media(source)


def test_invalid_media_and_missing_audio_are_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.bin"
    source.write_bytes(b"not-media")

    def unreadable(args: list[str], **_kwargs: Any) -> Any:
        raise subprocess.CalledProcessError(1, args, stderr="invalid data")

    monkeypatch.setattr(module.subprocess, "run", unreadable)
    with pytest.raises(module.InvalidMediaError):
        module.probe_media(source)

    def video_only(args: list[str], **_kwargs: Any) -> Any:
        return _completed(args, stdout=json.dumps({"streams": [{"codec_type": "video"}]}))

    monkeypatch.setattr(module.subprocess, "run", video_only)
    with pytest.raises(module.AudioStreamNotFoundError):
        module.probe_media(source)


def test_conversion_command_sets_required_mp3_parameters_without_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"media")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(args: list[str], **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        for candidate in reversed(args):
            if "%" in str(candidate) and str(candidate).endswith(".mp3"):
                Path(str(candidate).replace("%03d", "000")).write_bytes(b"mp3")
                break
        return _completed(args)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    chunks = module.convert_to_mp3_chunks(source, tmp_path / "output")

    assert chunks
    args, kwargs = calls[-1]
    assert isinstance(args, list)
    assert Path(args[0]).name.lower() in {"ffmpeg", "ffmpeg.exe"}
    assert kwargs.get("shell", False) is False
    for option, value in (("-ac", "1"), ("-ar", "16000"), ("-b:a", "64k")):
        index = args.index(option)
        assert args[index + 1] == value
    assert "-vn" in args
    assert "-segment_time" in args
    assert args[args.index("-segment_time") + 1] == "1200"


def test_chunk_paths_preserve_source_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"media")

    def fake_run(args: list[str], **_kwargs: Any) -> Any:
        pattern = next(Path(value) for value in args if "%" in str(value))
        pattern.parent.mkdir(parents=True, exist_ok=True)
        for index in (2, 0, 1):
            Path(str(pattern).replace("%03d", f"{index:03d}")).write_bytes(b"mp3")
        return _completed(args)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    chunks = module.convert_to_mp3_chunks(source, tmp_path / "output")

    assert [path.name for path in chunks] == [
        "chunk_000.mp3",
        "chunk_001.mp3",
        "chunk_002.mp3",
    ]


def test_missing_ffmpeg_raises_ffmpeg_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"media")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("ffmpeg")),
    )

    with pytest.raises(module.FFmpegNotFoundError):
        module.convert_to_mp3_chunks(source, tmp_path / "output")


def test_failed_or_empty_conversion_raises_conversion_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"media")

    def failed(args: list[str], **_kwargs: Any) -> Any:
        raise subprocess.CalledProcessError(1, args, stderr="encoder failed")

    monkeypatch.setattr(module.subprocess, "run", failed)
    with pytest.raises(module.ConversionFailedError):
        module.convert_to_mp3_chunks(source, tmp_path / "failed")

    monkeypatch.setattr(module.subprocess, "run", lambda args, **_kwargs: _completed(args))
    with pytest.raises(module.ConversionFailedError):
        module.convert_to_mp3_chunks(source, tmp_path / "empty")


def test_split_mp3_chunk_uses_ffmpeg_and_returns_ordered_valid_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    chunk = tmp_path / "chunk.mp3"
    chunk.write_bytes(b"mp3")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> Any:
        calls.append(args)
        assert kwargs.get("shell", False) is False
        pattern = next(Path(value) for value in args if "%" in str(value))
        pattern.parent.mkdir(parents=True, exist_ok=True)
        for index in (1, 0):
            Path(str(pattern).replace("%03d", f"{index:03d}")).write_bytes(b"mp3-part")
        return _completed(args)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    parts = module.split_mp3_chunk(chunk, tmp_path / "split")

    assert calls
    assert [part.name for part in parts] == ["part_000.mp3", "part_001.mp3"]
    assert all(part.read_bytes() == b"mp3-part" for part in parts)

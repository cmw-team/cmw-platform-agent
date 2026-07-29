"""RED contract tests for the ``transcribe_uploaded_media`` LangChain tool."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any, ClassVar
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


class FakeAgent:
    """Minimal agent carrying a session file registry and session ID."""

    def __init__(self, files: dict[str, str], session_id: str = "session-1") -> None:
        self.files = files
        self.session_id = session_id
        self.lookup_calls: list[str] = []

    def get_file_path(self, original_filename: str) -> str | None:
        self.lookup_calls.append(original_filename)
        return self.files.get(original_filename)


def _tool_module() -> Any:
    return importlib.import_module(
        "tools.media_tools.tool_transcribe_uploaded_media"
    )


def _client_module() -> Any:
    return importlib.import_module(
        "tools.media_tools.polza_transcription_client"
    )


def test_default_transcription_model_is_turbo() -> None:
    """Default Polza route uses the agreed inexpensive transcription model."""
    assert (
        _tool_module().DEFAULT_TRANSCRIPTION_MODEL
        == "openai/whisper-large-v3-turbo"
    )


def _invoke(source: str, agent: FakeAgent) -> dict[str, Any]:
    return _tool_module().transcribe_uploaded_media.func(source=source, agent=agent)


def _write_upload(tmp_path: Path, name: str = "meeting.mp4") -> Path:
    upload = tmp_path / name
    upload.write_bytes(b"original-user-file")
    return upload


def _patch_environment_key(
    monkeypatch: pytest.MonkeyPatch,
    *,
    value: str | None = "environment-polza-key",
) -> None:
    if value is None:
        monkeypatch.delenv("POLZA_API_KEY", raising=False)
    else:
        monkeypatch.setenv("POLZA_API_KEY", value)


def _patch_successful_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    chunk_results: list[Any],
    created_chunks: list[Path] | None = None,
) -> type:
    module = _tool_module()
    client_module = _client_module()

    monkeypatch.setattr(module, "probe_media", lambda _path: None)

    def fake_convert(_source: Path, output_dir: Path) -> list[Path]:
        chunks: list[Path] = []
        for index in range(len(chunk_results)):
            chunk = output_dir / f"chunk_{index + 1:03d}.mp3"
            chunk.write_bytes(f"mp3-{index}".encode())
            chunks.append(chunk)
        if created_chunks is not None:
            created_chunks.extend(chunks)
        return chunks

    monkeypatch.setattr(module, "convert_to_mp3_chunks", fake_convert)

    class FakeClient:
        instances: ClassVar[list[FakeClient]] = []

        def __init__(self, api_key: str, base_url: str, model: str) -> None:
            self.api_key = api_key
            self.base_url = base_url
            self.model = model
            self.calls: list[Path] = []
            self.__class__.instances.append(self)

        def transcribe_chunk(self, chunk_path: Path) -> Any:
            self.calls.append(chunk_path)
            return chunk_results[len(self.calls) - 1]

    monkeypatch.setattr(module, "PolzaTranscriptionClient", FakeClient)
    _patch_environment_key(monkeypatch)
    assert client_module.ChunkTranscription
    return FakeClient


def test_openai_schema_exposes_only_source() -> None:
    from langchain_core.utils.function_calling import convert_to_openai_tool

    spec = convert_to_openai_tool(_tool_module().transcribe_uploaded_media)
    parameters = spec["function"]["parameters"]

    assert set(parameters["properties"]) == {"source"}
    assert parameters["required"] == ["source"]


def test_agent_is_injected_and_absent_from_schema() -> None:
    module = _tool_module()

    assert "agent" in module.transcribe_uploaded_media.args_schema.model_fields
    field = module.transcribe_uploaded_media.args_schema.model_fields["agent"]
    assert any(
        marker.__name__ == "InjectedToolArg"
        for marker in field.metadata
    )

    from langchain_core.utils.function_calling import convert_to_openai_tool

    properties = convert_to_openai_tool(module.transcribe_uploaded_media)["function"][
        "parameters"
    ]["properties"]
    assert "agent" not in properties


@pytest.mark.parametrize(
    "source",
    [
        "",
        "   ",
        "https://example.test/file.mp3",
        "/rooted-file.mp3",
        "C:\\x\\a.mp3",
        "dir/file.mp3",
        "..\\file.mp3",
    ],
)
def test_invalid_source_is_rejected(source: str) -> None:
    agent = FakeAgent({})

    result = _invoke(source, agent)

    assert result["success"] is False
    assert result["error"]["code"] == "invalid_source"
    assert agent.lookup_calls == []


def test_resolves_source_via_agent_file_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[result_type("Текст", 10.0, 0.1)],
    )
    agent = FakeAgent({upload.name: str(upload)})

    result = _invoke(upload.name, agent)

    assert result["success"] is True
    assert agent.lookup_calls == [upload.name]
    assert result["data"]["source"] == {
        "requested": upload.name,
        "source_type": "uploaded",
    }


@pytest.mark.parametrize("registered", [False, True])
def test_missing_uploaded_file_returns_file_not_found(
    tmp_path: Path,
    registered: bool,
) -> None:
    missing = tmp_path / "missing.mp4"
    files = {missing.name: str(missing)} if registered else {}
    agent = FakeAgent(files)

    result = _invoke(missing.name, agent)

    assert result["success"] is False
    assert result["error"]["code"] == "file_not_found"
    assert agent.lookup_calls == [missing.name]


@pytest.mark.parametrize(
    ("exception_name", "expected_code"),
    [
        ("FFmpegNotFoundError", "ffmpeg_not_found"),
        ("InvalidMediaError", "invalid_media"),
        ("AudioStreamNotFoundError", "audio_stream_not_found"),
        ("ConversionFailedError", "conversion_failed"),
    ],
)
def test_media_errors_are_mapped_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exception_name: str,
    expected_code: str,
) -> None:
    upload = _write_upload(tmp_path)
    module = _tool_module()
    converter = importlib.import_module("tools.media_tools.media_converter")
    exception_type = getattr(converter, exception_name)
    monkeypatch.setattr(
        module,
        "probe_media",
        lambda _path: (_ for _ in ()).throw(exception_type("internal detail")),
    )
    _patch_environment_key(monkeypatch)

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is False
    assert result["error"]["code"] == expected_code


def test_environment_api_key_is_used_by_transcription_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    fake_client = _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[result_type("Готово", 5.0, 0.02)],
    )
    monkeypatch.setenv("POLZA_API_KEY", "environment-secret")

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is True
    assert fake_client.instances[-1].api_key == "environment-secret"
    assert "environment-secret" not in json.dumps(result)


def test_ui_session_key_is_not_used_when_environment_key_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[result_type("Готово", 5.0, 0.02)],
    )
    monkeypatch.delenv("POLZA_API_KEY", raising=False)
    monkeypatch.setattr(
        _tool_module(),
        "get_session_config",
        lambda _session_id: {"llm_provider_api_keys": {"polza": "session-secret"}},
        raising=False,
    )
    agent = FakeAgent({upload.name: str(upload)}, session_id="wanted-session")

    result = _invoke(upload.name, agent)

    assert result["success"] is False
    assert result["error"]["code"] == "polza_api_key_missing"


def test_missing_environment_key_returns_polza_api_key_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    _patch_environment_key(monkeypatch, value=None)

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is False
    assert result["error"]["code"] == "polza_api_key_missing"


def test_chunk_transcripts_are_joined_in_order_and_usage_is_summed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    fake_client = _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[
            result_type("Первая часть", 10.5, 0.10),
            result_type("Вторая часть", 20.0, 0.20),
        ],
    )

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is True
    assert result["data"]["transcript"] == "Первая часть\n\nВторая часть"
    assert result["data"]["duration_seconds"] == pytest.approx(30.5)
    assert result["cost_rub"] == pytest.approx(0.30)
    assert result["data"]["chunk_count"] == 2
    assert "capabilities" not in result["data"]
    assert [path.name for path in fake_client.instances[-1].calls] == [
        "chunk_001.mp3",
        "chunk_002.mp3",
    ]


def test_successful_transcript_is_cached_for_current_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[result_type("Полный текст встречи", 5.0, 0.02)],
    )
    agent = FakeAgent(
        {upload.name: str(upload)},
        session_id="meeting-session",
    )

    result = _invoke(upload.name, agent)

    cache = importlib.import_module(
        "tools.media_tools.meeting_transcript_cache"
    )
    assert result["success"] is True
    assert cache.get_transcript(agent, upload.name) == "Полный текст встречи"


def test_missing_chunk_cost_returns_null_total_cost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[
            result_type("Один", 1.0, 0.01),
            result_type("Два", 2.0, None),
        ],
    )

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is True
    assert result["cost_rub"] is None


def test_oversized_chunk_is_resplit_before_transcription(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    module = _tool_module()
    client_module = _client_module()
    oversized = client_module.PayloadTooLargeError("too large")
    result_type = client_module.ChunkTranscription
    http_attempts: list[str] = []
    split_calls: list[str] = []

    monkeypatch.setattr(module, "probe_media", lambda _path: None)

    def fake_convert(_source: Path, output_dir: Path) -> list[Path]:
        chunk = output_dir / "chunk_001.mp3"
        chunk.write_bytes(b"large")
        return [chunk]

    def fake_split(chunk: Path, output_dir: Path) -> list[Path]:
        split_calls.append(chunk.name)
        parts = [output_dir / "part_001.mp3", output_dir / "part_002.mp3"]
        for part in parts:
            part.write_bytes(b"small")
        return parts

    class FakeClient:
        def __init__(self, api_key: str, base_url: str, model: str) -> None:
            del api_key, base_url, model

        def transcribe_chunk(self, chunk: Path) -> Any:
            http_attempts.append(chunk.name)
            if chunk.name == "chunk_001.mp3":
                raise oversized
            return result_type(chunk.stem, 1.0, 0.01)

    monkeypatch.setattr(module, "convert_to_mp3_chunks", fake_convert)
    monkeypatch.setattr(module, "split_mp3_chunk", fake_split)
    monkeypatch.setattr(module, "PolzaTranscriptionClient", FakeClient)
    _patch_environment_key(monkeypatch)

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is True
    assert split_calls == ["chunk_001.mp3"]
    assert http_attempts == ["chunk_001.mp3", "part_001.mp3", "part_002.mp3"]
    assert result["data"]["transcript"] == "part_001\n\npart_002"


def test_failed_chunk_makes_whole_call_fail_without_partial_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    module = _tool_module()
    client_module = _client_module()
    result_type = client_module.ChunkTranscription
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[
            result_type("Успешная первая часть", 3.0, 0.01),
            client_module.PolzaUnavailableError("temporary failure"),
        ],
    )
    original_client = module.PolzaTranscriptionClient

    class FailingSecondClient(original_client):
        def transcribe_chunk(self, chunk_path: Path) -> Any:
            item = self.calls.__len__()
            self.calls.append(chunk_path)
            result = self.__class_result(item)
            if isinstance(result, Exception):
                raise result
            return result

        @staticmethod
        def __class_result(index: int) -> Any:
            return [
                result_type("Успешная первая часть", 3.0, 0.01),
                client_module.PolzaUnavailableError("temporary failure"),
            ][index]

    monkeypatch.setattr(module, "PolzaTranscriptionClient", FailingSecondClient)

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert result["success"] is False
    assert result["data"] is None
    assert result["error"]["code"] == "polza_unavailable"
    assert "Успешная первая часть" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("fail", [False, True])
def test_temporary_files_are_cleaned_and_source_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fail: bool,
) -> None:
    upload = _write_upload(tmp_path)
    original = upload.read_bytes()
    created_chunks: list[Path] = []
    client_module = _client_module()
    result = (
        client_module.PolzaUnavailableError("failure")
        if fail
        else client_module.ChunkTranscription("Текст", 1.0, 0.01)
    )
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[result],
        created_chunks=created_chunks,
    )
    if fail:
        module = _tool_module()
        base = module.PolzaTranscriptionClient

        class FailingClient(base):
            def transcribe_chunk(self, chunk_path: Path) -> Any:
                self.calls.append(chunk_path)
                raise client_module.PolzaUnavailableError("failure")

        monkeypatch.setattr(module, "PolzaTranscriptionClient", FailingClient)

    _invoke(upload.name, FakeAgent({upload.name: str(upload)}))

    assert upload.exists()
    assert upload.read_bytes() == original
    assert created_chunks
    assert all(not chunk.exists() for chunk in created_chunks)


def test_errors_and_logs_redact_sensitive_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    upload = _write_upload(tmp_path)
    module = _tool_module()
    client_module = _client_module()
    environment_value = "env-" + "test-value"
    base64_audio = "data:audio/mp3;base64,QUJDREVGRw=="
    raw = (
        f"Authorization: Bearer {environment_value} {base64_audio} {upload} Traceback"
    )
    monkeypatch.setattr(module, "probe_media", lambda _path: None)

    def fake_convert(_source: Path, output_dir: Path) -> list[Path]:
        chunk = output_dir / "chunk.mp3"
        chunk.write_bytes(b"audio")
        return [chunk]

    class FailingClient:
        def __init__(self, api_key: str, base_url: str, model: str) -> None:
            del api_key, base_url, model

        def transcribe_chunk(self, _chunk: Path) -> Any:
            raise client_module.PolzaTranscriptionError(raw)

    monkeypatch.setattr(module, "convert_to_mp3_chunks", fake_convert)
    monkeypatch.setattr(module, "PolzaTranscriptionClient", FailingClient)
    monkeypatch.setenv("POLZA_API_KEY", environment_value)

    result = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))
    rendered = json.dumps(result, ensure_ascii=False) + caplog.text

    for forbidden in (
        environment_value,
        "Authorization",
        "base64",
        str(upload),
        "Traceback",
    ):
        assert forbidden not in rendered


def test_tool_response_is_json_serializable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = _write_upload(tmp_path)
    result_type = _client_module().ChunkTranscription
    _patch_successful_pipeline(
        monkeypatch,
        chunk_results=[result_type("Текст", 1.25, None)],
    )

    success = _invoke(upload.name, FakeAgent({upload.name: str(upload)}))
    failure = _invoke("missing.mp3", FakeAgent({}))

    json.dumps(success, ensure_ascii=False)
    json.dumps(failure, ensure_ascii=False)

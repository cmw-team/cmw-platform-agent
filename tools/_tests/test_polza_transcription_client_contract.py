"""RED contract tests for the Polza audio transcription client."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
import shutil
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


BASE_URL = "https://polza.example/api/v1"
MODEL = "openai/whisper-large-v3-turbo"
API_KEY = "test-session-key"


def _module() -> Any:
    return importlib.import_module(
        "tools.media_tools.polza_transcription_client"
    )


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._payload


def _client() -> Any:
    return _module().PolzaTranscriptionClient(API_KEY, BASE_URL, MODEL)


def _audio(tmp_path: Path, *, size: int = 8) -> Path:
    path = tmp_path / "chunk.mp3"
    path.write_bytes(b"a" * size)
    return path


def _patch_post(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[FakeResponse | Exception],
) -> list[dict[str, Any]]:
    module = _module()
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(module.requests, "post", fake_post)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    return calls


def test_polza_payload_uses_fixed_model_russian_and_data_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_post(
        monkeypatch,
        [FakeResponse(200, {"text": "Текст", "usage": {"durationSeconds": 2.5}})],
    )

    result = _client().transcribe_chunk(_audio(tmp_path))

    assert result.text == "Текст"
    assert len(calls) == 1
    request = calls[0]
    assert request["url"] == f"{BASE_URL}/audio/transcriptions"
    assert request["headers"]["Authorization"] == f"Bearer {API_KEY}"
    assert request["headers"]["Content-Type"] == "application/json"
    payload = json.loads(request["data"].decode("utf-8"))
    assert payload["language"] == "ru"
    assert payload["response_format"] == "json"
    assert payload["model"] == MODEL
    assert payload["file"].startswith("data:audio/mp3;base64,")


def test_payload_size_is_limited_before_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    calls = _patch_post(monkeypatch, [])
    # 10.6 MB binary data expands beyond the 14 MB serialized JSON limit.
    chunk = _audio(tmp_path, size=10_600_000)

    with pytest.raises(module.PayloadTooLargeError):
        _client().transcribe_chunk(chunk)

    assert calls == []


@pytest.mark.parametrize("status", [400, 401, 402, 403])
def test_non_retryable_http_errors_have_one_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    module = _module()
    expected = {
        400: module.PolzaInvalidRequestError,
        401: module.PolzaAuthenticationError,
        402: module.PolzaInsufficientFundsError,
        403: module.PolzaAuthenticationError,
    }[status]
    calls = _patch_post(monkeypatch, [FakeResponse(status, {"error": "safe"})])

    with pytest.raises(expected):
        _client().transcribe_chunk(_audio(tmp_path))

    assert len(calls) == 1


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_retryable_errors_are_retried_at_most_three_times(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    module = _module()
    expected = (
        module.PolzaRateLimitError if status == 429 else module.PolzaUnavailableError
    )
    calls = _patch_post(
        monkeypatch,
        [FakeResponse(status, {"error": "temporary"}) for _ in range(3)],
    )

    with pytest.raises(expected):
        _client().transcribe_chunk(_audio(tmp_path))

    assert len(calls) == 3


def test_retry_stops_after_later_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_post(
        monkeypatch,
        [
            FakeResponse(502, {"error": "temporary"}),
            FakeResponse(
                200,
                {
                    "text": "Восстановлено",
                    "usage": {"durationSeconds": 4.0, "cost_rub": 0.04},
                },
            ),
        ],
    )

    result = _client().transcribe_chunk(_audio(tmp_path))

    assert result.text == "Восстановлено"
    assert len(calls) == 2


def test_response_maps_duration_and_cost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_post(
        monkeypatch,
        [
            FakeResponse(
                200,
                {
                    "text": "Результат",
                    "usage": {"durationSeconds": 12.75, "cost_rub": 0.15},
                },
            )
        ],
    )

    result = _client().transcribe_chunk(_audio(tmp_path))

    assert result == _module().ChunkTranscription("Результат", 12.75, 0.15)


def test_top_level_duration_is_used_when_usage_duration_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_post(
        monkeypatch,
        [
            FakeResponse(
                200,
                {
                    "text": "Результат",
                    "duration": 9.25,
                    "usage": {"cost_rub": 0.12},
                },
            )
        ],
    )

    result = _client().transcribe_chunk(_audio(tmp_path))

    assert result == _module().ChunkTranscription("Результат", 9.25, 0.12)


def test_response_diagnostics_log_only_field_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = _module()
    transcript_marker = "PRIVATE_TRANSCRIPT_VALUE"
    usage_marker = "PRIVATE_USAGE_VALUE"
    caplog.set_level(logging.DEBUG, logger=module.__name__)
    _patch_post(
        monkeypatch,
        [
            FakeResponse(
                200,
                {
                    "text": transcript_marker,
                    "duration": 3.0,
                    "usage": {
                        "provider_specific_field": usage_marker,
                    },
                },
                headers={"x-provider-cost": "SECRET_HEADER_VALUE"},
            )
        ],
    )

    _client().transcribe_chunk(_audio(tmp_path))

    assert "duration" in caplog.text
    assert "provider_specific_field" in caplog.text
    assert "x-provider-cost" in caplog.text
    assert transcript_marker not in caplog.text
    assert usage_marker not in caplog.text
    assert "SECRET_HEADER_VALUE" not in caplog.text


def test_missing_cost_is_none_instead_of_estimated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_post(
        monkeypatch,
        [FakeResponse(200, {"text": "Результат", "usage": {"durationSeconds": 1.0}})],
    )

    result = _client().transcribe_chunk(_audio(tmp_path))

    assert result.cost_rub is None


def test_usage_cost_is_used_as_ruble_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_post(
        monkeypatch,
        [
            FakeResponse(
                200,
                {
                    "text": "Результат",
                    "duration": 2.0,
                    "usage": {"cost": 0.08},
                },
            )
        ],
    )

    result = _client().transcribe_chunk(_audio(tmp_path))

    assert result.cost_rub == pytest.approx(0.08)


@pytest.mark.parametrize(
    "payload",
    [{}, {"text": ""}, {"text": "   "}, {"unexpected": "value"}],
)
def test_success_without_nonempty_text_is_invalid_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    module = _module()
    _patch_post(monkeypatch, [FakeResponse(200, payload)])

    with pytest.raises(module.PolzaInvalidResponseError):
        _client().transcribe_chunk(_audio(tmp_path))


def test_client_does_not_expose_key_or_base64_in_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = _module()
    raw = f"Authorization: Bearer {API_KEY} data:audio/mp3;base64,QUJD Traceback"
    calls = _patch_post(monkeypatch, [RuntimeError(raw) for _ in range(3)])

    with pytest.raises(module.PolzaUnavailableError) as captured:
        _client().transcribe_chunk(_audio(tmp_path))

    rendered = str(captured.value) + caplog.text
    assert len(calls) == 3
    for forbidden in (API_KEY, "Authorization", "base64", "Traceback"):
        assert forbidden not in rendered

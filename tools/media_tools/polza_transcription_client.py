# ruff: noqa: RUF002, RUF003
"""HTTP-клиент Polza AI для транскрибации одного готового MP3-фрагмента.

Модуль ничего не знает о UI-сессиях и не ищет API key самостоятельно. Будущий
LangChain tool передаст ключ текущей сессии в конструктор, а клиент использует
его только в HTTPS-заголовке и не выводит в сообщения или журнал.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from pathlib import Path


MAX_JSON_BODY_BYTES = 14_000_000
REQUEST_TIMEOUT_SECONDS = 180
MAX_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
_LOGGER = logging.getLogger(__name__)
_MAX_PROVIDER_ERROR_DETAIL_CHARS = 500
_SENSITIVE_ERROR_MARKERS = (
    "authorization",
    "bearer ",
    "api key",
    "api_key",
    "base64",
    "data:audio",
)
_LONG_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9+/=_-]{64,}")


class PolzaTranscriptionError(RuntimeError):
    """Базовая безопасная ошибка клиента транскрибации Polza."""


class PayloadTooLargeError(PolzaTranscriptionError):
    """Сериализованный JSON превышает согласованный проектный предел."""


class PolzaAuthenticationError(PolzaTranscriptionError):
    """Polza отклонила API key с кодом 401 или 403."""


class PolzaInsufficientFundsError(PolzaTranscriptionError):
    """На балансе Polza недостаточно средств для транскрибации."""


class PolzaInvalidRequestError(PolzaTranscriptionError):
    """Polza отклонила сформированный запрос с кодом 400."""


class PolzaRateLimitError(PolzaTranscriptionError):
    """Polza продолжила возвращать 429 после допустимых попыток."""


class PolzaUnavailableError(PolzaTranscriptionError):
    """Временная сетевая или серверная ошибка сохранилась после повторов."""


class PolzaInvalidResponseError(PolzaTranscriptionError):
    """Успешный HTTP-ответ не содержит ожидаемой транскрибации."""


@dataclass(frozen=True)
class ChunkTranscription:
    """Нормализованный результат транскрибации одного MP3-фрагмента."""

    text: str
    duration_seconds: float
    cost_rub: float | None


class PolzaTranscriptionClient:
    """Последовательно и безопасно отправляет один MP3 в Audio API Polza."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        """Сохранить серверные параметры без обращения к env или UI.

        Ключ хранится только внутри экземпляра. Удаление завершающего слеша у
        base URL предотвращает появление двойного слеша перед endpoint.
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    def _build_serialized_body(self, chunk_path: Path) -> bytes:
        """Прочитать MP3 и сформировать точное UTF-8 тело будущего запроса.

        Проверяется именно сериализованный JSON, а не исходный MP3: Base64
        увеличивает объём примерно на треть, и служебные поля тоже входят в
        лимит Polza. Слишком большой фрагмент не доходит до сетевого вызова.
        """
        try:
            audio_bytes = chunk_path.read_bytes()
        except OSError:
            raise PolzaTranscriptionError(
                "Не удалось прочитать MP3-фрагмент для транскрибации."
            ) from None

        encoded = base64.b64encode(audio_bytes).decode("ascii")
        payload = {
            "model": self._model,
            "file": f"data:audio/mp3;base64,{encoded}",
            "language": "ru",
            "response_format": "json",
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(serialized) > MAX_JSON_BODY_BYTES:
            raise PayloadTooLargeError(
                "MP3-фрагмент превышает допустимый размер тела запроса."
            )
        return serialized

    def _post(self, body: bytes) -> requests.Response:
        """Выполнить до трёх HTTP-попыток без раскрытия содержимого запроса.

        Повторы разрешены только для временных статусов и сетевых сбоев.
        Исключение сторонней библиотеки намеренно не включается в итоговую
        ошибку: оно может содержать Authorization, Base64 или сетевые детали.
        """
        url = f"{self._base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    data=body,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            except Exception:
                # Граница HTTP должна также обезвредить неожиданную ошибку
                # транспорта: наружу нельзя передавать её сырой текст.
                if attempt == MAX_ATTEMPTS:
                    raise PolzaUnavailableError(
                        "Сервис транскрибации Polza временно недоступен."
                    ) from None
                time.sleep(float(attempt))
                continue

            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            if attempt == MAX_ATTEMPTS:
                return response

            # Небольшая линейная задержка не блокирует первый запрос и уменьшает
            # вероятность мгновенно повторить временно перегруженный endpoint.
            time.sleep(float(attempt))

        raise PolzaUnavailableError(
            "Сервис транскрибации Polza временно недоступен."
        )

    @staticmethod
    def _raise_for_http_status(status_code: int) -> None:
        """Преобразовать HTTP-код в согласованное безопасное исключение."""
        if status_code == 400:
            raise PolzaInvalidRequestError("Polza отклонила запрос транскрибации.")
        if status_code in {401, 403}:
            raise PolzaAuthenticationError("Polza отклонила API key текущей сессии.")
        if status_code == 402:
            raise PolzaInsufficientFundsError(
                "На балансе Polza недостаточно средств."
            )
        if status_code == 429:
            raise PolzaRateLimitError("Polza исчерпала лимит запросов.")
        if status_code in RETRYABLE_STATUS_CODES:
            raise PolzaUnavailableError(
                "Сервис транскрибации Polza временно недоступен."
            )
        if not 200 <= status_code < 300:
            raise PolzaTranscriptionError("Polza не выполнила транскрибацию.")

    def _safe_provider_error_detail(self, response: requests.Response) -> str:
        """Извлечь диагностическое сообщение без секретов и аудиоданных.

        Polza может возвращать причину HTTP 400 в нескольких JSON-полях.
        Наружу допускается только короткая однострочная строка. Подозрительно
        длинные значения, data URL, Base64, Authorization и сам API key
        заменяются маркером, чтобы диагностика не раскрывала запрос.
        """
        try:
            payload = response.json()
        except (ValueError, TypeError):
            return "<unavailable>"
        if not isinstance(payload, Mapping):
            return "<unavailable>"

        candidates: list[Any] = []
        error = payload.get("error")
        if isinstance(error, Mapping):
            candidates.extend(
                error.get(field) for field in ("message", "detail", "code", "type")
            )
        else:
            candidates.append(error)
        candidates.extend(payload.get(field) for field in ("message", "detail"))

        raw_detail = next(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, str) and candidate.strip()
            ),
            None,
        )
        if raw_detail is None:
            return "<unavailable>"

        detail = " ".join(raw_detail.split())
        lowered = detail.lower()
        contains_secret = bool(self._api_key and self._api_key in detail)
        contains_sensitive_marker = any(
            marker in lowered for marker in _SENSITIVE_ERROR_MARKERS
        )
        if (
            len(detail) > _MAX_PROVIDER_ERROR_DETAIL_CHARS
            or contains_secret
            or contains_sensitive_marker
            or _LONG_TOKEN_PATTERN.search(detail)
        ):
            return "<redacted>"
        return detail

    @staticmethod
    def _number(
        value: Any,
        *,
        field_name: str,
        default: float | None,
    ) -> float | None:
        """Безопасно нормализовать числовое usage-поле внешнего ответа."""
        if value is None:
            return default
        invalid_message = f"Polza вернула некорректное поле {field_name}."
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PolzaInvalidResponseError(invalid_message)
        number = float(value)
        if number < 0:
            raise PolzaInvalidResponseError(invalid_message)
        return number

    @classmethod
    def _parse_success(cls, response: requests.Response) -> ChunkTranscription:
        """Проверить JSON Polza и вернуть минимальный типизированный результат."""
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise PolzaInvalidResponseError(
                "Polza вернула некорректный ответ транскрибации."
            ) from None
        if not isinstance(payload, dict):
            raise PolzaInvalidResponseError(
                "Polza вернула некорректный ответ транскрибации."
            )

        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise PolzaInvalidResponseError(
                "Ответ Polza не содержит текста транскрибации."
            )

        usage = payload.get("usage")
        if usage is None:
            usage = {}
        if not isinstance(usage, dict):
            raise PolzaInvalidResponseError("Polza вернула некорректное usage-поле.")

        # Для диагностики расхождений между документацией и конкретным
        # провайдером фиксируются только имена полей. Значения намеренно не
        # логируются: среди них находятся транскрипт, стоимость и иные данные
        # пользовательского запроса.
        response_headers = getattr(response, "headers", {})
        header_fields = (
            sorted(str(field) for field in response_headers)
            if isinstance(response_headers, Mapping)
            else []
        )
        _LOGGER.debug(
            "Polza transcription response fields: top_level=%s usage=%s headers=%s",
            sorted(str(field) for field in payload),
            sorted(str(field) for field in usage),
            header_fields,
        )

        # Документация Polza показывает длительность в двух местах. Приоритет
        # имеет usage.durationSeconds, а верхнеуровневый duration используется
        # для моделей, которые возвращают сокращённую структуру usage.
        duration_value = usage.get("durationSeconds")
        if duration_value is None:
            duration_value = payload.get("duration")
        duration = cls._number(
            duration_value,
            field_name="durationSeconds/duration",
            default=0.0,
        )

        # В API Polza фактическая стоимость в рублях документирована как
        # cost_rub. Поле cost используется только как официальный fallback:
        # существующий механизм учёта Polza в проекте применяет тот же порядок.
        cost_value = usage.get("cost_rub")
        if cost_value is None:
            cost_value = usage.get("cost")
        cost = cls._number(
            cost_value,
            field_name="cost_rub/cost",
            default=None,
        )
        assert duration is not None
        return ChunkTranscription(
            text=text,
            duration_seconds=duration,
            cost_rub=cost,
        )

    def transcribe_chunk(self, chunk_path: Path) -> ChunkTranscription:
        """Транскрибировать один MP3, не сокращая и не изменяя текст ответа."""
        body = self._build_serialized_body(chunk_path)
        response = self._post(body)
        if response.status_code == 400:
            _LOGGER.warning(
                "Polza transcription rejected request: status=400 detail=%s",
                self._safe_provider_error_detail(response),
            )
        self._raise_for_http_status(response.status_code)
        return self._parse_success(response)

"""Contract tests for the model-facing ``get_record_values`` tool."""

from __future__ import annotations

import importlib
from typing import Any

from pydantic import ValidationError
import pytest


def _tool_module() -> Any:
    return importlib.import_module(
        "tools.templates_tools.tool_get_record_values"
    )


def test_batch_input_is_sent_and_returned_by_record_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _tool_module()
    captured: dict[str, Any] = {}

    def fake_post_request(body: dict[str, Any], endpoint: str) -> dict[str, Any]:
        captured["body"] = body
        captured["endpoint"] = endpoint
        return {
            "success": True,
            "status_code": 200,
            "raw_response": {
                "response": {
                    "lead-1": {"Kompaniya": "Example"},
                    "lead-2": {"Kompaniya": None},
                }
            },
        }

    monkeypatch.setattr(module, "_post_request", fake_post_request)

    result = module.get_record_values.invoke(
        {
            "record_ids": [" lead-1 ", "lead-2"],
            "attribute_system_names": ["Kompaniya"],
        }
    )

    assert captured == {
        "body": {
            "objects": ["lead-1", "lead-2"],
            "propertiesByAlias": ["Kompaniya"],
        },
        "endpoint": module.GET_PROPERTY_VALUES,
    }
    assert result == {
        "success": True,
        "status_code": 200,
        "data": {
            "lead-1": {"Kompaniya": "Example"},
            "lead-2": {"Kompaniya": None},
        },
        "error": None,
    }


def test_missing_record_in_successful_response_gets_empty_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _tool_module()
    monkeypatch.setattr(
        module,
        "_post_request",
        lambda _body, _endpoint: {
            "success": True,
            "status_code": 200,
            "raw_response": {"response": {"record-1": {"Area": "area-1"}}},
        },
    )

    result = module.get_record_values.invoke(
        {
            "record_ids": ["record-1", "record-2"],
            "attribute_system_names": ["Area"],
        }
    )

    assert result["data"] == {
        "record-1": {"Area": "area-1"},
        "record-2": {},
    }


@pytest.mark.parametrize(
    "record_ids",
    [
        [],
        [""],
        ["   "],
        ["record-1", ""],
    ],
)
def test_schema_rejects_empty_record_ids(record_ids: list[str]) -> None:
    module = _tool_module()

    with pytest.raises(ValidationError):
        module.get_record_values.invoke(
            {
                "record_ids": record_ids,
                "attribute_system_names": ["Kompaniya"],
            }
        )


def test_transport_error_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _tool_module()
    monkeypatch.setattr(
        module,
        "_post_request",
        lambda _body, _endpoint: {
            "success": False,
            "status_code": 503,
            "error": "Connection error",
        },
    )

    result = module.get_record_values.invoke(
        {
            "record_ids": ["record-1"],
            "attribute_system_names": ["Kompaniya"],
        }
    )

    assert result == {
        "success": False,
        "status_code": 503,
        "data": None,
        "error": "Connection error",
    }


def test_unexpected_response_shape_returns_contract_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _tool_module()
    monkeypatch.setattr(
        module,
        "_post_request",
        lambda _body, _endpoint: {
            "success": True,
            "status_code": 200,
            "raw_response": {"response": []},
        },
    )

    result = module.get_record_values.invoke(
        {
            "record_ids": ["record-1"],
            "attribute_system_names": ["Kompaniya"],
        }
    )

    assert result == {
        "success": False,
        "status_code": 200,
        "data": None,
        "error": "Unexpected GetPropertyValues response shape",
    }

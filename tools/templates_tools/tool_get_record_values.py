"""LangChain tool: read attribute values for records (GetPropertyValues).

After the 2026-07 cleanup, ``tools.platform_record_document`` was removed.
The HTTP call is inlined here using the lower-level
:func:`tools.requests_._post_request` transport so the response shape
(``{success, status_code, data: {record_id: {attr: value, ...}}, error}``)
matches the previous tool contract exactly.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from tools.requests_ import _post_request

GET_PROPERTY_VALUES = (
    "api/public/system/TeamNetwork/ObjectService/GetPropertyValues"
)


def _unwrap_webapi_payload(raw: Any) -> Any:
    """Unwrap ``{"response": X}`` from WebApi-style JSON."""
    if isinstance(raw, dict) and "response" in raw:
        return raw["response"]
    return raw


def _fetch_record_field_values(
    record_ids: list[str],
    attribute_system_names: list[str],
) -> dict[str, Any]:
    """
    Load selected attribute values for records (TeamNetwork GetPropertyValues).

    Returns:
        success, data: ``{record_id: {attr_alias: value, ...}}`` or error.
    """
    body: dict[str, Any] = {
        "objects": list(record_ids),
        "propertiesByAlias": list(attribute_system_names),
    }
    result = _post_request(body, GET_PROPERTY_VALUES)
    if not result.get("success"):
        return {
            "success": False,
            "status_code": int(result.get("status_code", 0) or 0),
            "data": None,
            "error": result.get("error") or "Request failed",
        }
    raw = result.get("raw_response")
    inner = _unwrap_webapi_payload(raw)
    if not isinstance(inner, dict):
        return {
            "success": False,
            "status_code": int(result.get("status_code", 0) or 0),
            "data": None,
            "error": "Unexpected GetPropertyValues response shape",
        }
    rows: dict[str, dict[str, Any]] = {}
    for record_id in record_ids:
        row = inner.get(record_id, {})
        rows[record_id] = row if isinstance(row, dict) else {}
    return {
        "success": True,
        "status_code": int(result.get("status_code", 0) or 0),
        "data": rows,
        "error": None,
    }


class GetRecordValuesSchema(BaseModel):
    record_ids: list[str] = Field(min_length=1, description="Record IDs to read.")
    attribute_system_names: list[str] = Field(
        min_length=1,
        description=(
            "At least one attribute system name. GetPropertyValues with an empty list does not "
            "return all fields on the platform (typically only id); list_attributes first if needed."
        ),
    )

    @field_validator("record_ids")
    @classmethod
    def strip_record_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            msg = "record_ids must contain only non-empty strings"
            raise ValueError(msg)
        return normalized


@tool(
    "get_record_values",
    return_direct=False,
    args_schema=GetRecordValuesSchema,
)
def get_record_values(
    record_ids: list[str], attribute_system_names: list[str]
) -> dict[str, Any]:
    """
    Get current attribute values for one or more records by system name.
    """
    return _fetch_record_field_values(record_ids, attribute_system_names)


__all__ = [
    "GetRecordValuesSchema",
    "get_record_values",
]

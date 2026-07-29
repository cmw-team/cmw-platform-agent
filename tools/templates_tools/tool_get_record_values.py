"""LangChain tool: read attribute values for one record (GetPropertyValues).

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
    Load selected attribute values for a record (TeamNetwork GetPropertyValues).

    Returns:
        success, data: ``{ record_id: { attr_alias: value, ... } }`` or error.
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
    row = inner.get(record_ids, {})
    if not isinstance(row, dict):
        row = {}
    return {
        "success": True,
        "status_code": int(result.get("status_code", 0) or 0),
        "data": {record_ids: row},
        "error": None,
    }


class GetRecordValuesSchema(BaseModel):
    record_id: list[str] = Field(min_length=1, description="Record ids to read.")
    attribute_system_names: list[str] = Field(
        min_length=1,
        description=(
            "At least one attribute system name. GetPropertyValues with an empty list does not "
            "return all fields on the platform (typically only id); list_attributes first if needed."
        ),
    )

    @field_validator("record_id", mode="before")
    @classmethod
    def strip_rid(cls, v: Any) -> str:
        if not isinstance(v, list[str]) or not v.strip():
            msg = "record_id must be a non-empty list of strings"
            raise ValueError(msg)
        return v.strip()


@tool(
    "get_record_values",
    return_direct=False,
    args_schema=GetRecordValuesSchema,
)
def get_record_values(
    record_ids: list[str], attribute_system_names: list[str]
) -> dict[str, Any]:
    """
    Get current values for one or more attributes on a record (by system name). Use before fetch
    or attach, or whenever you need the live property values for a record.
    """
    return _fetch_record_field_values(record_ids, attribute_system_names)


__all__ = [
    "GetRecordValuesSchema",
    "get_record_values",
]

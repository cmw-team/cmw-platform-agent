"""LangChain tool: extract structured text from every slide of a PPTX.

Source resolution follows ``.scratch/extract_presentation_slides-contract.md``:

* ``default-product-deck`` and ``default-case-library`` resolve to runtime
  resources stored in ``resources/presentations/``.
* Any other value is treated as the original filename of a PPTX uploaded into
  the current user session and resolved through ``agent.get_file_path``.

The tool never accepts a physical path from the model and never returns
physical paths, stack traces, or secrets to the model.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

from tools.presentation_tools.presentation_parser import (
    CorruptedPresentationError,
    parse_presentation,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRESENTATIONS_DIR = REPO_ROOT / "resources" / "presentations"

DEFAULT_SOURCE_FILES: dict[str, str] = {
    "default-product-deck": "Comindware Platform 6.pptx",
    "default-case-library": "Comindware Кейсы_1.7.pptx",
}

PPTX_SUFFIX = ".pptx"

_INVALID_SOURCE_MESSAGE = (
    "Invalid 'source' value: expected the original PPTX filename uploaded in "
    "the current session or one of the default aliases "
    "(default-product-deck, default-case-library)."
)
_UNKNOWN_ALIAS_MESSAGE = (
    "Unknown default alias: only 'default-product-deck' and "
    "'default-case-library' are supported."
)
_FILE_NOT_FOUND_MESSAGE = (
    "File is not registered in the current session."
)
_DEFAULT_SOURCE_MISSING_MESSAGE = (
    "Configured default presentation is missing on the server."
)
_UNSUPPORTED_FORMAT_MESSAGE = (
    "Only .pptx files are supported by this tool."
)
_CORRUPTED_MESSAGE = (
    "The file is not a readable PPTX presentation."
)
_EXTRACTION_FAILED_MESSAGE = (
    "Failed to extract slides from the presentation."
)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def _success(data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def _looks_like_path(value: str) -> bool:
    if not value:
        return False
    if value != value.strip():
        return True
    if "/" in value or "\\" in value:
        return True
    if value in {".", ".."}:
        return True
    if value.startswith(("./", ".\\")):
        return True
    if value.startswith(("../", "..\\")):
        return True
    return len(value) >= 2 and value[1] == ":" and value[0].isalpha()


def _classify_source(source: object) -> tuple[str, str] | tuple[None, tuple[str, str]]:
    """Validate *source* and return ``(requested_name, kind)``.

    On failure, returns ``(None, (message, code))`` so the caller can map it
    directly to an error envelope without exception-driven control flow.
    ``kind`` is ``"default"`` or ``"uploaded"`` on success.
    """
    if not isinstance(source, str):
        return None, (_INVALID_SOURCE_MESSAGE, "invalid_source")
    stripped = source.strip()
    if not stripped:
        return None, (_INVALID_SOURCE_MESSAGE, "invalid_source")
    if _looks_like_path(stripped):
        return None, (_INVALID_SOURCE_MESSAGE, "invalid_source")

    if stripped.lower().startswith("default-"):
        canonical = stripped.lower()
        if canonical == "default-":
            return None, (_INVALID_SOURCE_MESSAGE, "invalid_source")
        if canonical not in DEFAULT_SOURCE_FILES:
            return None, (_UNKNOWN_ALIAS_MESSAGE, "unknown_source")
        return canonical, "default"

    if Path(stripped).suffix.lower() != PPTX_SUFFIX:
        return None, (_UNSUPPORTED_FORMAT_MESSAGE, "unsupported_format")
    return stripped, "uploaded"


def _resolve_path(
    requested: str,
    kind: str,
    agent: Any,
) -> tuple[Path | None, str | None, str | None]:
    """Resolve the requested source to a real on-disk path.

    Returns ``(path, error_code, error_message)``. Exactly one of *path* and
    *error_code* is non-``None``.
    """
    if kind == "default":
        filename = DEFAULT_SOURCE_FILES[requested]
        path = DEFAULT_PRESENTATIONS_DIR / filename
        if not path.is_file():
            return None, "default_source_missing", _DEFAULT_SOURCE_MISSING_MESSAGE
        if path.suffix.lower() != PPTX_SUFFIX:
            return None, "corrupted_presentation", _CORRUPTED_MESSAGE
        return path, None, None

    path_value: Any = None
    if agent is not None and hasattr(agent, "get_file_path"):
        path_value = agent.get_file_path(requested)
    if not path_value or not isinstance(path_value, (str, Path)):
        return None, "file_not_found", _FILE_NOT_FOUND_MESSAGE
    path = Path(path_value)
    if not path.is_file():
        return None, "file_not_found", _FILE_NOT_FOUND_MESSAGE
    if path.suffix.lower() != PPTX_SUFFIX:
        return None, "unsupported_format", _UNSUPPORTED_FORMAT_MESSAGE
    return path, None, None


class ExtractPresentationSlidesSchema(BaseModel):
    source: str = Field(
        description=(
            "Exact original filename of a PPTX uploaded in the current session, "
            "or 'default-product-deck', or 'default-case-library'."
        )
    )
    agent: Annotated[
        Any | None, InjectedToolArg
    ] = Field(
        default=None,
        description="Runtime-injected agent; never supplied by the model.",
    )


@tool(
    "extract_presentation_slides",
    args_schema=ExtractPresentationSlidesSchema,
    return_direct=False,
)
def extract_presentation_slides(
    source: str,
    agent: Annotated[Any | None, InjectedToolArg] = None,
) -> dict[str, Any]:
    """Read every slide of a PPTX and return its structured text and metadata.

    The tool does not score, summarise, or rewrite slides and never sends the
    presentation to an external service. ``source`` must be either a default
    alias (``default-product-deck`` / ``default-case-library``) or the exact
    original filename of a PPTX uploaded in the current session.
    """
    classification = _classify_source(source)
    if classification[0] is None:
        message, code = classification[1]
        return _error(code, message)
    requested, kind = classification

    path, error_code, error_message = _resolve_path(requested, kind, agent)
    if path is None:
        return _error(error_code, error_message)

    try:
        parsed = parse_presentation(path)
    except CorruptedPresentationError:
        return _error("corrupted_presentation", _CORRUPTED_MESSAGE)
    except Exception:
        logger.exception(
            "Unexpected failure while extracting slides from '%s'", requested
        )
        return _error("extraction_failed", _EXTRACTION_FAILED_MESSAGE)

    resolved_name = (
        DEFAULT_SOURCE_FILES[requested]
        if kind == "default"
        else requested
    )

    data = {
        "source": {
            "requested": requested,
            "resolved_name": resolved_name,
            "source_type": kind,
        },
        **parsed,
    }
    return _success(data)


__all__ = [
    "DEFAULT_PRESENTATIONS_DIR",
    "DEFAULT_SOURCE_FILES",
    "ExtractPresentationSlidesSchema",
    "extract_presentation_slides",
]

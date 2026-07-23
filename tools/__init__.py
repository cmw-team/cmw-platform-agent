# ruff: noqa: N999, E402, RUF022
"""
Tools Package
=============

This package contains tool-related modules for the CMW Platform agent.

After the 2026-07 cleanup, the active native tool surface is intentionally
minimal:

* ``tools.templates_tools.tool_get_record_values`` — generic field read on a record.
* ``tools.get_datetime.get_current_datetime`` — current date/time helper.

MCP tools (``agent_ng.mcp_tools`` + ``config/mcp_servers.yaml``) are loaded
separately when ``CMW_MCP_ENABLED=true`` and provide the Comindware knowledge
base tools (``ask_comindware``, ``get_knowledge_base_articles``).

Auxiliary modules kept at the root of ``tools/`` for external/standalone use
(not bound to the agent): ``asset_extractor``, ``file_reference_tool_text``,
``file_utils``, ``local_path_text``, ``models``, ``pdf_utils``,
``platform_record_document`` was removed (its helper code was inlined into
``templates_tools/tool_get_record_values.py``); ``requests_``, ``requests_models``,
``tool_utils``, ``tools``.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from agent_ng.logging_config import setup_logging  # type: ignore[import-not-found]

    setup_logging()
except Exception as exc:
    # Tools can be used standalone; ignore if agent_ng not available.
    logger.debug("Skipping tools logging setup: %s", exc)

# Surviving tool subpackages and modules
from . import (
    models,
    requests_,
    templates_tools,
    tool_utils,
    tools,
)

# Convenience re-exports for the surviving tool surface
from .get_datetime import get_current_datetime
from .templates_tools import get_record_values

__all__ = [
    "get_current_datetime",
    "get_record_values",
    "models",
    "requests_",
    "templates_tools",
    "tools",
    "tool_utils",
]

"""Tiny stdlib-only frontmatter parser for ``SKILL.md``.

Supports the small subset we need: ``key: value`` pairs and YAML-style
``- item`` lists. Anything we cannot parse falls back gracefully — the
caller gets an empty ``meta`` dict and the original body.
"""

from __future__ import annotations

from typing import Any


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_list_value(lines: list[str], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    idx = start
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        if stripped.startswith("- "):
            items.append(_strip_quotes(stripped[2:]))
            idx += 1
            continue
        break
    return items, idx


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md body into ``(meta, body)``.

    The body is everything after the closing ``---`` fence (or the original
    text if the frontmatter is missing or malformed).
    """
    if not text:
        return {}, text

    lines = text.splitlines(keepends=False)
    if not lines or lines[0].strip() != "---":
        return {}, text

    meta_lines: list[str] = []
    closing_idx: int | None = None
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == "---":
            closing_idx = idx
            break
        meta_lines.append(line)

    if closing_idx is None:
        return {}, text

    meta: dict[str, Any] = {}
    idx = 0
    while idx < len(meta_lines):
        raw = meta_lines[idx]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        if ":" not in stripped:
            idx += 1
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            idx += 1
            continue
        if value == "":
            items, consumed = _parse_list_value(meta_lines, idx + 1)
            if items:
                meta[key] = items
                idx = consumed
                continue
            meta[key] = ""
            idx += 1
            continue
        meta[key] = _strip_quotes(value)
        idx += 1

    body = "\n".join(lines[closing_idx + 1 :])
    if text.endswith("\n") and not body.endswith("\n"):
        body += "\n"
    return meta, body

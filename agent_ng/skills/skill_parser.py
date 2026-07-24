"""Parse ``/<skill-name> <message>`` slash commands out of user input.

Rules (URL- and path-safe):
- A command is detected only at the very start of the trimmed input.
- After ``/`` the next character must be ASCII alpha (``[a-zA-Z]``).
- The name may contain ``[a-zA-Z0-9._-]`` and stops at the first whitespace.
- Anything else (e.g. ``/api/v1/foo``, ``/etc/hosts``, ``/2024/x``) is **not** a
  command — it is the regular user message.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommand:
    """A parsed ``/<name> <suffix>`` command."""

    name: str
    suffix: str
    full: str


_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_FIRST_CHAR_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def parse_slash_command(text: str) -> SlashCommand | None:
    """Return a ``SlashCommand`` if ``text`` starts with ``/<name>``, else ``None``."""
    if not text:
        return None
    stripped = text.lstrip()
    if not stripped.startswith("/"):
        return None
    if len(stripped) < 2 or stripped[1] not in _FIRST_CHAR_OK:
        return None

    idx = 1
    while idx < len(stripped) and stripped[idx] in _NAME_CHARS:
        idx += 1
    name = stripped[1:idx]
    if not name:
        return None

    # The name must be followed by whitespace or end-of-string; otherwise this
    # is a path or URL (e.g. ``/usr/bin/python``), not a skill command.
    if idx < len(stripped) and not stripped[idx].isspace():
        return None

    if idx < len(stripped):
        suffix = stripped[idx:].lstrip()
    else:
        suffix = ""

    return SlashCommand(name=name, suffix=suffix, full=text)

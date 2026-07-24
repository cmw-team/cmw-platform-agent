"""Build and filter the choices for the slash-command popup Dropdown.

Pure logic — no Gradio imports. The chat tab feeds these into
``gr.Dropdown(choices=..., visible=...)``.
"""

from __future__ import annotations

from pathlib import Path

from .skill_registry import discover_skills

_DESCRIPTION_MAX = 60


def _format_label(name: str, description: str) -> str:
    """Return ``"<name> — <description>"`` with a truncated description."""
    desc = (description or "").strip()
    if not desc:
        return name
    if len(desc) > _DESCRIPTION_MAX:
        keep = _DESCRIPTION_MAX - 3
        desc = desc[:keep].rstrip() + "..."
    return f"{name} — {desc}"


def build_popup_choices(skills_dir: Path) -> list[tuple[str, str]]:
    """Return ``[(label, value)]`` for every skill under ``skills_dir``.

    ``label`` is what the user sees in the dropdown; ``value`` is the
    bare skill name (what gets inserted into the textbox on click).
    """
    if not skills_dir.exists():
        return []
    return [
        (_format_label(entry.name, entry.description), entry.name)
        for entry in discover_skills(skills_dir)
    ]


def filter_popup_choices(
    choices: list[tuple[str, str]], query: str
) -> list[tuple[str, str]]:
    """Return ``choices`` filtered by ``query`` (case-insensitive substring).

    A leading ``/`` is stripped so ``/cmw`` filters down to skills whose
    name or description contains ``cmw``. Whitespace-only queries return
    every choice.
    """
    q = (query or "").strip().lstrip("/").strip().lower()
    if not q:
        return list(choices)
    return [(label, value) for label, value in choices if q in label.lower()]


_NAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)
_FIRST_CHAR_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def should_show_popup(text: str) -> bool:
    """Return ``True`` when the popup should be visible.

    Mirrors the slash-command parser rule: the popup only appears when the
    trimmed text starts with ``/`` and the next character is ASCII alpha
    (or end-of-string). URLs (``/api/v1/...``) and POSIX paths (``/etc/hosts``)
    are excluded because the resulting "name" is followed by a non-whitespace
    character — same rule as the slash parser.
    """
    if not text:
        return False
    stripped = text.lstrip()
    if not stripped.startswith("/"):
        return False
    if len(stripped) == 1:
        # Just "/" — show the popup with all skills.
        return True
    if stripped[1] not in _FIRST_CHAR_OK:
        return False
    idx = 1
    while idx < len(stripped) and stripped[idx] in _NAME_CHARS:
        idx += 1
    if not stripped[1:idx]:
        return False
    if idx < len(stripped) and not stripped[idx].isspace():
        return False
    return True

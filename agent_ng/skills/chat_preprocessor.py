"""Preprocess chat input to handle ``/<skill>`` commands before the LLM call.

Three outcomes:

- **passthrough** — text is forwarded to the LLM as-is.
- **activated** — a known skill was loaded; the LLM gets the suffix (without
  the ``/<name>`` prefix) plus the session-attached skill body.
- **error** — an unknown ``/<name>`` was typed; the caller should render the
  error message as the assistant reply and not call the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .skill_loader import MAX_BODY_CHARS_DEFAULT, load_skill_body
from .skill_parser import parse_slash_command
from .skill_registry import discover_skills


@dataclass(frozen=True)
class ChatPreprocessResult:
    """The preprocessor's verdict on a single user input."""

    passthrough: bool
    user_text: str
    skill_activated: str | None
    error: str | None


def preprocess_chat_input(
    text: str,
    skills_dir: Path,
    *,
    enabled: bool = True,
    max_chars: int = MAX_BODY_CHARS_DEFAULT,
) -> ChatPreprocessResult:
    """Return a verdict describing how ``text`` should be handled."""
    if not enabled or not text:
        return ChatPreprocessResult(
            passthrough=True, user_text=text, skill_activated=None, error=None
        )

    cmd = parse_slash_command(text)
    if cmd is None:
        return ChatPreprocessResult(
            passthrough=True, user_text=text, skill_activated=None, error=None
        )

    if not skills_dir.exists():
        return ChatPreprocessResult(
            passthrough=True, user_text=text, skill_activated=None, error=None
        )

    skills = discover_skills(skills_dir)
    skill_names = {s.name for s in skills}
    if cmd.name not in skill_names:
        available = ", ".join(sorted(skill_names)) if skill_names else "_(none)_"
        return ChatPreprocessResult(
            passthrough=False,
            user_text="",
            skill_activated=None,
            error=f"Unknown skill: {cmd.name!r}. Available: {available}.",
        )

    # Load the body. This validates the skill still exists on disk and
    # populates the loader's truncation notice for oversized skills. The
    # actual body is later injected via the session block, not as a separate
    # message in the chat history.
    try:
        load_skill_body(skills_dir, cmd.name, max_chars=max_chars)
    except LookupError as exc:
        return ChatPreprocessResult(
            passthrough=False,
            user_text="",
            skill_activated=None,
            error=f"Error loading skill {cmd.name!r}: {exc}",
        )

    return ChatPreprocessResult(
        passthrough=False,
        user_text=cmd.suffix,
        skill_activated=cmd.name,
        error=None,
    )

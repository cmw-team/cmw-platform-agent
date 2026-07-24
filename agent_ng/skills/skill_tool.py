"""LangChain ``StructuredTool`` factory for skill activation.

Three tools are produced:
- ``load_skill(name)`` — load a skill's body into the active session.
- ``load_skill_reference(skill_name, reference_path)`` — fetch a single
  ``references/<path>`` file.
- ``deactivate_skill(name)`` — remove a skill from the active session.

The active-skill set is kept in process-local memory; it is reset between
tests and on application restart. Per-session state is layered on top by the
agent's memory manager in a later phase.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool

from .skill_loader import (
    MAX_BODY_CHARS_DEFAULT,
    ReferenceNotFoundError,
    load_reference,
    load_skill_body,
)
from .skill_registry import find_skill

if TYPE_CHECKING:
    from .skill_session import SkillSession

logger = logging.getLogger(__name__)

# Process-local state. Tests clear it via the fixture in
# ``agent_ng/_tests/test_skill_tool.py``.
_active_skills: dict[str, str] = {}


def get_active_skills() -> set[str]:
    """Return a snapshot of currently active skill names (tests + debug)."""
    return set(_active_skills.keys())


def clear_active_skills() -> None:
    """Drop the process-local active-skill map (used by tests)."""
    _active_skills.clear()


def _format_active_block(name: str, body: str) -> str:
    return f"# Active skill: {name}\n\n{body}"


def _load_skill_handler(
    skills_root: Path,
    max_chars: int,
    name: str,
    on_activate: Callable[[str, str], None] | None = None,
) -> str:
    name = (name or "").strip()
    if not name:
        return "Error: 'name' must be a non-empty string."
    try:
        loaded = load_skill_body(skills_root, name, max_chars=max_chars)
    except LookupError:
        from .skill_registry import discover_skills

        available = [s.name for s in discover_skills(skills_root)]
        return f"Unknown skill: {name!r}. Available skills: {available}"

    _active_skills[loaded.name] = loaded.body
    if on_activate is not None:
        try:
            on_activate(loaded.name, loaded.body)
        except Exception:
            logger.exception("Skill on_activate callback failed")
    return _format_active_block(loaded.name, loaded.body)


def _load_reference_handler(
    skills_root: Path, skill_name: str, reference_path: str
) -> str:
    skill_name = (skill_name or "").strip()
    reference_path = (reference_path or "").strip()
    if not skill_name or not reference_path:
        return "Error: both 'skill_name' and 'reference_path' must be non-empty."
    try:
        return load_reference(skills_root, skill_name, reference_path)
    except ReferenceNotFoundError as exc:
        return f"Error: {exc}"
    except LookupError as exc:
        return f"Error: {exc}"


def _deactivate_handler(
    name: str,
    on_deactivate: Callable[[str], None] | None = None,
) -> str:
    name = (name or "").strip()
    if not name:
        return "Error: 'name' must be a non-empty string."
    if name in _active_skills:
        _active_skills.pop(name, None)
        if on_deactivate is not None:
            try:
                on_deactivate(name)
            except Exception:
                logger.exception("Skill on_deactivate callback failed")
        return f"Deactivated skill: {name}"
    return f"Skill {name!r} is not active."


def build_skill_tools(
    skills_root: Path,
    *,
    max_chars: int = MAX_BODY_CHARS_DEFAULT,
    session: SkillSession | None = None,
) -> list[StructuredTool]:
    """Return the three skill tools rooted at ``skills_root``.

    When ``session`` is provided, the tools also mirror their state into the
    given ``SkillSession`` so the agent can re-attach active skill bodies as
    system messages on every turn.
    """

    def _on_activate(name: str, body: str) -> None:
        if session is not None:
            session.activate(name, body)

    def _on_deactivate(name: str) -> None:
        if session is not None:
            session.deactivate(name)

    def load_skill(name: str) -> str:
        """Load a skill's instructions into context. Marks it active for the session.

        Returns the skill body (capped at ``max_chars`` characters). If the
        body is larger than the cap, returns a notice listing the available
        references — call ``load_skill_reference`` to fetch them one at a time.
        """
        return _load_skill_handler(skills_root, max_chars, name, _on_activate)

    def load_skill_reference(skill_name: str, reference_path: str) -> str:
        """Load a single ``references/<path>`` file from a skill.

        Use this when a skill is too large to load as a whole, or when you
        need a specific reference document.
        """
        return _load_reference_handler(skills_root, skill_name, reference_path)

    def deactivate_skill(name: str) -> str:
        """Remove a skill from the active session. Frees its tokens from context."""
        return _deactivate_handler(name, _on_deactivate)

    return [
        StructuredTool.from_function(
            func=load_skill,
            name="load_skill",
            description=(
                "Load a skill's instructions into context. Use when the user "
                "asks a task that matches a known skill's description. "
                "Returns the skill body and marks it active for the session."
            ),
        ),
        StructuredTool.from_function(
            func=load_skill_reference,
            name="load_skill_reference",
            description=(
                "Load a single file from a skill's references directory. Use "
                "when a skill was too large to load in full, or when you need "
                "a specific reference document."
            ),
        ),
        StructuredTool.from_function(
            func=deactivate_skill,
            name="deactivate_skill",
            description=(
                "Remove a previously loaded skill from the active session. "
                "Frees its tokens from context."
            ),
        ),
    ]

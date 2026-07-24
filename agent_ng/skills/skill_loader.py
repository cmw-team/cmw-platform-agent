"""Read a skill's body and references from disk, with a soft size cap."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .skill_registry import find_skill

MAX_BODY_CHARS_DEFAULT = 60_000


class ReferenceNotFoundError(LookupError):
    """Raised when a skill's reference path does not exist."""


@dataclass(frozen=True)
class LoadedSkill:
    """Result of loading a skill body, possibly truncated."""

    name: str
    body: str
    truncated: bool
    total_chars: int
    references: tuple[str, ...]
    skill_path: Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_skill_body(
    skills_root: Path,
    name: str,
    *,
    max_chars: int = MAX_BODY_CHARS_DEFAULT,
) -> LoadedSkill:
    """Return the SKILL.md body for ``name``, capped at ``max_chars`` characters.

    A truncated body is replaced with a notice that lists the available
    references — the LLM can then call ``load_skill_reference`` to fetch them
    one at a time.
    """
    entry = find_skill(skills_root, name)
    if entry is None:
        raise LookupError(f"Unknown skill: {name!r}")

    raw = _read_text(entry.path)
    total = len(raw)
    truncated = total > max_chars
    body = raw if not truncated else _truncation_notice(name, entry, max_chars, total)

    return LoadedSkill(
        name=entry.name,
        body=body,
        truncated=truncated,
        total_chars=total,
        references=entry.references,
        skill_path=entry.path,
    )


def _truncation_notice(
    name: str,
    entry,
    max_chars: int,
    total: int,
) -> str:
    ref_list = (
        "\n".join(f"- {ref}" for ref in entry.references) or "_(no references)_"
    )
    return (
        f"# Skill: {name}\n\n"
        f"⚠️ This skill is large ({total:,} chars); only the first "
        f"{max_chars:,} chars are loaded. To see specific sections, call "
        f'`load_skill_reference(skill_name={name!r}, reference_path="...")` '
        f"with one of these paths (relative to the skill's `references/`):\n\n"
        f"{ref_list}\n"
    )


def load_reference(skills_root: Path, name: str, reference_path: str) -> str:
    """Return the text of a single ``references/<reference_path>`` file."""
    entry = find_skill(skills_root, name)
    if entry is None:
        raise LookupError(f"Unknown skill: {name!r}")

    _safe_name = Path(reference_path).name  # reject absolute paths
    refs_dir = entry.folder / "references"
    target = (refs_dir / reference_path).resolve()
    refs_resolved = refs_dir.resolve()
    try:
        target.relative_to(refs_resolved)
    except ValueError as exc:
        msg = (
            "Reference path escapes the skill's references directory: "
            f"{reference_path!r}"
        )
        raise ReferenceNotFoundError(msg) from exc

    if not target.is_file():
        raise ReferenceNotFoundError(
            f"Reference not found: {name}/references/{reference_path}"
        )
    return _read_text(target)

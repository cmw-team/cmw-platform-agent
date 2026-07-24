"""Discover ``.agents/skills/<name>/SKILL.md`` on disk and expose summaries."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path

from .frontmatter import parse_frontmatter

logger = logging.getLogger(__name__)

_HIDDEN_PREFIXES = (".")


@dataclass(frozen=True)
class SkillEntry:
    """A single skill discovered on disk."""

    name: str
    description: str
    path: Path
    references: tuple[str, ...] = field(default_factory=tuple)

    @property
    def folder(self) -> Path:
        return self.path.parent


_CACHE: dict[tuple[str, int | None], tuple[list[SkillEntry], float]] = {}


def _walk_skills(root: Path) -> Iterable[SkillEntry]:
    if not root.is_dir():
        return
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if child.name.startswith(_HIDDEN_PREFIXES):
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        yield _build_entry(skill_md, fallback_name=child.name)


def _build_entry(skill_md: Path, fallback_name: str) -> SkillEntry:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read skill file %s: %s", skill_md, exc)
        return SkillEntry(
            name=fallback_name,
            description="",
            path=skill_md,
            references=(),
        )

    meta, _ = parse_frontmatter(text)
    name = str(meta.get("name") or "").strip() or fallback_name
    description = str(meta.get("description") or "").strip()
    references = _list_references(skill_md.parent)
    return SkillEntry(
        name=name,
        description=description,
        path=skill_md,
        references=references,
    )


def _list_references(skill_dir: Path) -> tuple[str, ...]:
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return ()
    out: list[str] = []
    for child in sorted(refs_dir.rglob("*")):
        if not child.is_file():
            continue
        if child.name.startswith(_HIDDEN_PREFIXES):
            continue
        rel = child.relative_to(refs_dir).as_posix()
        out.append(rel)
    return tuple(out)


def _mtime_of(root: Path) -> int | None:
    if not root.exists():
        return None
    latest: int | None = None
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            try:
                mtime = (Path(dirpath) / fname).stat().st_mtime_ns
            except OSError:
                continue
            if latest is None or mtime > latest:
                latest = mtime
    return latest


def clear_cache(root: Path | None = None) -> None:
    """Drop cached registry results (mostly for tests)."""
    if root is None:
        _CACHE.clear()
        return
    _CACHE.pop((str(root.resolve()), _mtime_of(root)), None)
    _CACHE.pop((str(root.resolve()), None), None)


def discover_skills(root: Path) -> list[SkillEntry]:
    """Return all skills under ``root``, deduped by ``name``.

    Results are cached by directory mtime for the lifetime of the process.
    """
    if not root.exists():
        return []

    key = (str(root.resolve()), _mtime_of(root))
    cached = _CACHE.get(key)
    if cached is not None:
        return list(cached[0])

    entries = list(_walk_skills(root))
    seen: set[str] = set()
    deduped: list[SkillEntry] = []
    for entry in entries:
        if entry.name in seen:
            logger.warning(
                "Duplicate skill name '%s' in %s; keeping the first one.",
                entry.name,
                root,
            )
            continue
        seen.add(entry.name)
        deduped.append(entry)

    _CACHE[key] = (deduped, 0.0)
    return list(deduped)


def find_skill(root: Path, name: str) -> SkillEntry | None:
    """Return a single skill by name, or ``None`` if not found."""
    if not name:
        return None
    for entry in discover_skills(root):
        if entry.name == name:
            return entry
    return None


def list_skill_summaries(root: Path) -> list[str]:
    """Return ``- name: description`` lines, one per skill, for the system prompt."""
    lines: list[str] = []
    for entry in discover_skills(root):
        if entry.description:
            lines.append(f"- {entry.name}: {entry.description}")
        else:
            lines.append(f"- {entry.name}:")
    return lines

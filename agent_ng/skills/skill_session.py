"""Per-session skill state: track active skills and re-attach their bodies.

Each session keeps a mapping of ``name -> body`` for skills activated during
the conversation. On every turn we re-attach the bodies as system messages so
the model continues to honor them without paying the cost of re-loading.

The state is plain in-memory dict. The agent's memory manager is responsible
for scoping this dict per session.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .skill_registry import SkillEntry


@dataclass
class SkillSession:
    """Active skills for one conversation session."""

    active: dict[str, str] = field(default_factory=dict)

    def activate(self, name: str, body: str) -> None:
        self.active[name] = body

    def deactivate(self, name: str) -> bool:
        return self.active.pop(name, None) is not None

    def is_active(self, name: str) -> bool:
        return name in self.active

    def active_names(self) -> tuple[str, ...]:
        return tuple(self.active.keys())

    def as_system_messages(self) -> list[tuple[str, str]]:
        """Return ``(role, content)`` pairs ready for the LLM call."""
        return [
            ("system", f"# Active skill: {name}\n\n{body}")
            for name, body in self.active.items()
        ]

    def active_entries(self, registry: Iterable[SkillEntry]) -> list[SkillEntry]:
        """Resolve active names against the registry (in registry order)."""
        names = set(self.active)
        return [entry for entry in registry if entry.name in names]

    def clear(self) -> None:
        self.active.clear()

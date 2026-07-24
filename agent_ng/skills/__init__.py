# ruff: noqa: N999  # Module name 'cmw-platform-agent' is the package convention.
"""Skill runtime for the LangChain + Gradio agent.

Discovers and serves ``.agents/skills/<name>/SKILL.md`` files at runtime so the
agent can be made aware of skills (via the system prompt) and activate them on
demand either through a ``/<name>`` slash command or by calling the
``load_skill(name)`` tool.

Pure-Python, framework-agnostic. No PyYAML dependency.
"""

from .frontmatter import parse_frontmatter
from .skill_loader import (
    MAX_BODY_CHARS_DEFAULT,
    LoadedSkill,
    ReferenceNotFoundError,
    load_reference,
    load_skill_body,
)
from .skill_registry import (
    SkillEntry,
    clear_cache,
    discover_skills,
    find_skill,
    list_skill_summaries,
)
from .skill_session import SkillSession

__all__ = [
    "MAX_BODY_CHARS_DEFAULT",
    "LoadedSkill",
    "ReferenceNotFoundError",
    "SkillEntry",
    "SkillSession",
    "clear_cache",
    "discover_skills",
    "find_skill",
    "list_skill_summaries",
    "load_reference",
    "load_skill_body",
    "parse_frontmatter",
]

# Optional modules — these are re-exported when present so callers can do a
# single ``from agent_ng.skills import parse_slash_command`` regardless of the
# order in which the runtime is being built up.
try:
    from .skill_parser import SlashCommand, parse_slash_command

    __all__ += ["SlashCommand", "parse_slash_command"]
except ImportError:
    pass

try:
    from .chat_preprocessor import ChatPreprocessResult, preprocess_chat_input

    __all__ += ["ChatPreprocessResult", "preprocess_chat_input"]
except ImportError:
    pass

try:
    from .skill_tool import build_skill_tools, get_active_skills

    __all__ += ["build_skill_tools", "get_active_skills"]
except ImportError:
    pass

"""Prompts for history compression and other LLM operations."""

import json
import os
from pathlib import Path
from typing import Any


def _load_system_prompt_json() -> dict[str, Any] | None:
    """Load system prompt JSON file"""
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.json")
        if not os.path.exists(prompt_path):
            return None
        with open(prompt_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_critical_system_prompt_context() -> str:
    """
    Extract critical context from system_prompt.json for compression.

    Returns:
        Formatted string with critical system prompt context
    """
    system_prompt_data = _load_system_prompt_json()
    if not system_prompt_data:
        return ""

    context_parts = []

    # Extract critical terminology
    if "cmw_platform_terminology" in system_prompt_data:
        terms = system_prompt_data["cmw_platform_terminology"]
        if "description" in terms and isinstance(terms["description"], list):
            context_parts.append("Terminology: " + "; ".join(terms["description"]))

    # Extract key synonyms
    if "cmw_synonyms" in system_prompt_data:
        synonyms = system_prompt_data["cmw_synonyms"]
        key_synonyms = []
        for key, value in synonyms.items():
            if isinstance(value, list):
                syn_str = f"{key}: {', '.join(value)}"
            else:
                syn_str = f"{key}: {value}"
            key_synonyms.append(syn_str)
        if key_synonyms:
            context_parts.append("Key synonyms: " + "; ".join(key_synonyms))

    return "\n".join(context_parts) if context_parts else ""


def get_history_compression_prompt(target_tokens: int, target_words: int) -> str:
    """
    Get the history compression prompt with system context injection.

    Args:
        target_tokens: Target token count for compressed summary
        target_words: Target word count estimate

    Returns:
        Formatted compression prompt with extracted system context
    """
    system_context = _extract_critical_system_prompt_context()

    # Format system context section
    system_context_section = (
        f"Context:\n{system_context}\n" if system_context else ""
    )

    # Build the prompt template
    prompt_template = """
You are the Sales & Marketing Copilot conversation summarizer.
Compress the dialog between the Copilot and the revenue-team user.

Preserve:
- active deals, leads, campaigns, segments discussed;
- pipeline numbers, conversion rates, forecasts mentioned;
- open tasks, owners, SLAs, deadlines;
- CMW Platform entities touched (applications, templates, attributes, scenarios, buttons);
- decisions, blockers, and pending confirmations;
- CRM/marketing-specific terminology.

Target: ~{target_tokens} tokens (~{target_words} words).

Guidelines:
- Preserve technical accuracy and CMW terminology.
- Preserve numbers and thresholds used in sales/marketing reasoning.
- Keep recent context denser than older context.
- Use LLM-oriented format without human-oriented formatting bloat.
"""

    return prompt_template.format(
        system_context=system_context_section,
        target_tokens=target_tokens,
        target_words=target_words,
    )


def build_skill_prompt_section(skills_dir: Path | str | None) -> str:
    """Build a ``## Available skills`` block for the system prompt.

    Returns an empty string when there are no skills, so callers can append
    unconditionally. The block is intentionally short — only ``name`` and
    one-line ``description`` per skill, plus a brief usage hint. Skill bodies
    are loaded on demand by the ``load_skill`` tool.
    """
    if skills_dir is None:
        return ""
    root = Path(skills_dir)
    if not root.exists():
        return ""

    # Import lazily so prompts.py stays importable in narrow test contexts.
    from .skills.skill_registry import list_skill_summaries

    lines = list_skill_summaries(root)
    if not lines:
        return ""

    body = "\n".join(lines)
    return (
        "## Available skills\n\n"
        "The following skills are installed. To use one, either type "
        "`/<skill-name> <message>` in chat, or call the `load_skill` tool "
        "when you judge the skill is needed. The skill body will be loaded "
        "into context for the rest of the session. Use `deactivate_skill` to "
        "remove a skill and free its tokens.\n\n"
        f"{body}\n"
    )


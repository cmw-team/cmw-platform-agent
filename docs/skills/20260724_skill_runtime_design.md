---
title: Skill Runtime Design
date: 2026-07-24
status: Implemented
---

# Skill Runtime — Design

## Goal

Connect the static `.agents/skills/<name>/SKILL.md` tree to the live LangChain + Gradio + FastAPI agent so that:

1. The agent **knows skills exist** (sees names + one-line descriptions in the system prompt).
2. Skills are activated **on demand** in two equivalent ways:
   - The user types `/<skill-name> <message>` in chat.
   - The LLM itself calls a `load_skill(name)` tool when it judges the skill is relevant.
3. Drop-in new skills under `.agents/skills/<name>/SKILL.md` work without code changes.
4. The programmatic `POST /api/v1/chat/completions` API is the only public surface; no new endpoints.

## Out of scope

- A /command picker dropdown UI.
- OpenCode-side registration (this is for the local agent only).
- Editing skills from the UI.

## Source-of-truth layout

```
.agents/skills/
    <skill-name>/
        SKILL.md            <- required: YAML frontmatter + Markdown body
        references/...      # optional
        scripts/...         # optional
```

SKILL.md frontmatter contract (small, stdlib-parsable subset, no PyYAML dependency):

```yaml
---
name: cmw-platform             # required; defaults to folder name
description: Use when ...      # required; one-line trigger description
---
```

The body is plain Markdown and is loaded verbatim.

## Runtime layer

New module `agent_ng/skills/` — pure, framework-agnostic, fully unit-tested:

| File | Purpose |
|---|---|
| `frontmatter.py` | Tiny stdlib-only frontmatter parser (key/value + list items). |
| `skill_registry.py` | `discover_skills(root)` → `list[SkillEntry]`, mtime-cached. |
| `skill_parser.py` | `parse_slash_command(text)` → `(name, suffix) | None`. |
| `skill_loader.py` | `load_skill_body(name)` → capped body; `load_reference(name, ref_path)` → file contents. |
| `skill_tool.py` | Builds the three LangChain `StructuredTool`s: `load_skill`, `load_skill_reference`, `deactivate_skill`. |
| `skill_session.py` | Per-session state: `active_skills: dict[str, str]` (name → body). |

## Behavior

### Awareness

The system prompt appends a `## Available skills` section (one line per skill: `- <name>: <description>`) when the registry has any skills. The LLM is told:

> To use a skill, either type `/<name>` in chat, or call the `load_skill` tool. The skill body is loaded into context for the rest of the session.

### Slash command

- `"/cmw-platform list apps"` → `(name="cmw-platform", suffix="list apps")`.
- Parsing rule: `/` at the start of trimmed text, then `[a-z0-9._-]+`, then whitespace.
- URLs like `/api/v1/foo` and POSIX paths starting with `/` are **not** commands.
- On match:
  - If the skill exists → the suffix is forwarded to the LLM as the user message, and the skill body is attached to the session before the LLM is called.
  - If the skill does not exist → an inline `"Unknown skill: 'foo'. Available: cmw-platform."` reply is rendered; no LLM call.
- The user bubble in chat is rendered as just the suffix (`"list apps"`) so the chat looks natural.

### LLM judgment (tool call)

The agent has three tools:

- `load_skill(name: str) -> str` — returns the body (capped) and marks the skill active for the session.
- `load_skill_reference(skill_name: str, reference_path: str) -> str` — returns the file content of a `references/<path>` file.
- `deactivate_skill(name: str) -> str` — removes the skill from the session block.

On every turn, the session block (a single `SystemMessage` per active skill) is prepended to the LLM call so the skill body stays in context for the rest of the session.

## Caps and limits

- `SKILL_MAX_BODY_CHARS` default `60000`. When the body exceeds the cap, `load_skill` returns a short notice with the list of `references/` files and a hint to use `load_skill_reference` to load them one at a time. The full body is never sent to the LLM as a single message.
- Unknown slash commands never reach the LLM (inline reply, deterministic).
- Unknown `load_skill(name)` returns a tool error string so the model can self-correct.

## Configuration

`agent_ng/agent_config.py`:

| Env var | Default | Purpose |
|---|---|---|
| `CMW_SKILLS_DIR` | `<repo>/.agents/skills` | Skills root directory. |
| `CMW_SKILLS_ENABLED` | `true` | Master switch. When `false`, registry returns empty, no tools are registered, no system-prompt block is added, slash commands reply "Skills disabled". |
| `CMW_SKILL_MAX_BODY_CHARS` | `60000` | Soft cap per skill body. |

`SKILLS_ENABLED=false` is a complete opt-out, kept simple for testability and for hosts that don't want skill tooling.

## Failure modes

- Missing `.agents/skills/` directory → registry returns `[]`, agent behaves as if no skills exist.
- Missing frontmatter → fallback: `name = folder name`, `description = ""`. The skill still loads.
- Malformed frontmatter (e.g. not closed `---\n`) → treat whole file as body, fall back to folder name.
- Skill references a path on disk that doesn't exist → `load_skill_reference` returns a tool error string; never raises.
- Two skills with the same `name` (across folders) → the first discovered wins; the duplicate is logged at warning level.

## TDD ordering

Each phase ends green before the next phase starts.

1. Registry + frontmatter (pure).
2. Slash-command parser (pure).
3. Loader + tools.
4. System-prompt skill section.
5. Chat tab wiring (slash preprocessor + UI prefix-strip).
6. LangChain agent integration (register tools, pass summaries).
7. End-to-end with stubbed LLM.
8. Config + env vars.
9. Verification gate.

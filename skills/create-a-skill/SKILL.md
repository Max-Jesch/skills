---
name: create-a-skill
description: >-
  Guide for creating a new Bob skill (SKILL.md) — covers the frontmatter
  schema, name rules, file location, and gotchas. Use when the user wants to
  author, create, or scaffold a skill.
---

# Create a Bob Skill

Guide the user through authoring a new Bob skill — a self-activating procedural guide stored as a
`SKILL.md` file. Follow these steps in order.

## Step 1 — Gather Requirements

Use the `ask_followup_question` tool to understand the skill before writing anything:
- **What should the skill do?** What task or workflow does it guide the model through?
- **When should it activate?** What user phrasing or situation should trigger it? (This becomes the
  description — the single most important field.)
- **Which mode(s)?** Should it be available everywhere, or restricted to specific modes (e.g. only
  `plan` mode)?
- **Scope:** Global (available in every workspace) or workspace (only this project)?
- **User-invocable?** Should the user be able to run it as `/<skill-name>`, or is it agent-only?

## Step 2 — Choose and Validate the Name

The skill name is derived from the **directory name** that contains `SKILL.md` — there is no
`name` field for `SKILL.md` files. It must match:

```
^[a-z0-9]+(-[a-z0-9]+)*$        (lowercase, digits, single dashes between words)   max 64 chars
```

⚠️ **Validation is silent.** An invalid name (uppercase, underscores, spaces, leading/trailing or
doubled dashes) causes the skill to be **skipped with no error**. Confirm the final name with the
user before writing.

## Step 3 — Draft the Frontmatter and Body

Skills use YAML frontmatter followed by a markdown body. All frontmatter fields are optional:

| Field | Default | Notes |
|---|---|---|
| `description` | first non-empty body line | **The trigger.** Drives auto-activation — write it with concrete trigger phrases, not vague intent. |
| `metadata.user-invocable` | `true` | Set `false` for agent-only skills. |
| `metadata.groups` | (all modes) | Array of mode slugs to restrict activation, e.g. `["plan"]`. |
| `metadata.argument-hint` | — | Autocomplete hint shown after `/skill-name`, e.g. `"[issue-number]"`. |
| `metadata.disable-model-invocation` | `false` | `true` hides it from the auto-activation list (user-invocable only). |

Example `SKILL.md`:

```markdown
---
description: Use when the user wants to review a PR for security issues — walks through auth, input validation, and secrets handling.
metadata:
  user-invocable: true
  argument-hint: "[pr-number]"
---

# Security Review

Follow these steps to review the pull request...
```

The body is the procedural content the model follows when the skill activates. Write it like the
`create-plan` skill: clear, step-numbered, and naming the actual Bob tools to use
(`ask_followup_question`, `write_file`, etc.).

## Step 4 — Write the File

Place `SKILL.md` in a directory named exactly after the skill. Use the `write_file` tool.

```
Global scope (precedence: .bob > .agents > .claude):
  ~/.bob/skills/<skill-name>/SKILL.md
  ~/.agents/skills/<skill-name>/SKILL.md
  ~/.claude/skills/<skill-name>/SKILL.md

Workspace scope (overrides global; same three roots supported):
  .bob/skills/<skill-name>/SKILL.md
  .agents/skills/<skill-name>/SKILL.md
  .claude/skills/<skill-name>/SKILL.md
```

Prefer `.bob/skills/<skill-name>/SKILL.md` unless the user asked otherwise.

## Step 5 — Confirm

Tell the user the skill **hot-reloads** — it is available immediately, no restart needed. If it does
not show up, the most likely cause is an invalid name (Step 2) being silently skipped; re-check the
name against the regex.

## Notes for power users

- **First-wins deduplication by name:** workspace > global > builtin. A workspace skill silently
  overrides a global one with the same name.
- **Grouped skills:** a skill may live one level deeper inside a "group" folder
  (`skills/<group>/<skill-name>/SKILL.md`). The name still comes from the immediate parent
  directory, not the group folder. Useful for organizing many related skills.
- **Supporting files:** other files placed alongside `SKILL.md` in the skill directory can be
  exposed to the model — mention this as a next step if the user needs richer skills.

## Reminders

- Always ask questions using the `ask_followup_question` tool.
- Confirm the final name and scope with the user before writing.
- Never include information without evidence.

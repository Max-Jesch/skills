---
description: >-
  Guide for creating a new custom Bob mode (custom_modes.yaml) — covers the
  schema, permission groups, roleDefinition, and file location. Use when the
  user wants to author, create, or scaffold a mode or persona.
---

# Create a Bob Mode

Guide the user through authoring a new custom mode — a persona with its own system prompt and tool
permissions, defined as an entry in `custom_modes.yaml`. Follow these steps in order.

## Step 1 — Gather Requirements

Use the `ask_followup_question` tool before writing anything:
- **Purpose & persona:** What is this mode for? What role/behavior should it embody? (This becomes
  `roleDefinition` — the primary differentiator. Push for a focused, specific persona, not a
  generic one.)
- **Tool access:** What should it be allowed to do — read files, edit files, run commands, use the
  browser, use MCP servers? (This maps to `groups`.)
- **Scope:** Global (available in every workspace) or workspace (only this project)?
- **Display details:** A human-readable `name` for the picker, and optionally `whenToUse`
  (tooltip) and a short `description`.

## Step 2 — Choose and Validate the Slug

The `slug` is the mode's unique identifier. It must match:

```
^[a-zA-Z0-9-]+$        (letters, digits, and dashes only — no underscores, no spaces)
```

⚠️ **Slug uniqueness is per-file.** A duplicate slug within the same `custom_modes.yaml` fails
schema validation and the **entire file is dropped** (no modes from it load) — an error is surfaced
in the UI. Before writing, read the target file (Step 4) and confirm the slug isn't already taken.

## Step 3 — Draft the YAML Entry

Each mode is one object under the top-level `customModes` array. Fields:

| Field | Required | Notes |
|---|---|---|
| `slug` | ✅ | Unique id, regex above. |
| `name` | ✅ | Display name shown in the mode picker. |
| `roleDefinition` | ✅ | Core system prompt / persona. Where most design effort goes. |
| `whenToUse` | No | Tooltip in the mode picker. |
| `description` | No | Short description. |
| `customInstructions` | No | Appended to the system prompt after `roleDefinition`. |
| `groups` | No | Tool permission groups (see below). Omit for default access. |
| `allowedSubagents` | No | **Trap:** if set, restricts sub-agent spawning to only the named presets. Omit unless you specifically need that restriction. |

⚠️ Do **not** set a `source` field — it exists in the schema but is managed internally.

### Tool permission groups

Common group values (the schema accepts any string — these are conventions, not an enforced enum):

| Group | Allows |
|---|---|
| `read` | File reading, symbol lookup |
| `edit` | File writing and modification |
| `execute` | Shell command execution |
| `browser` | Playwright browser tools |
| `mcp` | MCP server tools |

A group can carry a `fileRegex` restriction (tuple form):

```yaml
groups:
  - read
  - - edit
    - fileRegex: ".*\\.md$"   # this mode may only edit markdown files
```

⚠️ Two validations beyond the slug rule will drop the whole file if violated: **duplicate group
names** are rejected, and any `fileRegex` must **compile as a valid regular expression**.

Example entry:

```yaml
customModes:
  - slug: docs-writer
    name: Docs Writer
    roleDefinition: >-
      You are a technical writer who produces clear, concise documentation.
      You favor examples over prose and never edit source code.
    whenToUse: Use when writing or revising documentation.
    groups:
      - read
      - - edit
        - fileRegex: ".*\\.(md|mdx)$"
```

⚠️ **Use plain ASCII.** The loader strips problematic unicode (curly quotes " " ' ', em/en
dashes, non-breaking spaces) — copy-pasting YAML from a rich editor often introduces these. Type
straight quotes and hyphens.

## Step 4 — Write the File (read-then-append)

The file's top-level key is `customModes` (an array). Use `read_file` first; if the file exists,
**append** your new entry to the existing `customModes` array and write the whole thing back with
`write_file`. If it doesn't exist, create it with a single-entry `customModes` array.

```
Global:    ~/.bob/custom_modes.yaml      (available in all workspaces)
Workspace: .bob/custom_modes.yaml        (only when this workspace is open; overrides global on slug match)
```

Never overwrite an existing file blind — you would delete the user's other modes.

## Step 5 — Confirm

Tell the user the mode appears in the **mode picker immediately** (hot-reload, no restart). If it
doesn't appear, the file likely failed validation and was dropped — re-check the slug regex,
slug uniqueness, group names, and any `fileRegex`.

## Reminders

- Always ask questions using the `ask_followup_question` tool.
- Read the target file and confirm slug uniqueness before writing.
- Prefer workspace scope (`.bob/custom_modes.yaml`) unless the user wants the mode everywhere.
- Never include information without evidence.

# Skills

A collection of reusable [Agent Skills](https://www.skills.sh/) — portable `SKILL.md` files that teach coding agents how to do specific tasks. They work across Claude Code, Cursor, IBM Bob, and any other agent that supports the skills format.

## Install

Install all skills from this repo into your current project:

```bash
npx skills add <your-github-username>/skills
```

List what's available without installing:

```bash
npx skills add <your-github-username>/skills --list
```

Install a single skill:

```bash
npx skills add <your-github-username>/skills --skill example-skill
```

The `npx skills` CLI auto-detects which agents you have installed and copies the skill into the right place for each one (`.claude/skills/`, `.cursor/skills/`, `.agents/skills/`, etc.).

> Replace `<your-github-username>` above with your actual GitHub handle once the repo is pushed.

## Repository layout

```
skills/
└── <skill-name>/
    ├── SKILL.md        # required — the skill itself
    ├── reference.md    # optional supporting docs
    └── scripts/        # optional helper scripts
```

Skills live in a **neutral top-level `skills/` folder**, one directory per skill. They are intentionally *not* stored under any agent-specific folder (like `.claude/` or `.bob/`) — see [Multi-agent / IBM Bob](#multi-agent--ibm-bob-notes) below.

Each `SKILL.md` needs YAML frontmatter with two required fields:

```markdown
---
name: example-skill
description: What it does and — critically — WHEN to use it. This line is what the
  agent matches against, so be specific about the triggers.
---

# Example Skill

Instructions the agent follows when this skill activates...
```

## How this gets onto skills.sh

There are two separate things, and only one is automatic:

1. **Publicly installable** — happens the instant this repo is public on GitHub. Anyone can run `npx skills add <your-github-username>/skills`. No form, no approval.
2. **Listed on the skills.sh directory/leaderboard** — driven by **anonymous install telemetry**, ranked by real install counts. There is no submission step, but a repo with zero installs won't surface on its own. Visibility follows adoption.

To get picked up:

- Push the public repo with a clear install command (above).
- Drive real installs — dogfood by installing into your own projects via the CLI (each counts), and share the repo.
- Telemetry is on by default; if `SKILLS_NO_TELEMETRY=1` is set, your own installs won't count.

## Development workflow

The repo is the **source of truth**. Pull skills *into* projects rather than copy-pasting back and forth:

- **Active iteration** — symlink a project's skill folder to this repo so edits are the same file (no drift):
  ```bash
  ln -s ~/01_CODE/skills/skills/<skill-name> .bob/skills/<skill-name>
  ```
- **Stable use** — install via the CLI: `npx skills add <your-github-username>/skills --skill <skill-name>`. This is also exactly how others will consume it, so it dogfoods the real path.

## Multi-agent / IBM Bob notes

A `SKILL.md` is portable markdown — it doesn't belong to any one agent. The folder it lands in is a consumer-side detail:

- **Source of truth (this repo):** `skills/<name>/SKILL.md` — agent-agnostic. This is what the skills.sh CLI reads.
- **Consumption (a project):** the CLI copies the skill into each agent's folder — `.claude/skills/`, `.cursor/skills/`, `.agents/skills/`, etc.

The `npx skills` CLI knows ~55 agents but likely does **not** auto-target a custom `.bob/skills/` folder. So for IBM Bob, either:

- point Bob at the agent-neutral `.agents/skills/` location, or
- symlink/copy skills into `.bob/skills/` (see the workflow above).

Either way, keeping the canonical copies in `skills/` means `.bob` is never a problem for skills.sh discovery.

## License

[MIT](./LICENSE)

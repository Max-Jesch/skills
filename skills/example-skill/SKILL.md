---
name: example-skill
description: A template skill demonstrating the SKILL.md format. Replace this with a
  real skill. Copy this folder as the starting point for each new skill you create.
---

# Example Skill

This is a scaffold. Use it as the template for new skills, then delete it (or keep it
as a reference) once you have real skills.

## When to use this skill

Be specific here and in the `description` frontmatter above — the `description` is the
line the agent matches against to decide whether to activate the skill. State the
concrete triggers ("when the user asks to X", "when editing files of type Y").

## Instructions

1. Step-by-step guidance the agent should follow.
2. Keep it focused — one skill, one job.
3. Reference supporting files relatively, e.g. see [reference.md](./reference.md) or
   run `scripts/example.sh`.

## Examples

- Example input → expected behavior.

## Notes

- Optional supporting files (`reference.md`, `scripts/`) live alongside this file and
  are bundled when the skill is installed.

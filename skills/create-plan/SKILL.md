---
description: >-
  Structured workflow for gathering requirements, researching the codebase,
  writing a plan file. Use when the user wants to create a plan, design a
  solution, or break down a task before implementation.
metadata:
  user-invocable: false
  groups:
    - plan
---

# Create Plan

Follow this structured workflow to produce a high-quality, actionable plan.

## Step 1 — Gather Requirements

Ask the user clarifying questions to fully understand the task:
- What is the goal and expected outcome?
- Are there constraints, preferences, or non-goals?
- Which parts of the codebase are likely involved?
- Any related issues or requirement documents?

Do not proceed until you have enough context to scope the work, be critical of vague intent or requirements.

## Step 2 — Code Search via Sub-Agent

Spawn a `spawn_subagent` of type `"explore"` to research the codebase. The sub-agent should:
- Locate relevant files, symbols, and patterns related to the task
- Identify existing utilities or abstractions that should be reused
- Identify existing design patterns
- Surface any constraints or conventions (e.g. patterns in similar files)

Use the sub-agent's findings to ground your plan in the actual code.

## Step 3 — Clarify Design Intention

Based on the requirements and code research:
- Always confirm your understanding of the intended design with the user
- Raise any open questions or trade-offs that need a decision
- Adjust scope if the code research revealed complexity or simplifications

Do not begin writing the plan document until design intent is confirmed.

## Step 4 — Write the Plan File

Write a structured plan to a markdown file (e.g. `{short-plan-name}-plan.md`). The plan must NOT go into low-level code detail — focus on *what* needs to happen and *why*.

The plan file must include:

### Top-Level Overview
A concise summary of the goal, scope, and approach.

### Sub-Tasks
Break the work into sub-tasks. Each sub-task must have:
- **Intent** — what this sub-task achieves and why
- **Expected Outcomes** — observable results when this sub-task is complete
- **Todo List** — ordered, specific steps to achieve the outcome
- **Relevant Context** — pointers to relevant files, symbols, or patterns
- **Status** — `[ ] pending` (updated to `[x] done` after completion)

Design each sub-task to be processed independently, one at a time, so changes stay focused and reviewable.

## Step 5 — Plan Validation

Before moving to implementation, ensure that the user has fully read the plan. Always ask the user targeted questions to verify the plan is correct and complete:
- Does this plan capture the full scope of the task?
- Are the sub-task boundaries and ordering correct?
- Is any context missing that would be needed during implementation?

Use Mermaid diagrams in chat responses where they clarify architecture or workflow, but do not place Mermaid diagrams directly in the plan file. Avoid double quotes and parentheses inside square brackets in Mermaid syntax.

Refine the plan file based on the user's answers.

## Step 6 — Implementation

Only after the user confirms the plan, recommend implementation by calling the `switch_mode` tool to `agent`.

When explaining how to implement the plan in agent mode:
- Using the `start_subtask` tool, create a new task for each subtask in the <plan-file>.
- In the prompt for the subtask make sure it reads the plan-file to gain the full context around the task.
- After each sub task is complete update the task status in the <plan-file>
- Add any context needed for the next subtask in the <plan-file>
- Wait for the user to check and ok the changes before moving on to the next subtask.

## Reminders

- Ask questions always using the "ask_followup_question" tool
- Never include information without evidence
- Don't include time estimates

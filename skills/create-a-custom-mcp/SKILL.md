---
description: >-
  Guide for registering a new custom MCP server (mcp.json) — covers local vs
  remote transport, config fields, secrets handling, and scope. Use when the
  user wants to add, register, or configure an MCP server.
---

# Register a Custom MCP Server

Guide the user through adding an MCP (Model Context Protocol) server — an external tool provider —
by writing an entry into `mcp.json`. Follow these steps in order.

## Step 1 — Local or Remote?

This is the first decision, and it determines the config shape. Ask with `ask_followup_question`:
- **Local process:** Bob spawns the server as a child process. Needs `command` + `args`.
- **Remote server:** Bob connects to a running server over HTTP. Needs `url` (+ optional
  `headers`).

These are mutually exclusive — set `command`/`args` **or** `url`, not both. The transport is
inferred from which you provide; you do not need to set `transportType` yourself (it is an optional
passthrough field the harness does not interpret).

## Step 2 — Gather Connection Details

- **Local:** the executable (`"npx"`, `"uvx"`, `"node"`, or an absolute path) and its arguments
  (e.g. `["-y", "@my-org/my-mcp-server"]`).
- **Remote:** the full URL, plus any auth headers.
- **Environment:** any env vars the server needs (`env`). See the secrets warning in Step 4.

## Step 3 — Scope and Restrictions

- **Scope:** Global (`~/.bob/mcp.json`, all workspaces) or workspace (`.bob/mcp.json`, this
  project only)?
- **Mode restrictions (`groups`):** omit for universal availability, or restrict the server's tools
  to specific modes (e.g. `["plan"]`).
- **Auto-approval (`alwaysAllow`):** an optional list of tool names that skip the confirmation
  prompt. Use sparingly — prefer explicit approval for anything destructive or network-writing.

## Step 4 — Draft the Config Entry

Each server is one named object under the top-level `mcpServers` key. Fields:

| Field | Notes |
|---|---|
| `command` | Local executable, e.g. `"npx"`. (local only) |
| `args` | Array of arguments to the command. (local only) |
| `url` | Remote server URL — mutually exclusive with `command`. (remote only) |
| `headers` | HTTP headers for remote servers (e.g. auth tokens). |
| `env` | Env vars injected into a local server process. |
| `transportType` | Optional passthrough; normally leave unset (transport is inferred). |
| `disabled` | `true` to keep the entry but not connect. |
| `disabledTools` | Array of tool names to suppress from this server. |
| `alwaysAllow` | Array of tool names to auto-approve. |
| `timeout` | Connection timeout (ms). See note below. |
| `groups` | Restrict the server's tools to specific modes. |

⚠️ **Secrets in `env`/`headers` are written to disk verbatim.** Bob does **not** expand
`${VAR}`-style references in `mcp.json` — whatever you write is stored literally and in
plaintext. Prefer servers that read their own credentials from the OS environment, a keychain, or a
`.env` file, and put only non-secret config here. If a secret must be passed inline, make sure the
user understands it persists in the file.

⚠️ **Timeout values:** the settings UI snaps `timeout` to one of
`5000, 10000, 30000, 60000, 120000, 300000, 600000, 1800000, 3600000` (and defaults to `60000`
otherwise). Direct edits to `mcp.json` are **not** re-validated, so an off-list value is kept as-is
— but prefer the listed values for consistency.

Example file:

```json
{
  "mcpServers": {
    "my-server-name": {
      "command": "npx",
      "args": ["-y", "@my-org/my-mcp-server"],
      "env": { "MY_API_KEY": "..." }
    }
  }
}
```

## Step 5 — Write the File (read-then-merge)

The top-level key is `mcpServers` (an object keyed by server name). Use `read_file` first; if the
file exists, **add your server to the existing `mcpServers` object** and write the whole file back
with `write_file`. If it doesn't exist, create it with a single-server `mcpServers` object. Never
blind-overwrite — you would delete the user's other servers.

```
Global:    ~/.bob/mcp.json      (available in all workspaces)
Workspace: .bob/mcp.json        (overrides global for same-named servers)
```

Confirm with the user before writing, especially if `env` or `headers` contains a secret.

## Step 6 — Confirm

The server connects immediately on save (hot-reload). If it fails to connect, check: the
`command`/`url` is correct and reachable, required `env`/`headers` are present, and `disabled`
is not `true`.

## Notes for power users

- **Server name is the deduplication key:** a same-named server at workspace scope overrides global.
  Use this intentionally for per-project credential overrides.
- **Nested monorepos:** a deeper `.bob/mcp.json` overrides a shallower one within the same
  workspace (depth via `calculateConfigDepth()`).

## Reminders

- Always ask questions using the `ask_followup_question` tool.
- Read the target file and merge — never overwrite existing servers.
- Confirm before writing secrets to disk.
- Never include information without evidence.

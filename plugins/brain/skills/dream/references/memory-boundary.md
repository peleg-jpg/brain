# Memory boundary - what dream owns vs routes vs never touches

dream owns ONE thing: the target auto-memory directory (its `MEMORY.md` index plus the
topic `*.md` files beside it). Everything else is a guest to leave alone or PROPOSE a route
for. Cross-system moves are always flag-list suggestions the user executes; dream never
writes a foreign system itself.

This file is dream's OWN copy of the boundary so it does not depend on the live layout of
external rule files (which get reorganized).

## dream OWNS (may rewrite, with dry-run + snapshot)

- `<memory-dir>/MEMORY.md` - the always-loaded index
- `<memory-dir>/*.md` - topic files (durable, project-scoped preferences, rules,
  shortcuts, infra gotchas, identity facts, active project state)

## dream NEVER writes (hard denylist)

| System                                                    | Why off-limits                                                                                                                          |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| any `CLAUDE.md` (global or project)                       | identity/rules; dream only FLAGS drift, never edits directly.                                                                           |
| claude-mem (its DB / observation store)                   | frozen cross-session observations with their own session-hook ingest. No stable write API; writing directly risks corrupting its index. |
| the Obsidian vault(s) (`vault_path` in `~/.claude/brain-config.json`) | evolving knowledge with its own ingest (vault-ingest) + brain-doctor.                                                                                |
| `~/.claude/memory/diary` and `/reflections`               | owned by the /diary and /reflect skills; dream never writes there.                                      |

## Routing table (PROPOSE only, never auto-move)

When a memory clearly belongs in another system, propose a one-line pointer to replace it
locally and let the user move the content:

| Memory looks like...                                                                                   | Belongs in...                          | dream proposes                                                     |
| ------------------------------------------------------------------------------------------------------ | -------------------------------------- | ------------------------------------------------------------------ |
| a code convention / "always use X in code"                                                             | CLAUDE.md or a skill                   | flag: "this is a code rule, move to CLAUDE.md?"                    |
| a frozen dated event ("we shipped X on 2026-06-16")                                                    | claude-mem                             | flag: "frozen history, save to claude-mem then drop here?"         |
| evolving deep architecture / a decision that keeps changing                                            | Obsidian domain note                   | flag: "evolving design, Obsidian note + one-line pointer?"         |
| a voice/style rule duplicated in an installed skill (e.g. biz-carousels voice-rules, the `/pic` skill) | that skill's `references/`             | flag: "duplicates <skill>, replace with a one-line skill-pointer?" |
| raw session transcript content                                                                         | nowhere (it is the source, not memory) | flag for deletion with evidence                                    |

## What STAYS in auto-memory

Terse, durable, frequently-needed operational pointers: infra gotchas, process shortcuts,
user identity facts (email, chat ids, hardware), active project state, and one-line
links to the topic files that hold the detail. The index is a router, not a warehouse.

## The test for a single memory

Keep it in auto-memory if ALL hold: it is durable (not a one-off event), it is operational
or identity (not evolving prose), and a future session would want it surfaced cheaply at
start. Otherwise propose a route.

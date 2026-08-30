---
name: brain-router
version: 1.1.0
description: The routing decision tree for the knowledge layers - answers "where does this go" in one authoritative place. Use whenever the user says "remember this", "save this", "don't forget", "put this somewhere", when Claude is about to write to any memory layer (auto-memory, claude-mem, the Obsidian vault, CLAUDE.md) and the destination is not obvious, or when deciding whether knowledge is duplicated across layers. Prevents the fragmentation where the same fact lands in 3 stores. Not for YouTube/article ingestion (use vault-ingest) or full brain health scans (use brain-doctor) - answers only the single-fact routing question.
---

# Brain Router

One fact, one home. Without a rule, every "remember this" moment improvises
its own destination and the same learned rule ends up in 3 places with no
sync. This is the non-improvised answer.

## The routing table

Ask two questions: **does it evolve or is it frozen?** and **who consumes it?**

| The thing | Home | Why |
| --- | --- | --- |
| Correction / "do it this way" feedback on how Claude works | `feedback_<topic>.md` in the project's auto-memory (`~/.claude/projects/<slug>/memory/`) + one MEMORY.md index line | Auto-loaded every session; janitored by /dream. The ONE store for learned rules |
| Who the user is: identity, voice, global hard rules | `~/.claude/CLAUDE.md` (global) or the project CLAUDE.md | Loaded everywhere; keep lean, pointers over content |
| Evolving knowledge: video insights, research, patterns, architecture decisions, project state | the Obsidian vault (`vault_path` in `~/.claude/brain-config.json`), then `/graphify . --update` | Things that get revised belong in the vault with links + graph |
| Frozen record: session events, one-off observations, exact recall, timestamps | claude-mem (automatic via its hooks) and transcript-memory (automatic via the brain hooks) | Frozen material must NOT enter the vault |
| Full transcripts, raw articles, source dumps | `~/brain-archive/<vault>/<YYYY-MM>/` | Never inside a vault, never inside memory files |
| Project state only this machine needs (paths, runbooks, ids) | `project_*` / `reference_*` auto-memory file | Operational recall, not knowledge |
| Temporary research spike | scratchpad | Not a persistent layer; let it die |

## Tie-breakers

- **Evolves AND operational?** Vault gets the knowledge; auto-memory gets a
  one-line pointer to the vault note (not a copy).
- **Two vaults (engineering + research)?** Engineering/code/architecture goes
  to the engineering vault, external-source knowledge (videos, articles) to
  the research vault. Never both.
- **Unsure after this table?** Ask the user one line: "vault / memory / claude-mem?"

## The one hard rule

Before writing, grep the target layer for an existing home
(`Grep` the memory dir, `graphify query` the vault). Update beats create;
one home beats two copies. If you find the fact already living in another
layer, replace the copy with a pointer instead of adding a third.

---
name: dream
version: 1.0.0
description: >-
  Consolidates Claude Code auto-memory: strips stale content, fixes the index, and
  keeps MEMORY.md under its load budget. Use when the user says "/dream", "dream",
  "consolidate memory", "clean up my memory", "prune memory", "my MEMORY.md is over
  the line limit", or asks to merge duplicate memory files, resolve contradictory
  memories, convert relative dates to absolute, or re-index orphan memory files. Not
  for claude-mem observations, Obsidian vault notes, or session diary/reflect entries:
  dream never writes those systems.
---

# dream - auto-memory consolidation

## What this is

Claude Code accumulates an auto-memory folder per project: a `MEMORY.md` index plus
many topic `*.md` files, all loaded at session start. Over time the index bloats,
duplicates and contradictions pile up, relative dates rot, and stale junk creeps in.
`dream` is the janitor that fixes this safely.

This is the v1 "cut-to-3" build: a thin skill driving one deterministic Python helper.
It does the high-value, low-risk cleanup mechanically, and surfaces the judgement calls
as a flag list for the user to approve. It deliberately does NOT mine session
transcripts or auto-merge topic-file contradictions yet (deferred to a later version).

## Iron rules

1. **Dry-run first, always.** Bare `/dream` only reports and shows a diff. Writing
   requires the user to say "go" / "apply".
2. **Scope-lock.** dream touches ONLY the target auto-memory directory (its `MEMORY.md`
   plus topic `*.md` files). It NEVER writes claude-mem, either Obsidian vault, or any
   `CLAUDE.md`. (`~/.claude/memory/diary` and `/reflections` were retired 2026-07-03 -
   flag for archival if found, do not treat as live protected systems.) Cross-system
   cleanup is PROPOSE-only (a flag list the user acts on). See `references/memory-boundary.md`.
3. **Lossless.** Content is moved, never silently deleted. The only hard deletions are
   ghost links (pointing at files that no longer exist) and the stale `# Environment`
   trailer; both are reported line by line.
4. **Snapshot before write.** A tarball of the whole memory dir is written OUTSIDE it
   (`~/.dream-snapshots/`, override with `DREAM_SNAPSHOT_DIR`) as the first action on
   apply. The restore command is printed.

## Flags / scope

| Invocation    | Target directory                                                                                                                |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `/dream`      | the current project's auto-memory dir (resolve from the project path under `~/.claude/projects/<slug>/memory/`)                 |
| `/dream user` | the global memory dir `~/.claude/memory/` IF it contains a `MEMORY.md` (else report that there is no user-level index and stop) |
| `/dream all`  | iterate every `~/.claude/projects/*/memory/` that has a `MEMORY.md`, one at a time, each with its own dry-run/apply gate        |

`--apply` (or the user saying "go") flips dry-run to a real write. Default is dry-run.

## Procedure

Run these as TodoWrite items.

### 1. Resolve the target directory

From the flag. The current project's memory dir is `~/.claude/projects/<project-slug>/memory/`
where `<project-slug>` is the working directory path with `/` replaced by `-`. Confirm
`MEMORY.md` exists there. If not, tell the user and stop.

### 2. Audit (read-only)

```bash
python3 ~/.claude/skills/dream/scripts/dream.py audit "<memory-dir>"
```

Show the user the report: line/byte budget status, whether the stale `# Environment`
trailer is present (a known harness pollution bug), em-dash count, orphan files,
ghost links, split `(cont)` sections, over-long lines. This is the diagnosis.

### 3. Dry-run rebuild

```bash
python3 ~/.claude/skills/dream/scripts/dream.py rebuild "<memory-dir>"
```

This prints the planned actions, the before/after line+byte counts, any new topic files
it would create, and a unified diff of `MEMORY.md`. The Python helper deterministically:

- strips the stale `# Environment` system-preamble trailer (and would flag it if it ever
  regenerates: it should not, the writer is a one-time past-session artifact, not a hook)
- sweeps every em-dash / en-dash to a hyphen (no em/en dashes rule)
- merges any `X (cont)` section back into `X`
- re-indexes orphan files (on disk but missing from the index) under an `## Unsorted`
  section, using each file's frontmatter `description`
- drops ghost links whose target file no longer exists
- collapses decorative blank-line padding
- if still over budget (200 lines OR 25000 bytes), demotes the largest inline-prose
  sections into their own `inline_*.md` topic files (content preserved verbatim) and
  leaves a one-line pointer, until under budget

Present the diff to the user. If the rebuild reports "STILL OVER" budget, that means even
after demotion there are too many entries; tell the user a judgement-based consolidation
(merging similar topic files) is needed and offer to do that as a separate gated pass.

### 4. Flag-only reconciliation (the LLM judgement layer, PROPOSE only)

While the user reviews the diff, scan for things the deterministic pass cannot decide, and
present them as a numbered flag list. DO NOT act on these without per-item approval, and
NEVER write outside the memory dir:

- **Duplicates / contradictions across topic files.** Cluster files by subject. Same
  subject + same claim = candidate merge. Same subject + conflicting claim = contradiction;
  the newer/more-specific one usually wins, but ASK. Beware false dupes: files sharing a
  subject but encoding distinct rules (e.g. the many `feedback_hebrew_*` word-pair files)
  are NOT duplicates.
- **Relative dates** ("next Friday", "last week") in topic-file bodies. Propose absolute
  dates; you generally cannot know the anchor, so ask.
- **Wrong-system content.** A memory that is really a code convention, a frozen one-off
  event, or evolving architecture belongs elsewhere (CLAUDE.md / claude-mem / Obsidian).
  Propose a one-line skill-or-system pointer to replace it locally; let the user move the
  content. See `references/memory-boundary.md` for the routing table.

### 5. Apply (only on explicit "go")

```bash
python3 ~/.claude/skills/dream/scripts/dream.py rebuild "<memory-dir>" --apply
```

This snapshots, re-stats every file (aborts if anything changed since the snapshot, to
avoid clobbering a parallel session), writes new topic files first, then atomically
replaces `MEMORY.md`. Then apply any flag-list items the user approved.

### 6. Report

Show the summary card: snapshot path + restore command, before/after lines+bytes, what
changed (stripped / swept / merged / re-indexed / demoted), and the flag list with each
item's disposition (applied / deferred). If the env trailer was present, note that the
audit detector will catch it on future runs if it ever returns.

## Permissions warning

Editing files inside `.claude/` triggers a "allow Claude to edit its own settings?" prompt
even when bypass is on. Approve the per-file edits. Do NOT pick the session-wide
"allow all self-edits" escalation, and do not run dream under `bypassPermissions`: a memory
janitor with delete-and-rewrite scope over hand-won files should stay gated.

## Recovery

Every apply leaves a tarball in `~/.dream-snapshots/` (or `$DREAM_SNAPSHOT_DIR`). To undo:

```bash
tar xzf ~/.dream-snapshots/<dir>-<timestamp>.tgz -C <memory-dir>
```

## Tests

`scripts/test_dream.py` covers env-trailer strip, em-dash sweep, `(cont)` merge, orphan
re-index, ghost-link drop, lossless demotion, and the idempotence guarantee (a second
rebuild on a clean dir is byte-identical). Run `python3 scripts/test_dream.py` before
changing the helper.

## Additional resources

- `references/memory-boundary.md` - what belongs in auto-memory vs what dream proposes to
  route to CLAUDE.md / claude-mem / Obsidian, and the parallel-system denylist.

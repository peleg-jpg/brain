---
name: harvest
version: 1.1.0
description: Distill a FINISHED piece of work (shipped repo milestone, completed project, closed session, done client engagement) into an evergreen wiki note in the Obsidian vault, cross-linked and graphified. This is the ONLY sanctioned writer of evergreen/wiki notes from your own work - never write one directly outside this skill. Use whenever the user says "harvest", "harvest this", "distill this project", "turn this into a wiki note", "evergreen note from this", or finishes a milestone and wants the learning kept. NOT for raw capture (claude-mem does that), NOT for WIP project notes, NOT for videos/articles (vault-ingest does those).
---

# Harvest

Karpathy pipeline: capture -> project -> output -> **wiki**. Harvest is the last arrow. It takes work that SHIPPED and distills what was learned into an evergreen note. Nothing from your own projects enters the wiki layer any other way - that rule is what keeps the wiki trustworthy.

Why only from shipped work: an idea that never shipped is a guess. A pattern extracted from something that ran in production earned its place.

## Preconditions

1. Find the vault: `vault_path` in `~/.claude/brain-config.json` (or `$BRAIN_VAULT`). Read its `CLAUDE.md` and index (`_vault-index.md` or `wiki/index.md`).
2. Confirm the work is actually finished (shipped commit, deployed page, closed engagement). If it is WIP, stop - harvesting WIP produces wiki noise.

## The loop

### 1. Gather the learning

Pull from every store that touched the work - this is distillation, not invention:

- `git log` of the repo (what shipped, in what order)
- claude-mem: `mem-search` for the project name (decisions, bugs, learnings)
- project auto-memory (`~/.claude/projects/<slug>/memory/`)
- any project notes already in the vault
- transcript memory - the actual back-and-forth of the work:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcript_memory.py" search "<topic>"` then `session <session_id>` for full exchanges

### 2. Distill - the hard part

An evergreen note answers: **what would I want to know before doing this again?**

Keep: architecture decisions + rationale, patterns that transfer, gotchas that cost hours, numbers that surprised.
Drop: changelogs, timestamps, one-off bug fixes, anything already frozen in claude-mem. If a fact will never be revised, it does not belong here.

Target: one screen of markdown. If it wants to be longer, it is probably two notes or it is carrying changelog weight.

### 3. Place it

- Pick the domain folder from the vault index. Never the vault root. If you keep a separate engineering vault, engineering learnings go there.
- **Update over create** (Karpathy simplicity): if a note on this topic exists, fold the new learning in surgically instead of spawning a sibling.
- Filename must contain the project slug (kebab-case), e.g. `my-shop-checkout.md` for project "my shop checkout".

### 4. Cross-link

Search the vault for related notes (grep titles/index, `graphify query`) and wire `[[...]]` links both ways where the related note gains from it. A wiki without links is a folder.

### 5. Graphify

From the vault root: `/graphify . --update` (incremental, agent-driven, run in-session). Git hooks do NOT regraph markdown - this explicit run is mandatory, never skip it.

### 6. Log

One line appended to the vault's `_log.md`, matching the existing entry style:

```
- YYYY-MM-DD [harvest] <domain>/<note>.md distilled from <source project/milestone>; N cross-links; graphify updated.
```

### 7. Prove it

Report in the same reply: note path, link count, graphify output confirmation, the `_log.md` line. Harvest without proof is not done.

## Working from transcript-memory nominations

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcript_memory.py" harvest-candidates` lists sessions that look shipped and were never harvested. After deciding on each one, close the loop so it is not re-nominated:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcript_memory.py" harvest-mark harvested <session ids...>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcript_memory.py" harvest-mark skipped <session ids...>
```

## Hard rules

- Plain markdown, no Obsidian-plugin syntax.
- No em/en dashes in the note - only `-`.
- Never delete or rewrite unrelated lines in an existing note (surgical principle).
- Raw sources stay where they are - harvest reads them, never moves or deletes them.

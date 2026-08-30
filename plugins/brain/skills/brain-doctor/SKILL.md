---
name: brain-doctor
version: 1.1.0
description: Weekly health check and repair for the second brain - the Obsidian vault (broken wikilinks, stale graphify graph, raw/ backlog, index drift, cruft), Claude Code auto-memory (MEMORY.md budget) and claude-mem (DB counts). Use when the user says "brain doctor", "check my brain", "check my vault", "vault health", "fix my second brain", "brain checkup", asks why the vault, graph or index feels stale, after any large ingest batch, or as the weekly maintenance run. Scans deterministically, auto-applies only safe reversible fixes, proposes the rest for approval.
---

# Brain Doctor

One run = scan every knowledge layer, fix what is safe, propose what is not.
The goal is a compounding second brain: raw sources flow in, get distilled,
get linked, get graphed, and nothing rots silently.

## Why this exists

The usual failure mode is never "bad notes". It is maintenance loops that
detect problems without fixing them (a linter flagging the same broken links
for 3 months), staleness nobody notices (a graph 80 days behind the notes),
and staging areas turning into warehouses (dozens of un-summarized
transcripts in `raw/`). A doctor that only diagnoses is useless; each run
must leave the system measurably healthier.

## Step 1 - Scan (deterministic, read-only)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/brain-doctor/scripts/brain_scan.py" --pretty
```

Vault discovery: `$BRAIN_VAULT`, then `~/.claude/brain-config.json`
(`vault_path`, written by `/brain-init`), then `~/obsidian-brain`. Add more
vaults with `--vault PATH` (repeatable). Drop `--pretty` for JSON when you
need to file results or compare runs.

The scanner covers: note counts + 30-day activity, staging backlog (`raw/`,
`_raw/`, `transcripts/`), broken wikilinks, index drift (folders missing
from the vault index), graphify staleness, frontmatter coverage, embedded
transcript blocks, cruft, MEMORY.md budget for every project, claude-mem DB
counts.

`scripts/weekly_report.py` takes the JSON on stdin and prints a short
pass/fail scorecard (exit 1 = something needs an interactive run). Wire it
to cron, launchd or `/loop` if you want a weekly nudge:

```bash
python3 .../brain_scan.py | python3 .../weekly_report.py
```

Known false positives: wikilinks inside control files (`CLAUDE.md`,
`_rules.md`, index templates) are usually documentation examples like
`[[note-name]]`. Ignore those; only real notes count as broken links.

## Step 2 - Auto-fix the SAFE list (no approval needed)

Safe = reversible, no knowledge deleted. Apply all that the scan flags:

1. **Stale graph** (`graph_stale: true`): from the vault root run
   `/graphify . --update`. Do this LAST, after the link/index fixes below,
   so the rebuilt graph includes them.
2. **Broken wikilinks in real notes**: if a same-named note exists elsewhere,
   repair the path. If the target never existed, either create a stub note
   (when 2+ notes link to it - demand proves it deserves to exist) or unlink
   the text (single reference, clearly abandoned). Folder-links like
   `[[folder/]]` cannot resolve in Obsidian - convert to plain text or link
   a real note.
3. **Index drift**: add one-line entries (under 80 chars) to the vault index
   for any content folder the scan lists in `index_missing_folders`.
4. **Cruft**: delete 0-byte `Untitled.md`, `.DS_Store`, stale `.graphify_*`
   cache files older than the current graph.
5. **MEMORY.md over 200 lines**: invoke the `dream` skill (`/dream`) - it is
   the sanctioned janitor for auto-memory. Do not hand-trim MEMORY.md here.
6. **Log the run**: one line in each touched vault's `_log.md`:
   `- YYYY-MM-DD: [brain-doctor] fixed N links, indexed M folders, regraphed`.

## Step 3 - Propose the GATED list (wait for the user's "go")

These move or transform knowledge, so present them as a short numbered menu
with counts from the scan and wait. Procedures live in
[references/fix-playbook.md](references/fix-playbook.md) - read it before
executing any approved item.

- **Staging backlog** (`raw/`, `_raw/`): ingest-then-delete, archive, or
  drop, per file batch.
- **Transcript squatters**: `transcripts/` folders and notes flagged by
  `notes_with_embedded_transcripts` - archive full transcripts out of the
  vault, keep the distilled top of each note.
- **Monolithic pages** (5,000+ words): split into atomic concept notes.
- **Dormant domains**: folders with 0 edits in 30+ days that claim to be
  active projects - propose archiving or a refresh session.

Never delete source material outright: gated fixes MOVE files to
`~/brain-archive/<vault>/<YYYY-MM>/` so every step is reversible.

## Step 4 - Report

End with a compact scorecard (before -> after for each fixed metric, plus the
gated proposals awaiting decision). If a metric could not be fixed, say so
plainly - a silent skip is how maintenance loops die.

## Boundaries

- Read-only toward claude-mem (report counts, never write the DB).
- Never edit CLAUDE.md files or skills.
- Respect Karpathy rules: surgical edits only, every changed line traceable
  to a scan finding, update existing notes instead of creating new ones.

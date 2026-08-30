<!-- BRAIN-AUTOUSE-START -->
<!-- Paste this block into ~/.claude/CLAUDE.md (or let /brain-init merge it). -->
<!-- It tells Claude Code WHEN to reach for each brain skill on its own, so you never have to remember. -->

# Brain: auto-use rules (less repeating yourself, fewer tokens)

The vault lives at `vault_path` in `~/.claude/brain-config.json`. Skills: /yt-capture, /vault-ingest, /harvest, brain-router, /dream, /brain-doctor, transcript-memory, graphify, claude-mem. Full guide: SKILLS.md in the brain repo.

## Before reading anything

- Topic that could live in the vault -> from the vault root run `graphify query "<topic>"` FIRST. Read only the notes it returns. Never open the whole vault, never read 30 notes to find one.
- The user hints at past work ("did we", "last time", "how did we fix", "have we solved") -> the transcript-memory hook injects the top 3 matching exchanges automatically. If nothing arrived, run `transcript_memory.py search "<2-3 terms>"` before redoing solved work.
- Prior decisions, bugs, learnings -> claude-mem `mem-search` before starting, not after finishing.

## While working

- YouTube URL or article link -> /yt-capture, then the 4-option ingest menu. Never summarize a video into chat and lose it.
- "remember this", "don't forget", "save this", any correction of how you work -> brain-router picks the ONE home. Corrections become a `feedback_<topic>.md` in the project's auto-memory (`~/.claude/projects/<slug>/memory/`) + one MEMORY.md line, with **Why** and **How to apply**. Never the same fact in two layers: one home, one pointer.
- Shipped milestone, closed project, finished client work -> offer /harvest once. Only shipped work becomes a wiki note.
- After ANY vault write: `/graphify . --update` from the vault root, then one line in `_log.md`. A stale graph answers wrong.

## Maintenance (act when triggered, do not nag)

- MEMORY.md over 200 lines, duplicate or contradicting memories, relative dates ("last week") in memory -> run /dream. Dry-run, show the diff, apply only on "go".
- First session of the week, or after a batch ingest -> run /brain-doctor. Auto-apply the safe list, propose the gated list with counts, wait.
- `raw/` is a loading dock, not a warehouse. Files older than 7 days in raw/ get the ingest menu.

## Token discipline

- Search before read: grep, glob, `graphify query`, then read the slice (`offset`/`limit`), never the whole file.
- Filter, don't scan: logs, CSVs, big JSON get a targeted command, not an eyeball pass.
- Never paste transcripts or raw articles into notes, memory files or chat. Insights go to the wiki, the source goes to `~/brain-archive/` or gets deleted.
- Prefer one-line pointers over copies. The index is a router, not a warehouse.

<!-- BRAIN-AUTOUSE-END -->

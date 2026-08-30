---
name: transcript-memory
version: 1.1.0
description: Search a local index of ALL completed Claude Code transcripts (every project, any language, BM25 full-text, zero dependencies). Use when the user asks "what did we do about X", "have we solved this before", "find that session where...", "search my transcripts", "when did I work on X", or when past-session context would prevent redoing solved work. Distinct from claude-mem (curated observations) - this is raw exchange-level search over the transcripts themselves.
---

# Transcript Memory

Local SQLite FTS5 index over every completed Claude Code session. Stdlib only. The brain plugin's hooks ingest automatically (SessionEnd, PreCompact, SessionStart backfill) and inject the top 3 past exchanges when a prompt sounds like recall ("did we", "last time", "how did we fix"). DB: `~/.claude/transcript-memory/transcripts.db` (override with `$TRANSCRIPT_MEMORY_DB`).

## Commands

All via: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcript_memory.py" <cmd>`

| Command | Use |
| --- | --- |
| `search "query" [--project X] [--since YYYY-MM-DD] [--limit 8] [--any]` | BM25 search. Terms are ANDed; `--any` = OR. Non-Latin text works. |
| `show <chunk_id>` | Full exchange (user + assistant text, tools, branch). |
| `session <session_id_prefix>` | All exchanges of one session in order. |
| `stats` | Corpus size, per-project counts. |
| `backfill` | Re-scan all transcripts (incremental, mtime-skipped). |
| `ingest <path> [--force]` | One transcript. |
| `recall --prompt "..."` | What the UserPromptSubmit hook does; test it by hand. |
| `harvest-candidates` / `harvest-mark` | Nominate shipped-looking sessions for /harvest and close the loop. |

## Workflow

1. `search` with 2-3 distinctive terms (fewer terms = more recall; ANDed).
2. No results: retry with `--any` or a single strong term.
3. Drill in with `show <chunk_id>` for the full exchange, `session <prefix>` for surrounding turns.
4. Cite findings with session id + date so the user can locate the original.

## Notes

- Exchange = one real user turn + assistant replies until the next. Injected skill bodies / system reminders / tool results are stripped.
- Subagent transcripts and claude-mem observer sessions are excluded (noise).
- Ingestion is automatic. If a just-finished session is missing, run `backfill`.
- The Obsidian vault (from `~/.claude/brain-config.json` or `$BRAIN_VAULT`) is indexed too, under `--project obsidian-vault`; `backfill` keeps it fresh.

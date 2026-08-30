# Brain skills - what each one does and when Claude uses it

Drop this file into any project (or keep it open) and Claude Code understands the whole stack. Every skill below is either shipped by the brain plugin or installed with one command. The auto-use rules in [CLAUDE-UPGRADE.md](CLAUDE-UPGRADE.md) make Claude reach for them without being asked.

## Install (once)

```
/plugin marketplace add peleg-jpg/brain
/plugin install brain@brain
/brain-init
```

`/brain-init` installs the tooling (yt-dlp, ffmpeg, whisper, graphify), creates the vault, copies the starter notes, writes `~/.claude/brain-config.json` and merges the framework rules + the auto-use rules into `~/.claude/CLAUDE.md`.

Two pieces are third-party and install separately:

```
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem@thedotmack
```

```
uv tool install graphifyy      # or: pip install graphifyy
graphify install --platform claude
```

## The map

| Layer | What lives there | Skill that owns it |
| --- | --- | --- |
| Obsidian vault | evolving knowledge: video insights, research, patterns, project learnings | yt-capture, vault-ingest, harvest |
| graphify | the map over the vault: concepts, links, communities | graphify |
| auto-memory (`~/.claude/projects/<slug>/memory/`) | how the user wants Claude to work: corrections, project pointers | brain-router, dream |
| claude-mem | frozen record of what happened in each session, injected next session | claude-mem |
| transcript-memory | full-text search over every past transcript | transcript-memory (+ hooks) |
| the whole thing | health: broken links, stale graph, raw/ backlog, memory budget | brain-doctor |

## The skills

### /yt-capture
Drop a YouTube URL. Claude downloads, transcribes (captions first, whisper fallback) and saves a raw note to `raw/`, then offers the 4-option ingest menu.
Triggers: a YouTube URL, "save this video", "transcribe this".

### /vault-ingest
Turns anything in `raw/` (video transcript, clipped article) into wiki notes: extracts insights, updates existing notes surgically, links, cleans raw/, rebuilds the graph, prints a summary card.
Triggers: "ingest this", "obsidian this", "process raw/", after /yt-capture.

### graphify (third-party, by the graphify project)
Builds `graphify-out/graph.json` + an interactive HTML from the vault. Two commands matter daily:
- `graphify query "<topic>"` from the vault root: returns only the notes connected to the topic. Claude runs this BEFORE reading notes. This is the biggest token saver in the stack.
- `/graphify . --update` after any vault write: incremental rebuild. Git hooks do not regraph markdown, so this is explicit.

### brain-router
Not a command, a decision table. Answers "where does this go?" for every "remember this". One fact, one home: corrections -> auto-memory feedback file; evolving knowledge -> vault; frozen events -> claude-mem; transcripts -> archive, never the vault.
Triggers: "remember", "don't forget", "save this", any correction, any write to a memory layer.

### /dream
Janitor for auto-memory. Dry-run first: strips stale trailers, fixes the MEMORY.md index, re-indexes orphan files, drops ghost links, keeps the index under 200 lines by demoting prose into topic files. Snapshot before every apply, restore command printed.
Triggers: "/dream", "clean up my memory", MEMORY.md over budget, contradicting memories.

### /harvest
The only way your OWN work enters the wiki. Takes a shipped project or closed milestone, pulls the learning from git log + claude-mem + auto-memory + transcript-memory, distills one screen of "what would I want to know before doing this again", places it in the right domain folder, cross-links, regraphs, logs.
Triggers: "harvest this", "distill this project", "turn this into a wiki note", a finished milestone.

### /brain-doctor
Weekly checkup. `brain_scan.py` scans the vault (broken wikilinks, index drift, graph staleness, raw/ backlog, embedded transcripts, cruft), every project's MEMORY.md budget and claude-mem counts. Auto-fixes the safe reversible list (links, index lines, cruft, regraph, /dream), proposes the gated list (archive backlog, strip transcripts, split monoliths, dormant folders) and waits for "go".
Triggers: "brain doctor", "check my vault", stale-feeling graph, after a batch ingest, Monday.

### transcript-memory
Stdlib SQLite FTS5 index over every completed Claude Code transcript. The plugin's hooks keep it current (SessionEnd + PreCompact ingest, SessionStart backfill) and inject the top 3 past exchanges when a prompt sounds like recall. Manual: `search`, `show`, `session`, `stats`.
Triggers: "did we", "last time", "how did we fix", "find that session", "have we solved this".

### claude-mem (third-party, by thedotmack)
Observes each session, stores curated observations, injects a compact index at the next session start. Frozen layer: what happened, decisions, bugs. Search with `mem-search`.
Triggers: automatic; "did we already solve this?", "how did we do X last time?".

### /diary and /reflect (optional)
Older, manual alternative to claude-mem: /diary writes a structured session entry, /reflect synthesizes patterns across entries and proposes CLAUDE.md updates. If claude-mem is installed you rarely need them.

## A normal day

1. Session starts. claude-mem injects the index of past work; transcript-memory backfills silently.
2. You drop a YouTube link. /yt-capture -> raw/ -> "ingest now" -> wiki notes updated -> `/graphify . --update` -> summary card.
3. You ask about a topic. Claude runs `graphify query` first and reads only 3 notes instead of 30.
4. You correct Claude ("not like that, like this"). brain-router routes it to a `feedback_*` memory file. Next session it does not repeat the mistake.
5. You ship something. Claude offers /harvest; one evergreen note lands in the vault.
6. Monday. /brain-doctor runs, fixes links and the graph, asks about the 12 files sitting in raw/.
7. MEMORY.md crosses 200 lines. /dream trims it, you approve the diff.

## Boundaries that keep it honest

- Frozen material (transcripts, session logs) never enters the vault. Insights do.
- Nothing is deleted by maintenance: it is moved to `~/brain-archive/` or snapshotted to `~/.dream-snapshots/`.
- Skills never edit your CLAUDE.md on their own; /brain-init asks, /dream and /reflect propose.

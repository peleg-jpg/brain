---
name: yt-capture
description: Capture a YouTube video into the brain vault - download, transcribe, and stage for ingestion. Use when user drops a YouTube URL, says "save this video", "transcribe this", "ingest this video", "/yt-capture", or pastes a bare YouTube URL with no other instruction.
tools: Read, Write, Bash
---

# YouTube Capture

Drop a YouTube URL → get a clean, structured note in the vault's `raw/` folder ready for ingestion into the wiki.

## Workflow (3 steps)

### Step 1: Capture (automatic, no user input needed)

Read the vault path from `~/.claude/brain-config.json`. If the file is missing, tell the user to run `/brain-init` first.

Run the capture script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/yt-to-raw.py" "<URL>" "<vault-path>"
```

The script:

- Fetches title, channel, duration, upload date via `yt-dlp`
- Tries auto-captions first (fast, free)
- Falls back to whisper transcription if no captions available (slower, local)
- Saves a markdown note to `<vault>/raw/yt-<date>-<slug>.md` with frontmatter and full transcript

Show a one-line confirmation:
**Title | Channel | Duration | filepath**

### Step 2: Always offer the 4 options (numbered, exactly this format)

```
What should I do with it?
1. ingest now (default - extract insights, update wiki, delete raw)
2. ingest + archive (save full transcript externally, then delete raw)
3. ingest + keep raw (extract but leave source for follow-up)
4. leave in raw/ for later
```

Wait for the user to pick a number or keyword. Never ingest silently.

### Step 3: After ingest (options 1/2/3), ALWAYS show this summary card

```
INGESTED: [Video Title]
Channel: [Name] | Duration: [X min] | Uploaded: [YYYY-MM-DD]

Wiki notes updated (or created):
  - [[note-path-1]] - one-line what changed
  - [[note-path-2]] - one-line what changed

Key insights captured:
  - insight 1 (one line)
  - insight 2 (one line)
  - insight 3 (one line)
  (3-6 bullets max - the hard takeaways)

Raw file: [deleted / archived / kept in raw/]
Log: _log.md updated
```

Never skip the summary - it's how the user verifies what was actually captured. If an ingest touched zero existing notes and created zero new ones, that's a failure mode - say so explicitly.

## Ingestion (when user picks option 1, 2, or 3)

For ingestion, hand off to the `vault-ingest` skill - it implements Karpathy's 4 maintenance principles (think before writing, simplicity, surgical changes, goal-driven) and updates `wiki/index.md` and `_log.md` correctly.

## Failure modes

- yt-dlp not installed: tell user to run `/brain-init` (which runs `install-deps.sh`)
- No captions + no whisper: tell user to install whisper or pick a video with captions
- Vault config missing: tell user to run `/brain-init`
- URL not a valid YouTube URL: ask user to paste a real URL

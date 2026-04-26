---
name: vault-ingest
description: Process raw captures into structured wiki notes using Karpathy's 4 maintenance principles. Use when user says "ingest", "process raw", "/vault-ingest", or after capturing a video and choosing options 1, 2, or 3 in the yt-capture flow.
tools: Read, Write, Edit, Bash, Glob, Grep
---

# Vault Ingest

Transform raw captures (in `<vault>/raw/`) into clean, cross-linked wiki notes (in `<vault>/wiki/`) following the four discipline principles.

## The Four Principles (apply to every ingest)

1. **Think first.** State what wiki notes are likely affected before touching anything. If unsure, ask the user. Do not start writing blind.
2. **Simplicity.** Update an existing note when you can, rather than creating a new one. New notes only when the topic genuinely doesn't fit anywhere.
3. **Surgical changes.** Every line you change must trace back to the raw capture. No drive-by reformatting. No "while I'm here" cleanup.
4. **Goal-driven.** Convert vague intent ("research X") into a verifiable goal ("answer the question Y by capturing fact Z in note W") before executing.

## Workflow

### Step 1: Find the raw file

Read vault path from `~/.claude/brain-config.json`. Look in `<vault>/raw/` for the file to ingest. If multiple unprocessed raws exist, ask the user which to ingest (or all).

### Step 2: Read and classify

Read the raw note. Identify:

- The core topic (one of the master wiki page topics, or a new one)
- Key insights (3-6 hard takeaways)
- Connections to existing wiki concepts (use Grep to find related notes)

### Step 3: Apply Principle 1 - state intent

Before writing anything, tell the user:

- "I think this affects the following wiki notes: [list]"
- "I plan to: [add section X to note Y / create new note Z / update wikilinks in N notes]"
- Wait for confirmation if the plan is non-obvious.

### Step 4: Update the wiki

Apply Principle 2: prefer editing existing notes over creating new ones. Apply Principle 3: every change traces to the raw. Use the Edit tool with surgical replacements, not full-file rewrites.

If creating a new note, place it in the appropriate domain folder (never at vault root). Name it with kebab-case-after-content (e.g., `hook-formulas.md`, not `note-2026-04-26.md`).

### Step 5: Update the index

Add a one-line entry to `<vault>/wiki/index.md` (or whatever the index file is named). Keep it under 80 chars. Group it under the correct domain heading.

### Step 6: Update the log

Append a one-line entry to `<vault>/_log.md`:

```
2026-04-26 | ingested yt-2026-04-26-<slug> | updated [[hooks-and-retention]], created [[curiosity-loops]]
```

### Step 7: Handle the raw file

Per the user's choice in `/yt-capture`:

- Option 1 (default): delete the raw file
- Option 2: archive externally (claude-mem if installed, or a designated archive folder), then delete
- Option 3: keep in raw/ for follow-up

### Step 8: Print the summary card

Show the standard summary (see `yt-capture` SKILL.md step 3).

## Quality gates

- If after ingesting you touched zero existing notes AND created zero new notes, that's a failure. Say so.
- If a wiki note grows beyond 500 lines, propose splitting it (but don't split without confirmation).
- If you create a wikilink to a non-existent note, flag it in `_log.md`.

## Vault hygiene rules

- Never paste full transcripts or raw articles into wiki notes - those belong in `raw/` or external archives. Wiki notes are synthesized insight only.
- `raw/` is a loading dock, not a warehouse. Default to deleting after ingest.
- Index entries are ONE LINE under 80 chars each.

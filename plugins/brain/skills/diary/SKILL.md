---
name: diary
description: Capture a structured diary entry from the current Claude Code session. Use when user says "/diary", "save this session", "diary entry", or before ending a substantial session (3+ tasks or 30+ minutes of work). Also runs automatically when PreCompact fires.
tools: Read, Write, Bash
---

# Session Diary

Capture the essential signal of the current Claude Code session into a dated diary file at `~/.claude/memory/diary/YYYY-MM-DD-HHMM.md`.

## What goes in a diary entry

A diary entry is a short structured snapshot. NOT a full transcript. The aim is "what did we decide, what did we learn, what's still open" - captured in minutes, not hours.

Required sections:

```markdown
---
date: YYYY-MM-DD
session-start: HH:MM
session-end: HH:MM
project: <inferred from cwd>
---

## What we worked on

<2-4 bullets - the actual tasks completed>

## What we learned

<1-3 bullets - non-obvious insights worth keeping>

## What's still open

<0-3 bullets - todos, blockers, follow-ups>

## Patterns worth flagging

<0-3 bullets - repeated mistakes or successful approaches that might inform CLAUDE.md>
```

## Workflow

### Step 1: Determine the diary location

Diary entries go to `~/.claude/memory/diary/`. Create the directory if missing. Name format: `YYYY-MM-DD-HHMM.md` (24-hour, local time).

### Step 2: Synthesize from session context

You have access to the entire current session context. Pull from:

- The user's original requests
- What was actually built/changed/decided
- Any corrections the user gave
- Any non-obvious technical learnings

Skip:

- Verbatim transcript chunks
- Routine tool calls
- File diffs (they're in git)

### Step 3: Write the entry

Use the template above. Keep total length under 500 words. The aim is signal, not completeness.

### Step 4: Confirm

Print the file path and a 1-line summary of what was captured.

## When to run automatically

- Before any substantial session ends (3+ tasks completed or 30+ minutes of work)
- When PreCompact event fires (capture context before it's compressed)
- When user explicitly invokes

## Pruning

Diary files older than 90 days can be archived or deleted. The `reflect` skill aggregates patterns across diary entries - once reflected on, individual entries lose value.

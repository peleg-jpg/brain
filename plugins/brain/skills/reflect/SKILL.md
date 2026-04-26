---
name: reflect
description: Analyze recent diary entries to identify patterns and propose CLAUDE.md updates. Use when user says "/reflect", "review my sessions", "find patterns in my diary", or when 5+ unprocessed diary entries accumulate.
tools: Read, Write, Edit, Glob, Grep
---

# Session Reflection

Synthesize patterns across recent diary entries and propose targeted updates to the user's CLAUDE.md (project-level or global).

## What this skill does

Reads recent diary entries from `~/.claude/memory/diary/`, identifies recurring patterns (repeated corrections, successful approaches, blockers), and proposes specific CLAUDE.md additions. Never edits CLAUDE.md without user confirmation.

## Workflow

### Step 1: Gather diary entries

List all diary files in `~/.claude/memory/diary/` from the last 30 days (or since the last reflection, tracked in `~/.claude/memory/reflections/_last-run.txt`).

If fewer than 3 entries exist, tell the user there's not enough signal yet - come back when more sessions have accumulated.

### Step 2: Identify patterns

Read the gathered entries. Look for:

**Recurring corrections** - the user said "no, don't do X" or "stop doing Y" multiple times across sessions. These are strong CLAUDE.md candidates.

**Validated approaches** - non-obvious choices the user accepted without pushback, multiple times. Worth codifying.

**Recurring blockers** - same kind of error or confusion appearing in multiple sessions. May indicate missing tooling, missing context, or a workflow gap.

**Project-specific patterns** - observations that only apply to one project (vs global). Route these to that project's CLAUDE.md, not the global one.

### Step 3: Draft the synthesis

Write to `~/.claude/memory/reflections/YYYY-MM-DD-reflection.md`:

```markdown
---
date: YYYY-MM-DD
diary-entries-reviewed: <N>
date-range: YYYY-MM-DD to YYYY-MM-DD
---

## Recurring patterns

1. **<Pattern name>** - <description>
   - Evidence: <which diary entries showed this>
   - Proposed CLAUDE.md addition: `<the rule>`
   - Target: <global ~/.claude/CLAUDE.md | project /path/CLAUDE.md>

2. ...
```

### Step 4: Present to user

Show the synthesis. For each proposed CLAUDE.md addition, ask explicitly:

- Apply this addition? (yes/no/edit)

If yes: use Edit to add the rule to the target CLAUDE.md, in the appropriate section.
If edit: take the user's rephrasing and apply it.
If no: skip and move on.

### Step 5: Update the last-run marker

Write today's date to `~/.claude/memory/reflections/_last-run.txt` so the next reflection only considers newer diary entries.

## What NOT to propose

- Code style rules that lint already enforces
- Project-architecture facts (those go in CLAUDE.md naturally as the project evolves)
- One-off corrections that haven't recurred
- Anything that would balloon CLAUDE.md beyond its useful size

## Frequency

Run when 5+ unprocessed diary entries exist, or weekly, whichever comes first. Don't reflect after every session - patterns need a few data points to be real.

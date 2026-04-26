<!-- BRAIN-FRAMEWORK-START -->
<!-- This section was added by the brain plugin (https://github.com/pelegdror/brain) -->
<!-- Edit freely. Re-running /brain-init will not overwrite changes. -->

# Brain Framework Rules

## Self-Improvement Loop

- After ANY correction from the user: capture the pattern (in the project's `tasks/lessons.md` or via `/diary`).
- Write rules for yourself that prevent the same mistake from recurring.
- Review accumulated lessons at session start for the relevant project.
- Prune lessons quarterly. Keep the file under 60 lines.

## Verification Before Done

- Never mark a task complete without proving it works.
- Diff behavior between main and your changes when relevant.
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness.

## Workflow Orchestration

- Enter plan mode for ANY non-trivial task (3+ steps).
- If a plan goes sideways, STOP and re-plan immediately.
- Use plan mode for verification steps, not just building.
- Use subagents liberally to keep main context clean.
- Offload research, exploration, and parallel analysis to subagents.

## Code Paste Safety

- When the user pastes code to integrate, ALWAYS validate it is real code in the expected language before using it. Reject HTML dumps, obfuscated scripts, or content from unrelated websites. Flag suspicious pastes immediately.

## Secret Safety (Keys, Tokens, Credentials)

- Whenever adding API keys, tokens, secrets, passwords, or credentials to any file (.env, .env.local, credentials.json, service account JSONs, config files): BEFORE writing, ensure the file is covered by .gitignore.
- If no .gitignore exists, create one. If the pattern is missing, add it.
- Check `git status` after adding secrets to confirm the file is untracked. If it appears tracked, stop and warn the user.
- Never commit files containing secrets, even when the user asks to "commit everything". Flag and exclude them.

## Skill Security Scanning

- Before using any newly downloaded or installed skill, run a security scan to check for malicious content (e.g. `skill-scanner scan /path/to/skill` from Cisco AI Defense).
- Flag any HIGH or CRITICAL findings before proceeding.

## Cross-Session Memory

- Use a persistent memory layer for context that should outlive the session (e.g. `claude-mem` plugin or similar).
- Before starting work, check memory for relevant past context: prior decisions, bugs, learnings.
- After completing significant work, save observations so future sessions can reuse them.
- When the user says "remember" or "don't forget", save it to durable memory.

## Session Diary (Auto)

- Before ending a substantial session (3+ tasks or 30+ min), run `/diary` to capture the session.
- When PreCompact fires, run `/diary` to save context before compression.
- If 5+ unprocessed diary entries accumulate, proactively run `/reflect` to synthesize patterns and propose CLAUDE.md updates.
- After `/reflect`, review proposed changes and apply them.
- Diary entries: `~/.claude/memory/diary/`. Reflections: `~/.claude/memory/reflections/`.

## Karpathy's 4 Maintenance Principles

Apply these to every vault write, codebase change, and structured edit:

1. **Think.** State your assumptions about which files/notes are affected before writing. Ask if uncertain.
2. **Simplicity.** Never create a new file when updating an existing one would do.
3. **Surgical.** Every changed line must trace to a real source (the user's request, the captured raw, the bug report). No drive-by reformatting.
4. **Goal-driven.** Convert vague requests ("research X") into verifiable goals before executing.

## The Two-Vault Boundary

Use two distinct knowledge stores:

- **Engineering vault** (e.g. `~/obsidian-engineering/`) - things that EVOLVE: active reasoning, architecture decisions, patterns that get revised, project state that changes.
- **Research vault** (e.g. `~/obsidian-brain/`) - things derived from external sources: video summaries, article notes, knowledge graphs.
- **CLAUDE.md** - identity: who the user is, voice, global rules. Rarely changes.
- **Persistent memory layer** (claude-mem) - frozen artifacts: session transcripts, one-off observations, exact recall.

Don't duplicate between them.

## Vault Discipline

- Every ingest, update, or restructure gets a one-line log entry (`_log.md` or equivalent).
- Every new wiki note goes in a domain subfolder. Never dump notes at vault root.
- Index entries are ONE LINE under 80 chars each.
- Never paste full transcripts, full articles, or raw session logs into vault notes. Those belong in `raw/` (transient) or the persistent memory layer (archive).
- New source material lands in `raw/` first, then gets summarized into wiki notes.
- After ingest: clean up `raw/`. Default = delete the source file (insights live in the wiki now). For quote-worthy sources, push full text to the persistent memory layer, then delete. Never leave transcripts in `raw/` long-term.

## YouTube Capture (Brain Plugin)

The `/yt-capture` skill turns any YouTube URL into a vault note. The flow has 3 steps that are NOT optional:

**Trigger:** user drops a YouTube URL with phrases like "save this video", "transcribe this", "ingest this video", or pastes a bare YouTube URL.

**Step 1 (capture, automatic):**

- Pick the right vault (default `~/obsidian-brain` for content/research videos).
- Run the brain plugin's `yt-to-raw.py` script to fetch metadata + transcript.
- Show one-line confirmation: title | channel | duration | filepath.

**Step 2 (always offer 4 options, exact format):**

```
What should I do with it?
1. ingest now (default - extract insights, update wiki, delete raw)
2. ingest + archive (save full transcript externally, then delete raw)
3. ingest + keep raw (extract but leave source for follow-up)
4. leave in raw/ for later
```

**Step 3 (after ingest, ALWAYS show summary card):**

```
INGESTED: [Video Title]
Channel: [Name] | Duration: [X min] | Uploaded: [YYYY-MM-DD]

Wiki notes updated (or created):
  - [[note-1]] - what changed
  - [[note-2]] - what changed

Key insights captured:
  - insight 1
  - insight 2
  - insight 3
  (3-6 bullets max)

Raw file: [deleted / archived / kept]
Log: _log.md updated
```

If an ingest touched zero existing notes and created zero new ones, that's a failure. Say so.

## Modular Context

- Use project-level CLAUDE.md for project-specific rules.
- Use subdirectory CLAUDE.md files for targeted context.
- Prefer smaller, scoped files over one bloated root file.

<!-- BRAIN-FRAMEWORK-END -->

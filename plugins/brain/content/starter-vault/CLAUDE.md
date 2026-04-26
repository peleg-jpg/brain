# Brain Vault

This is a brain vault - a research-side Obsidian vault for capturing and synthesizing knowledge from external sources (YouTube videos, articles, papers, podcasts).

## What lives here

- **raw/** - loading dock for new captures. Files here are transient. Delete after ingestion.
- **wiki/** - synthesized notes organized by topic. This is where insights live.
- **graphify-out/** - generated semantic knowledge graph. Regenerate periodically.
- **\_log.md** - one-line entry per ingest, restructure, or significant edit.
- **\_vault-index.md** - top-level index of wiki domains.

## Vault discipline (apply to every write)

1. **Think first.** State which notes are affected before writing.
2. **Simplicity.** Update existing notes when possible - new notes only when topic genuinely doesn't fit.
3. **Surgical.** Every line you change traces to a real source.
4. **Goal-driven.** Vague intent gets converted to verifiable goal before execution.

## Hard rules

- Never paste full transcripts or articles into wiki notes. Those belong in raw/ (transient) or external archive (permanent).
- raw/ is a loading dock, not a warehouse. Default = delete after ingest.
- Index entries are ONE LINE under 80 chars.
- New notes go in domain subfolders, never at vault root.
- Every ingest gets a `_log.md` entry.

## Workflow

Use the brain plugin's `/yt-capture` and `/vault-ingest` skills to ingest new content. They handle the discipline automatically.

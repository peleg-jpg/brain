# Brain Doctor - Gated Fix Playbook

Procedures for the fixes that need the user's approval. Every procedure is
move-based (reversible), never delete-based. Archive root:
`~/brain-archive/<vault-name>/<YYYY-MM>/` (create if missing).

## 1. Staging backlog (`raw/`, `_raw/`)

Defer to vault-ingest's 4-option menu - do not re-decide here.
Batch by topic, not one file at a time. After any ingest: `/graphify . --update`.

## 2. Transcript squatters

Two shapes, one principle: full transcripts are frozen material and do not
belong in an evolving vault.

**A. A `transcripts/` folder:**

- Verify wiki pages cite transcripts by video ID only (`(source: <id>)`).
- Move the whole folder to `~/brain-archive/<vault>/<YYYY-MM>/transcripts/`.
- Leave behind `transcripts/README.md` with one line pointing at the archive
  path, so `(source: id)` references stay traceable.

**B. Embedded `<details>` transcript blocks inside notes:**
For each note: keep everything above the `<details>` block (the curated
summary IS the note), extract the transcript body to
`~/brain-archive/<vault>/<YYYY-MM>/transcripts/<same-relative-path>`,
and replace the block with one line: `Transcript: archived <archive-path>`.
`scripts/strip_transcripts.py <vault> <subdir> <archive-root>` does exactly
this; dry-run by default, `--apply` to write. Show the diff on 3 notes first,
then run the batch. Effect: the vault shrinks and the graph stops indexing
raw transcript text.

## 3. Monolithic pages (5,000+ words)

Split ONE page per session, not all at once (quality over bulk):

- Extract each `##` section that stands alone as a concept into its own note
  (kebab-case name, frontmatter: `created / updated / tags / sources`).
- The original page becomes a hub: one-paragraph overview + links to the
  atomic notes. This is what fixes a starved backlink graph - links need
  atomic targets to point at.
- Update the index, log, regraph.

## 4. Dormant domains

For folders with 0 edits in 30+ days: ask one question per folder -
"still active?" If yes, schedule a refresh of its status note. If no, move
the folder to the archive and drop its index entries. Do not guess; project
status is the user's call.

## 5. Frontmatter backfill (optional, low priority)

When touching a note for any other reason, add missing frontmatter
(`created` from file birth time, `updated` from mtime, `tags` from folder,
`sources` if derivable). Do not run a vault-wide backfill as its own job -
it is churn with no knowledge gain.

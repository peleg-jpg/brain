# Philosophy

The brain plugin is built on four ideas. None of them are mine. All of them have been validated in practice over a year of daily use.

## 1. Claude is a YouTube learning machine, not a code assistant

The default framing of Claude Code is "AI pair programmer". That's true but undersells what it can do.

The bigger unlock: Claude can ingest external knowledge - videos, articles, papers, podcasts - faster than any human can. With the right workflow, every YouTube video you watch becomes a permanent, searchable, cross-linked addition to your personal knowledge graph. Five minutes of capture per video. No notes to take. No transcripts to skim later. Just: drop URL, get summary, refine into wiki.

After a year, this compounds into something a human alone can't build: a structured second brain that gets denser every week.

The brain plugin is the workflow that makes this real.

## 2. Two vaults, sharply separated

There's a temptation to dump everything into one giant Obsidian vault. Don't.

Use two:

- **Engineering vault** - things that EVOLVE. Active reasoning, architecture decisions, patterns that get revised, project state that changes. Edited often. Pruned often.
- **Research vault** (this one - the brain vault) - things derived from external sources. Video summaries, article notes, knowledge graphs. Append-mostly. Pruned rarely.

And two adjacent stores:

- **CLAUDE.md** - identity. Who you are, voice, global rules. Rarely changes.
- **Persistent memory layer** (e.g. claude-mem) - frozen artifacts. Session transcripts, one-off observations, exact recall. Never edited.

The discipline is: don't duplicate between them, and route every new thing to exactly one.

## 3. Karpathy's 4 maintenance principles

Andrej Karpathy has written about how to keep AI-assisted projects from rotting. Four rules:

1. **Think.** State your assumptions about which files are affected before writing. Ask if uncertain.
2. **Simplicity.** Never create a new file when updating an existing one would do.
3. **Surgical.** Every changed line traces back to a real source. No drive-by reformatting.
4. **Goal-driven.** Convert vague requests into verifiable goals before executing.

These apply to vault writes, codebase changes, and structured edits equally. The brain plugin's `vault-ingest` skill enforces them at every ingest.

The point: AI can write fast. It will gladly write five paragraphs when one will do. It will gladly create a new file when an edit would suffice. The discipline is to slow it down at exactly the moment it wants to speed up.

## 4. Pre-shipped worked example, not empty skeleton

Most "framework" packages ship empty. New user installs, opens it, sees blank folders, doesn't know what success looks like, gives up.

The brain plugin ships 148 worked notes - synthesized from one creator's video corpus on content strategy. You install it, you open the vault, and you immediately see "oh, this is what my vault will look like after a few months of capture." You can search across 146 notes. You can query the 614-node graph. You can browse the 17 master wiki pages.

Then you start capturing your own videos and the vault grows from there.

Empty skeletons require imagination to use. Worked examples require nothing.

## Why "brain"

It's the shortest name for what it actually is. Not "knowledge OS" (too grand). Not "youtube-cli" (too narrow). Just brain. The thing you're building externally to extend your own.

## On the starter content

The 146 notes are anonymized study synthesis derived from publicly available videos by one content creator. The creator's name has been stripped and all direct quotes have been paraphrased. The notes are treated as transformative study material - my interpretation of patterns, not republished content. URLs to source videos have been removed.

If the creator wants the content removed, open an issue. The framework value is the workflow, not the specific content - other users can build their own knowledge bases from creators they choose.

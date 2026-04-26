# Workflow

The full ingestion flow, end to end.

## The shape

```
YouTube URL
    |
    v
[/yt-capture]
    |
    +--> yt-dlp downloads metadata + auto-captions
    |       (or whisper transcribes audio if no captions)
    |
    v
<vault>/raw/yt-2026-04-26-<slug>.md
    |
    v
[user picks: ingest now / ingest + archive / ingest + keep / leave]
    |
    v
[/vault-ingest]
    |
    +--> read raw note
    +--> classify topic (one of 16 master pages, or new)
    +--> Karpathy 1: think first - state which wiki notes are affected
    +--> Karpathy 2: simplicity - update existing notes when possible
    +--> Karpathy 3: surgical - every change traces to the raw
    +--> Karpathy 4: goal-driven - convert intent to verifiable goal
    |
    v
<vault>/wiki/<topic>.md       (updated)
<vault>/wiki/index.md          (one-line entry added)
<vault>/_log.md                (one-line ingestion record)
    |
    v
[summary card shown to user]
    |
    v
raw file: deleted / archived / kept (per user choice)
    |
    v
[periodic: graphify regenerates the semantic graph]
    |
    v
<vault>/graphify-out/.graphify_semantic.json
```

## Example end-to-end run

User pastes a URL:

```
/yt-capture https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Claude:

```
-> Fetching metadata for https://www.youtube.com/watch?v=dQw4w9WgXcQ
-> Title: Never Gonna Give You Up
-> Trying auto-captions first
[saved] /Users/you/obsidian-brain/raw/yt-2026-04-26-never-gonna-give-you-up.md

What should I do with it?
1. ingest now (default - extract insights, update wiki, delete raw)
2. ingest + archive (save full transcript externally, then delete raw)
3. ingest + keep raw (extract but leave source for follow-up)
4. leave in raw/ for later
```

User picks `1`. Claude:

```
Reading raw note. The core topic is on-camera presence and emotional commitment.

I think this affects:
  - wiki/on-camera-presence.md (existing - I'll add a section on commitment)

Plan: append a new section "Emotional commitment as a hook" to on-camera-presence.md, with 3 tactics from this video. No new notes needed.

Confirm? [Y/n]
```

User confirms. Claude updates the wiki note surgically, adds an index entry, logs the ingest, deletes the raw file, then prints:

```
INGESTED: Never Gonna Give You Up
Channel: Rick Astley | Duration: 3 min | Uploaded: 2009-10-25

Wiki notes updated:
  - [[on-camera-presence]] - added "Emotional commitment as a hook" section

Key insights captured:
  - emotional commitment in delivery beats technical perfection
  - reaction-style hooks work because they feel low-stakes
  - earnestness is rare on platform and self-selecting

Raw file: deleted
Log: _log.md updated
```

That's the loop. Repeat for every video you'd otherwise just watch.

## Vault hygiene

Rules baked into the workflow:

- `raw/` is a loading dock, not a warehouse. Default = delete after ingest.
- Wiki notes are synthesized insight, not transcripts. Never paste raw text in.
- Index entries are ONE LINE under 80 chars.
- New notes go in domain subfolders, never at vault root.
- Every ingest gets a `_log.md` entry.

## Querying the knowledge graph

After enough notes accumulate, regenerate the semantic graph:

```bash
graphify build --vault ~/obsidian-brain
```

Then query it:

```bash
graphify query "what makes a good hook" --graph ~/obsidian-brain/graphify-out/.graphify_semantic.json
```

The graph surfaces concept clusters, central nodes ("god nodes"), and bridges between communities. Useful when you want to ask "what do I actually know about X" across hundreds of notes.

## When to use which skill

| Skill               | When to use                                                     |
| ------------------- | --------------------------------------------------------------- |
| `/brain-init`       | Once, after installing the plugin                               |
| `/yt-capture <url>` | Every YouTube video worth keeping                               |
| `/vault-ingest`     | After capturing, OR when raw/ has accumulated unprocessed files |
| `/diary`            | At the end of any substantial session                           |
| `/reflect`          | Weekly, OR when 5+ unprocessed diary entries accumulate         |

## Common failure modes

**"yt-dlp not found"** - run `/brain-init` to install dependencies.

**"No captions and whisper not installed"** - run `/brain-init` and confirm whisper install. Or pick a video that has auto-captions (most videos under 4 hours do).

**"Vault config missing"** - run `/brain-init` (you skipped it).

**`/vault-ingest` touched zero notes** - you ingested something with no signal. Check the raw file - maybe it's an off-topic ramble. Either delete it or pick a different angle to extract.

**Wiki note is over 500 lines** - propose splitting it. Don't split without confirmation.

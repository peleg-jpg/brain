# brain

Turn Claude Code into a YouTube learning machine. Drop a YouTube URL, Claude downloads it, transcribes it, summarizes it into your Obsidian vault, and grows a semantic knowledge graph over time.

Ships with a **worked starter vault**: 146 anonymized study notes + 16 master wiki pages + a 614-node knowledge graph, so the system is useful from day one - not just an empty skeleton.

## Install

### Recommended: download the bundle

**[Download brain-bundle-v0.1.0.zip](https://github.com/peleg-jpg/brain/releases/download/v0.1.0/brain-bundle-v0.1.0.zip)** (632 MB - includes Obsidian for Mac, Windows, Linux)

1. Download and unzip
2. Open the unzipped folder, read `README.txt`
3. Run the installer:
   - Mac / Linux / WSL: `bash install.sh`
   - Native Windows: right-click `install.ps1` -> "Run with PowerShell"
4. Follow the prompts (it asks before each install step)

The installer:

1. Installs Homebrew (Mac/Linux) or uses winget (Windows) if missing
2. Installs YouTube tooling (`yt-dlp`, `ffmpeg`, `whisper`, `graphify`) - prompts each
3. Installs Obsidian from the bundled installer (no separate download needed)
4. Copies the 5 skills to `~/.claude/skills/`
5. Creates a vault at `~/obsidian-brain` (or wherever you choose)
6. Copies the 146-note starter vault into it
7. Merges the framework rules into your `~/.claude/CLAUDE.md`
8. Tells you what to do next (including: open Obsidian and add the vault folder)

## What you get

### Skills

- **`/brain-init`** - one-time setup wizard
- **`/yt-capture`** - drop a YouTube URL, get a clean note in your vault
- **`/vault-ingest`** - process raw captures into the wiki using Karpathy's 4 maintenance principles
- **`/diary`** - capture session context into a structured diary entry
- **`/reflect`** - synthesize patterns across diary entries and propose CLAUDE.md updates

### Starter vault content

- **146 anonymized study notes** - synthesized insights from one creator's video corpus on content strategy, growth, monetization, and creator psychology. Each note is ~500 words of paraphrased, instructional prose with wikilinks to the master topics.
- **16 master wiki pages** organized into Content Strategy, Growth and Algorithm, Monetization, and Creator Skills. Cross-linked, with concrete frameworks and tactics.
- **A 614-node semantic knowledge graph** built by `graphify` from the wiki content. Query with `graphify query "<topic>"`.

### Framework rules

The setup wizard merges a curated set of rules into your `~/.claude/CLAUDE.md`:

- Self-improvement loop (capture corrections in lessons.md)
- Verification before done (no claiming work is complete without proving it)
- Workflow orchestration (plan mode for non-trivial tasks, subagents for parallel work)
- Code paste safety, secret safety
- Karpathy's 4 maintenance principles (think, simplicity, surgical, goal-driven)
- The two-vault boundary (engineering vs research vs identity vs frozen)
- Vault discipline (one-line index entries, raw/ as loading dock not warehouse)
- The 3-step YouTube capture flow

## Quick start (after install)

Try it on a real video:

```
/yt-capture https://www.youtube.com/watch?v=<some-video-id>
```

Claude will download it, transcribe it, save it to `<vault>/raw/`, then offer four options:

```
1. ingest now (default - extract insights, update wiki, delete raw)
2. ingest + archive (save full transcript externally, then delete raw)
3. ingest + keep raw (extract but leave source for follow-up)
4. leave in raw/ for later
```

Pick `1` and Claude updates your wiki, surgical-style, and shows you exactly what changed.

## How the starter vault was made

The 146 starter notes are anonymized study notes synthesized from publicly available videos by a single content creator. The creator's name has been stripped, all direct quotes have been paraphrased, and all source URLs have been removed. The notes are treated as transformative study material rather than republished content.

If you want to study a specific creator yourself, use the `/yt-capture` workflow on their videos - you'll build your own knowledge base over time. The shipped 146 are there as a worked example so you see what your vault will look like after a few months of capture.

## Philosophy

Read [docs/philosophy.md](docs/philosophy.md) for the thesis behind this plugin: why two vaults, why Karpathy's 4 principles, why pre-shipped notes, and why "Claude as YouTube learning machine" is a different framing from "Claude as code assistant."

Read [docs/workflow.md](docs/workflow.md) for the operational guide: full ingestion flow with examples.

## Requirements

- Claude Code (`claude` CLI installed)
- macOS, Linux, Windows (via WSL), or Windows native
- Python 3.8+
- Disk: ~50MB for the plugin + ~100MB for the starter vault + 2GB for whisper models (only if you let it install whisper)

## Installing Obsidian (per platform)

The vault works as plain markdown in any editor. To get the full experience (graph view, wikilink navigation, plugins), install Obsidian:

| Platform    | How                                                                                                                                                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **macOS**   | `/brain-init` will offer to run `brew install --cask obsidian` for you                                                                                                                                              |
| **Linux**   | Download from https://obsidian.md/download (AppImage, snap, or flatpak)                                                                                                                                             |
| **Windows** | **Download installer from https://obsidian.md/download** (the .exe)                                                                                                                                                 |
| **WSL**     | Install Obsidian on the **Windows** side (not WSL) using the link above. Then in Obsidian, point at your vault path via `\\wsl.localhost\Ubuntu\home\<user>\obsidian-brain` or copy the vault to a Windows location |

After install, open Obsidian, click "Open folder as vault", and pick your vault path (default `~/obsidian-brain`).

## License

MIT. See [LICENSE](LICENSE).

## Credits

Built by [Peleg Dror](https://pelegdror.com).

The starter vault content is anonymized study synthesis derived from publicly available videos by one content creator. All identifying info has been stripped and direct quotes paraphrased. If you're the creator and want it pulled, open an issue.

The vault discipline rules are inspired by Andrej Karpathy's writing on context-engineering and AI workflow design.

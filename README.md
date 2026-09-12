# brain

Turn Claude Code into a YouTube learning machine. Drop a YouTube URL, Claude downloads it, transcribes it, summarizes it into your Obsidian vault, and grows a semantic knowledge graph over time.

Ships with a **worked starter vault**: 146 anonymized study notes + 16 master wiki pages + a 614-node knowledge graph, so the system is useful from day one - not just an empty skeleton.

## Install

One command. No prompts, no `/brain-init`, everything lands in one go:

```
git clone https://github.com/peleg-jpg/brain && cd brain && bash install.sh
```

Or open the downloaded folder in VS Code: it runs `install.sh` for you in the terminal the first time (click "Trust" when VS Code asks, allow automatic tasks if prompted).

Or without cloning:

```
curl -fsSL https://raw.githubusercontent.com/peleg-jpg/brain/main/install.sh | bash
```

What `install.sh` does (Mac / Linux / WSL):

1. Installs Homebrew (Mac, if missing), then `yt-dlp`, `ffmpeg`, `whisper`, `graphify`, Obsidian
2. Installs the brain plugin into Claude Code: all 10 skills + 4 hooks
3. Installs the claude-mem plugin (cross-session memory)
4. Registers the graphify skill with Claude Code
5. Creates the vault at `~/obsidian-brain` with the 146-note starter content
6. Writes `~/.claude/brain-config.json`
7. Merges the framework + auto-use rules into `~/.claude/CLAUDE.md`

Every download explained (what, why, size, where it lands, how to undo): [docs/install.md](docs/install.md).

Requirements: Claude Code CLI installed (`claude` on PATH), git. Re-running is safe. Custom vault path: `BRAIN_VAULT=/path bash install.sh`.

Native Windows: same thing with `install.ps1`. Right-click it > "Run with PowerShell", or in PowerShell:

```
irm https://raw.githubusercontent.com/peleg-jpg/brain/main/install.ps1 | iex
```

It uses winget for git, yt-dlp, ffmpeg, uv and Obsidian, uv for python3, whisper and graphify, then the same plugin, vault, config and CLAUDE.md steps. Needs Claude Code installed first (`irm https://claude.ai/install.ps1 | iex`) and winget (App Installer from the Microsoft Store, present on Windows 10 1709+ and 11).

## What you get

### Skills

Capture and distill:

- **`/brain-init`** - one-time setup wizard
- **`/yt-capture`** - drop a YouTube URL, get a clean note in your vault
- **`/vault-ingest`** - process raw captures into the wiki using Karpathy's 4 maintenance principles
- **`/harvest`** - distill a SHIPPED project or milestone into one evergreen wiki note

Memory and hygiene:

- **`brain-router`** - "where does this go?" - one fact, one home (vault / auto-memory / claude-mem / archive)
- **`/dream`** - janitor for Claude Code auto-memory: fixes the MEMORY.md index, keeps it under budget, snapshot before every write
- **`/brain-doctor`** - weekly checkup: broken wikilinks, stale graph, raw/ backlog, memory budget. Auto-fixes the safe list, proposes the rest
- **`transcript-memory`** - stdlib full-text search over every past Claude Code session. Plugin hooks index sessions automatically and inject past work when you ask "did we / last time / how did we fix"
- **`/diary`** and **`/reflect`** - optional manual session capture + pattern synthesis

Third-party pieces (installed separately, not vendored):

- **graphify** - the knowledge graph over the vault (`graphify query "<topic>"` before reading, `/graphify . --update` after writing). `/brain-init` installs it.
- **claude-mem** - frozen cross-session memory: `/plugin marketplace add thedotmack/claude-mem` then `/plugin install claude-mem@thedotmack`

Read **[SKILLS.md](SKILLS.md)** for what each skill does and when Claude reaches for it, and **[CLAUDE-UPGRADE.md](CLAUDE-UPGRADE.md)** for the auto-use rules that make Claude use them without being asked (merged by `/brain-init`, or paste it yourself).

### Starter vault content

- **146 anonymized study notes** - synthesized insights from one creator's video corpus on content strategy, growth, monetization, and creator psychology. Each note is ~500 words of paraphrased, instructional prose with wikilinks to the master topics.
- **16 master wiki pages** organized into Content Strategy, Growth and Algorithm, Monetization, and Creator Skills. Cross-linked, with concrete frameworks and tactics.
- **A 614-node semantic knowledge graph** built by `graphify` from the wiki content. Query with `graphify query "<topic>"`.

### Framework rules

The setup wizard merges a curated set of rules into your `~/.claude/CLAUDE.md`:

- Self-improvement loop (corrections become auto-memory feedback files, janitored by /dream)
- Verification before done (no claiming work is complete without proving it)
- Workflow orchestration (plan mode for non-trivial tasks, subagents for parallel work)
- Code paste safety, secret safety
- Karpathy's 4 maintenance principles (think, simplicity, surgical, goal-driven)
- The two-vault boundary (engineering vs research vs identity vs frozen)
- Vault discipline (one-line index entries, raw/ as loading dock not warehouse)
- The 3-step YouTube capture flow
- Auto-use rules: graphify query before reading, transcript recall before redoing, brain-router on every "remember", /dream and /brain-doctor on their triggers

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
- Python 3.8+ (transcript-memory uses the bundled sqlite3 FTS5, no extra packages)
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

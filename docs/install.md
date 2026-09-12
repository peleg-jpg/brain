# What the installer does, step by step

`install.sh` (Mac / Linux / WSL) and `install.ps1` (Windows) do the same seven steps. Each step prints a `== [n/7] ... ==` header so you can see where it is. Total time on a normal home connection: 5 to 15 minutes. Most of it is the whisper download.

Nothing here needs a paid account. Everything is free and open source except Claude Code itself, which you already have.

## Before you run it

| Need | Why | Get it |
| --- | --- | --- |
| Claude Code, logged in | the skills and hooks install into it | Mac/Linux: `curl -fsSL https://claude.ai/install.sh \| bash`. Windows: `irm https://claude.ai/install.ps1 \| iex` |
| Internet | every download below | |
| Mac: your password once | only if Homebrew is missing | |
| Windows: winget | the package manager the script uses | built into Windows 11 and Windows 10 1709+. If `winget` is missing, install "App Installer" from the Microsoft Store |

## The seven steps

### 1. Tooling

| Tool | What it is | Why brain needs it | Size | Installed with |
| --- | --- | --- | --- | --- |
| Homebrew (Mac only) | package manager | installs the rest | ~500 MB | official installer, skipped if present |
| git (Windows only) | version control + Git Bash | Claude Code runs the plugin hooks through Git Bash | ~300 MB | winget |
| yt-dlp | YouTube downloader | fetches video audio and auto-captions | ~15 MB | brew / apt / winget |
| ffmpeg | audio/video converter | turns downloaded audio into what whisper reads | ~100 MB | brew / apt / winget |
| uv | Python tool manager | installs whisper and graphify in their own clean environments, no pip conflicts | ~20 MB | brew / curl / winget |
| python3 (Windows only) | Python runtime | the hooks call `python3`. Mac and Linux already have it | ~60 MB | `uv python install --default` |
| openai-whisper | speech to text, runs on your machine | transcribes videos that have no captions | ~400 MB (includes PyTorch) | `uv tool install openai-whisper` |
| whisper model `turbo` | the actual speech model, downloaded once | without it the first transcription would stall for minutes | ~1.6 GB | pulled in step 1, cached in `~/.cache/whisper/` |
| graphify | knowledge graph builder | turns the vault into a graph Claude can query | ~50 MB | `uv tool install graphifyy` |
| Obsidian | the vault app | browse notes, graph view, wikilinks | ~150 MB | `brew install --cask obsidian` / winget. Linux: manual, see README |

Every tool is skipped if already on your machine. Re-running is safe.

**About the whisper model.** `turbo` is OpenAI's large-v3-turbo: large-v3 accuracy, about 8x faster, free. It is the right default for a laptop CPU. Want the full `large-v3` (2.9 GB, slower, marginally better)? Set `BRAIN_WHISPER_MODEL=large-v3` before running the installer, and again when capturing. Anything from `tiny` to `large-v3` works.

### 2. Claude Code plugins

- `brain@brain`: 10 skills (brain-init, yt-capture, vault-ingest, harvest, brain-router, dream, brain-doctor, transcript-memory, diary, reflect) and 4 hooks (SessionStart, SessionEnd, PreCompact, UserPromptSubmit). Lands in `~/.claude/plugins/`.
- `claude-mem@thedotmack`: cross-session memory, third party, free.

Both are installed with `claude plugin install`, the same thing `/plugin install` does inside Claude Code.

### 3. graphify skill

`graphify install --platform claude` registers the `/graphify` skill in `~/.claude/skills/graphify/` so Claude can rebuild the graph itself.

### 4. Vault

Copies the starter vault to `~/obsidian-brain`: 146 study notes, 16 master wiki pages, a 614-node graph, `_log.md`, `_vault-index.md`, and the vault's own `CLAUDE.md` with the discipline rules. About 2 MB. If the folder already exists and is not empty, it is left alone. Override the location with `BRAIN_VAULT=/path`.

### 5. Config

Writes `~/.claude/brain-config.json` with the vault path and plugin version. Every brain skill reads it to find the vault.

### 6. Rules

Appends the framework rules and auto-use rules to `~/.claude/CLAUDE.md`, wrapped in `<!-- BRAIN-FRAMEWORK-START -->` and `<!-- BRAIN-FRAMEWORK-END -->`. If the marker is already there, nothing is written. Delete that block to undo.

### 7. Summary

Prints OK / MISS per tool and what to do next.

## Where everything lands

| Path | What |
| --- | --- |
| `~/obsidian-brain/` | your vault |
| `~/.claude/plugins/` | brain and claude-mem plugins |
| `~/.claude/skills/graphify/` | graphify skill |
| `~/.claude/brain-config.json` | vault path |
| `~/.claude/CLAUDE.md` | rules block |
| `~/.cache/whisper/` | whisper model file |
| `~/.local/bin/` | whisper, graphify, python3 (Windows) executables |
| `~/.brain-src/` | repo clone, only when installed via `curl \| bash` or `irm \| iex` |

On Windows `~` is `C:\Users\<you>`.

## After it finishes

1. Windows: close and reopen the terminal so the new PATH applies.
2. Open Obsidian, "Open folder as vault", pick `~/obsidian-brain`.
3. Run `claude`. Type `/brain-doctor` to see it read your vault, or paste a YouTube URL.

## Checking it worked

```
claude plugin list          # brain@brain and claude-mem@thedotmack, both enabled
which yt-dlp ffmpeg whisper graphify    # Windows: Get-Command yt-dlp, ffmpeg, whisper, graphify, python3
cat ~/.claude/brain-config.json
```

The repo runs exactly these checks on a clean Mac and a clean Windows machine on every change: see the `test-install` workflow under Actions.

## Undo

- Plugins: `claude plugin uninstall brain@brain` and `claude plugin uninstall claude-mem@thedotmack`
- Rules: delete the BRAIN-FRAMEWORK block from `~/.claude/CLAUDE.md`
- Vault: delete `~/obsidian-brain` (it is yours, back it up first)
- Tools: `uv tool uninstall openai-whisper graphifyy`, then `brew uninstall` / `winget uninstall` the rest if you want them gone

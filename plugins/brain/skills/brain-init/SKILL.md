---
name: brain-init
description: First-run setup wizard for the brain plugin. Use when user installs the brain plugin for the first time, or says "set up brain", "initialize brain", "/brain-init", or asks how to get started with the brain knowledge system. Installs YouTube tooling, creates the Obsidian vault skeleton, copies the starter content, and merges the framework rules into the user's CLAUDE.md.
tools: Read, Write, Edit, Bash, Glob
---

# Brain Setup Wizard

One-time setup for the brain second-brain workflow. Run this immediately after installing the brain plugin.

## What This Does

1. Installs YouTube ingestion dependencies (`yt-dlp`, `ffmpeg`, `whisper`, `graphify`) with explicit per-tool confirmation
2. Creates an Obsidian vault at the user's chosen location (default `~/obsidian-brain`)
3. Copies the starter vault content (146 anonymized study notes + 16 master wiki pages + a 614-node semantic graph) into the vault
4. Merges the framework rules into the user's `~/.claude/CLAUDE.md` (idempotent - checks for marker before appending)
5. Prints next steps

## Workflow

### Step 1: Confirm vault location

Ask the user where to put the vault. Default: `~/obsidian-brain`. Accept any absolute path. Verify the parent directory exists and is writable. If the vault path already exists and is non-empty, ask whether to merge into it (preserves their files, only adds missing ones) or pick a different location. Never silently overwrite an existing vault.

### Step 2: Install dependencies

Run the bundled install script:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/install-deps.sh"
```

The script handles platform detection (Mac via `brew`, Linux via `apt`/`dnf`/`yum`, WSL via `apt`) and prompts before each install. Set `BRAIN_AUTO_YES=1` to skip prompts in scripted setups.

Verify all four tools are available afterward by running `which yt-dlp ffmpeg whisper graphify`. Report which ones succeeded and which need manual installation.

### Step 3: Create the vault

Create the vault directory and copy the starter content:

```bash
VAULT="<user-chosen-path>"
mkdir -p "$VAULT"
cp -R "${CLAUDE_PLUGIN_ROOT}/content/starter-vault/." "$VAULT/"
```

Verify the copy by listing `$VAULT` - should show `raw/`, `wiki/`, `graphify-out/`, `CLAUDE.md`, `_vault-index.md`, `_log.md`.

### Step 4: Merge framework rules into the user's CLAUDE.md

Read `${CLAUDE_PLUGIN_ROOT}/templates/claude-md-additions.md`. This contains the universal framework rules (Karpathy's 4 principles, vault discipline, two-vault boundary, YouTube capture flow) and the auto-use rules (when Claude reaches for graphify query, transcript recall, brain-router, /dream, /brain-doctor on its own).

Check the user's `~/.claude/CLAUDE.md` for the marker `<!-- BRAIN-FRAMEWORK-START -->`. If present, the merge has already happened - skip and tell the user it's already configured. If absent, append the template content (with the markers wrapping it) to the end of the file. Create `~/.claude/CLAUDE.md` if it doesn't exist.

Always ask the user to confirm before modifying their CLAUDE.md. Show them a diff or summary of what will be added.

### Step 5: Save vault location

Write the user's chosen vault path to `~/.claude/brain-config.json`:

```json
{
  "vault_path": "/path/the/user/chose",
  "version": "0.2.0"
}
```

All brain skills and scripts (`yt-capture`, `vault-ingest`, `harvest`, `brain-doctor`, `transcript-memory`) read this file to know where the vault lives. `$BRAIN_VAULT` overrides it.

### Step 6: Print next steps

Tell the user:

- The vault is at `<path>`. The install script offered to install Obsidian. If they accepted: open Obsidian, click "Open folder as vault", point at `<path>` to browse the 146 starter notes with graph view and wikilinks. If they declined: the vault works as plain markdown in any editor (VS Code, Foam, Logseq, plain `cat`/`grep`).
- Try `/yt-capture <youtube-url>` to capture a video
- Try `/vault-ingest` to process anything in `raw/` into the wiki
- The framework rules and auto-use rules are now active in the user's CLAUDE.md
- The plugin's hooks index every finished session into transcript-memory automatically; try `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcript_memory.py" stats` after the next session
- For cross-session observations install claude-mem: `/plugin marketplace add thedotmack/claude-mem` then `/plugin install claude-mem@thedotmack`
- Run `/brain-doctor` once a week; see SKILLS.md in the repo for the full map

## Idempotency

Safe to re-run. On second run:

- Skip dependencies that are already installed
- If vault exists and is non-empty, ask whether to merge or skip
- Skip CLAUDE.md merge if marker is already present

## Failure modes

If a step fails, report exactly which step and why. Never leave partial state without telling the user. If the vault copy half-completes, offer to clean up before retry.

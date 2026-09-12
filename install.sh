#!/usr/bin/env bash
# install.sh - one-shot brain install. No /brain-init needed afterwards.
#
#   git clone https://github.com/peleg-jpg/brain && cd brain && bash install.sh
#   or: curl -fsSL https://raw.githubusercontent.com/peleg-jpg/brain/main/install.sh | bash
#
# Does everything in one go, no prompts:
#   1. Homebrew (Mac, if missing) + yt-dlp, ffmpeg, whisper, graphify, Obsidian
#   2. brain plugin + claude-mem plugin into Claude Code (all 10 skills + hooks)
#   3. graphify skill registered with Claude Code
#   4. Vault at ~/obsidian-brain with the 146-note starter content
#   5. ~/.claude/brain-config.json
#   6. Framework rules merged into ~/.claude/CLAUDE.md
# Idempotent - re-running is safe. Override vault path: BRAIN_VAULT=/path bash install.sh

set -uo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
info()    { printf "${GREEN}-> %s${RESET}\n" "$*"; }
warn()    { printf "${YELLOW}!! %s${RESET}\n" "$*"; }
err()     { printf "${RED}xx %s${RESET}\n" "$*" >&2; }
section() { printf "\n${GREEN}== %s ==${RESET}\n" "$*"; }

REPO_URL="https://github.com/peleg-jpg/brain"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [[ -z "$SRC" || ! -d "$SRC/plugins/brain" ]]; then
    # curl | bash - no local clone, fetch one
    SRC="$HOME/.brain-src"
    section "Fetching brain source -> $SRC"
    if [[ -d "$SRC/.git" ]]; then git -C "$SRC" pull -q; else git clone -q --depth 1 "$REPO_URL" "$SRC"; fi
fi
PLUGIN="$SRC/plugins/brain"
VAULT="${BRAIN_VAULT:-$HOME/obsidian-brain}"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
export BRAIN_AUTO_YES=1
# resolve claude BEFORE touching PATH - some machines carry an older claude in ~/.local/bin
CLAUDE_BIN="$(command -v claude || true)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
[[ -z "$CLAUDE_BIN" ]] && CLAUDE_BIN="$(command -v claude || true)"

# --- 0. preflight ---
section "Preflight"
if [[ -z "$CLAUDE_BIN" ]]; then
    err "Claude Code CLI not found. Install it first: https://docs.claude.com/en/docs/claude-code/setup"
    exit 1
fi
info "claude: $("$CLAUDE_BIN" --version 2>/dev/null | head -1) ($CLAUDE_BIN)"
if [[ "$(uname -s)" == "Darwin" ]] && ! command -v brew >/dev/null 2>&1; then
    info "Homebrew missing - installing (needs your Mac password once)"
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

# --- 1. tooling ---
section "Tooling (yt-dlp, ffmpeg, whisper, graphify, Obsidian)"
bash "$PLUGIN/scripts/install-deps.sh"

# --- 2. Claude Code plugins ---
section "Claude Code plugins"
install_plugin() {  # $1 = plugin@marketplace. --yes for new CLIs, plain + closed stdin for old ones
    "$CLAUDE_BIN" plugin install "$1" --yes 2>/dev/null || "$CLAUDE_BIN" plugin install "$1" </dev/null
}
"$CLAUDE_BIN" plugin marketplace add peleg-jpg/brain >/dev/null 2>&1 || true
install_plugin brain@brain && info "brain plugin OK (10 skills + 4 hooks)" || err "brain plugin install failed"
"$CLAUDE_BIN" plugin marketplace add thedotmack/claude-mem >/dev/null 2>&1 || true
install_plugin claude-mem@thedotmack && info "claude-mem plugin OK" || warn "claude-mem install failed - cross-session memory off, install later with: claude plugin install claude-mem@thedotmack"

# --- 3. graphify skill ---
if command -v graphify >/dev/null 2>&1; then
    graphify install --platform claude >/dev/null 2>&1 && info "graphify skill registered" || warn "graphify install --platform claude failed"
fi

# --- 4. vault ---
section "Vault -> $VAULT"
if [[ -d "$VAULT" && -n "$(ls -A "$VAULT" 2>/dev/null)" ]]; then
    warn "Vault exists and is not empty - leaving it as is"
else
    mkdir -p "$VAULT"
    cp -R "$PLUGIN/content/starter-vault/." "$VAULT/"
    info "Starter vault copied: $(find "$VAULT" -name '*.md' | wc -l | tr -d ' ') notes"
fi

# --- 5. config ---
mkdir -p "$HOME/.claude"
printf '{\n  "vault_path": "%s",\n  "version": "%s"\n}\n' "$VAULT" \
    "$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$PLUGIN/.claude-plugin/plugin.json")" > "$HOME/.claude/brain-config.json"
info "Wrote ~/.claude/brain-config.json"

# --- 6. CLAUDE.md ---
section "Framework rules -> $CLAUDE_MD"
if grep -q "BRAIN-FRAMEWORK-START" "$CLAUDE_MD" 2>/dev/null; then
    info "Already merged - skipping"
else
    [[ -s "$CLAUDE_MD" ]] && printf '\n' >> "$CLAUDE_MD"
    cat "$PLUGIN/templates/claude-md-additions.md" >> "$CLAUDE_MD"
    info "Merged (wrapped in BRAIN-FRAMEWORK markers, remove that block to undo)"
fi

# --- done ---
section "Done"
for t in yt-dlp ffmpeg whisper graphify; do
    command -v "$t" >/dev/null 2>&1 && printf "  ${GREEN}OK${RESET}   %s\n" "$t" || printf "  ${RED}MISS${RESET} %s\n" "$t"
done
cat <<NEXT

Next:
  1. Open Obsidian -> "Open folder as vault" -> $VAULT
  2. Run: claude
  3. Paste a YouTube URL, or type: /yt-capture <url>
  4. Weekly: /brain-doctor

NEXT

#!/usr/bin/env bash
# install-deps.sh - Install YouTube ingestion tooling required by the brain plugin.
#
# Installs (with explicit confirmation per tool):
#   - yt-dlp     YouTube downloader + auto-caption fetcher
#   - ffmpeg     audio/video processing (whisper dependency)
#   - whisper    OpenAI Whisper for transcription when auto-captions unavailable
#   - graphify   Semantic graph builder for the Obsidian vault
#
# Run by /brain-init on first install. Idempotent - re-running is safe.

set -uo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

info()    { printf "${GREEN}-> %s${RESET}\n" "$*"; }
warn()    { printf "${YELLOW}!! %s${RESET}\n" "$*"; }
err()     { printf "${RED}xx %s${RESET}\n" "$*" >&2; }
section() { printf "\n${GREEN}== %s ==${RESET}\n" "$*"; }

confirm() {
    local prompt="$1"
    local response
    if [[ "${BRAIN_AUTO_YES:-0}" == "1" ]]; then
        return 0
    fi
    read -r -p "${prompt} [Y/n] " response
    response="${response:-Y}"
    [[ "${response}" =~ ^[Yy] ]]
}

detect_platform() {
    case "$(uname -s)" in
        Darwin) echo "mac" ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            elif command -v apt-get >/dev/null 2>&1; then
                echo "linux-apt"
            elif command -v dnf >/dev/null 2>&1; then
                echo "linux-dnf"
            elif command -v yum >/dev/null 2>&1; then
                echo "linux-yum"
            else
                echo "linux-unknown"
            fi
            ;;
        *) echo "unknown" ;;
    esac
}

PLATFORM=$(detect_platform)
info "Detected platform: ${PLATFORM}"

install_pkg() {
    local pkg="$1"
    case "${PLATFORM}" in
        mac)         brew install "${pkg}" ;;
        linux-apt|wsl) sudo apt-get install -y "${pkg}" ;;
        linux-dnf)   sudo dnf install -y "${pkg}" ;;
        linux-yum)   sudo yum install -y "${pkg}" ;;
        *)           err "Unsupported platform for ${pkg}. Install manually."; return 1 ;;
    esac
}

# --- yt-dlp ---
section "yt-dlp"
if command -v yt-dlp >/dev/null 2>&1; then
    info "yt-dlp already installed: $(yt-dlp --version 2>&1 | head -1)"
else
    if confirm "Install yt-dlp (YouTube downloader)?"; then
        install_pkg yt-dlp || pip3 install --user yt-dlp
        command -v yt-dlp >/dev/null 2>&1 && info "yt-dlp OK" || err "yt-dlp install failed"
    else
        warn "Skipped yt-dlp - YouTube ingestion will not work without it."
    fi
fi

# --- ffmpeg ---
section "ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
    info "ffmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
else
    if confirm "Install ffmpeg (whisper audio dependency)?"; then
        install_pkg ffmpeg
        command -v ffmpeg >/dev/null 2>&1 && info "ffmpeg OK" || err "ffmpeg install failed"
    else
        warn "Skipped ffmpeg - whisper transcription will not work."
    fi
fi

# --- whisper ---
section "whisper (openai-whisper)"
if command -v whisper >/dev/null 2>&1; then
    info "whisper already installed: $(whisper --help 2>&1 | head -1)"
else
    if confirm "Install openai-whisper via pip (large download, ~2GB models)?"; then
        if command -v pip3 >/dev/null 2>&1; then
            pip3 install --user openai-whisper
        elif command -v pip >/dev/null 2>&1; then
            pip install --user openai-whisper
        else
            err "pip not found. Install Python 3 first."
        fi
        command -v whisper >/dev/null 2>&1 && info "whisper OK" || warn "whisper not in PATH after install - ensure ~/.local/bin is in PATH"
    else
        warn "Skipped whisper - videos without auto-captions cannot be transcribed."
    fi
fi

# --- graphify ---
section "graphify (semantic graph builder)"
if command -v graphify >/dev/null 2>&1; then
    info "graphify already installed: $(graphify --version 2>&1 | head -1)"
else
    if confirm "Install graphify via uv (semantic graph builder for the vault)?"; then
        if ! command -v uv >/dev/null 2>&1; then
            warn "uv not installed. Installing uv first..."
            if [[ "${PLATFORM}" == "mac" ]]; then
                brew install uv
            else
                curl -LsSf https://astral.sh/uv/install.sh | sh
            fi
        fi
        uv tool install graphifyy
        command -v graphify >/dev/null 2>&1 && info "graphify OK" || warn "graphify not in PATH after install"
    else
        warn "Skipped graphify - semantic graph features will not work."
    fi
fi

# --- Obsidian (GUI app, optional) ---
section "Obsidian (optional - the vault GUI)"

obsidian_installed() {
    case "${PLATFORM}" in
        mac) [[ -d "/Applications/Obsidian.app" ]] || ls "$HOME/Applications/Obsidian.app" >/dev/null 2>&1 ;;
        linux-apt|linux-dnf|linux-yum) command -v obsidian >/dev/null 2>&1 || [[ -f "$HOME/.local/bin/Obsidian.AppImage" ]] ;;
        wsl) return 1 ;;  # always tell WSL users to install on Windows side
        *) return 1 ;;
    esac
}

if obsidian_installed; then
    info "Obsidian already installed."
else
    if confirm "Install Obsidian (GUI for browsing the vault and seeing the knowledge graph)?"; then
        case "${PLATFORM}" in
            mac)
                brew install --cask obsidian \
                    && info "Obsidian installed at /Applications/Obsidian.app" \
                    || warn "Obsidian install failed - get it manually from https://obsidian.md"
                ;;
            linux-apt|linux-dnf|linux-yum)
                warn "On Linux, Obsidian ships as an AppImage. Download from https://obsidian.md/download"
                warn "Or install via snap: sudo snap install obsidian --classic"
                warn "Or flatpak: flatpak install flathub md.obsidian.Obsidian"
                ;;
            wsl)
                warn "On WSL, install Obsidian on the Windows side (not WSL): https://obsidian.md/download"
                warn "Then open it and point to the vault via /mnt/c/... path or copy the vault to a Windows location."
                ;;
            *)
                warn "Unsupported platform for automatic Obsidian install. Get it from https://obsidian.md"
                ;;
        esac
    else
        warn "Skipped Obsidian. Vault still works as plain markdown - open in any editor (VS Code, Foam, etc.)."
    fi
fi

section "Summary"
for tool in yt-dlp ffmpeg whisper graphify; do
    if command -v "${tool}" >/dev/null 2>&1; then
        printf "  ${GREEN}OK${RESET}   %s\n" "${tool}"
    else
        printf "  ${RED}MISS${RESET} %s\n" "${tool}"
    fi
done
if obsidian_installed; then
    printf "  ${GREEN}OK${RESET}   obsidian\n"
else
    printf "  ${YELLOW}--${RESET}   obsidian (optional)\n"
fi
echo
info "Done. Run /brain-init to set up your vault."
echo
info "After /brain-init: open Obsidian, click 'Open folder as vault', and pick your vault location."

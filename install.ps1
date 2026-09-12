# install.ps1 - one-shot brain install for native Windows. No /brain-init needed afterwards.
#
#   Right-click -> "Run with PowerShell", or:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   or without cloning:
#   irm https://raw.githubusercontent.com/peleg-jpg/brain/main/install.ps1 | iex
#
# Does everything in one go, no prompts:
#   1. winget: git, yt-dlp, ffmpeg, uv, Obsidian. uv: python3, whisper, graphify
#   2. brain plugin + claude-mem plugin into Claude Code (all 10 skills + hooks)
#   3. graphify skill registered with Claude Code
#   4. Vault at ~\obsidian-brain with the 146-note starter content
#   5. ~\.claude\brain-config.json
#   6. Framework rules merged into ~\.claude\CLAUDE.md
# Idempotent - re-running is safe. Override vault path: $env:BRAIN_VAULT = "D:\vault"

$ErrorActionPreference = "Continue"
function Info($m)    { Write-Host "-> $m" -ForegroundColor Green }
function Warn($m)    { Write-Host "!! $m" -ForegroundColor Yellow }
function Err($m)     { Write-Host "xx $m" -ForegroundColor Red }
function Section($m) { Write-Host "`n== $m ==" -ForegroundColor Green }
function Has($cmd)   { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function RefreshPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                "$env:USERPROFILE\.local\bin"
}
function WingetInstall($id, $cmd) {
    if ($cmd -and (Has $cmd)) { Info "$cmd already installed"; return }
    Info "Installing $id via winget"
    winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements | Out-Null
    RefreshPath
}

$RepoUrl = "https://github.com/peleg-jpg/brain"
$Src = $PSScriptRoot
if (-not $Src -or -not (Test-Path "$Src\plugins\brain")) {
    # irm | iex - no local clone, fetch one
    $Src = "$env:USERPROFILE\.brain-src"
    Section "Fetching brain source -> $Src"
    if (-not (Has git)) { WingetInstall "Git.Git" "git" }
    if (Test-Path "$Src\.git") { git -C $Src pull -q } else { git clone -q --depth 1 $RepoUrl $Src }
}
$Plugin   = "$Src\plugins\brain"
$Vault    = if ($env:BRAIN_VAULT) { $env:BRAIN_VAULT } else { "$env:USERPROFILE\obsidian-brain" }
$ClaudeMd = "$env:USERPROFILE\.claude\CLAUDE.md"
RefreshPath

# --- 0. preflight ---
Section "Preflight"
if (-not (Has claude)) {
    Err "Claude Code CLI not found. Install it first in PowerShell:  irm https://claude.ai/install.ps1 | iex"
    exit 1
}
Info "claude: $(claude --version 2>$null | Select-Object -First 1)"
if (-not (Has winget)) {
    Err "winget not found. Update 'App Installer' from the Microsoft Store, then re-run."
    exit 1
}

# --- 1. tooling ---
Section "Tooling (git, yt-dlp, ffmpeg, uv, Obsidian, python3, whisper, graphify)"
WingetInstall "Git.Git"           "git"       # Claude Code hooks run through Git Bash
WingetInstall "yt-dlp.yt-dlp"     "yt-dlp"
WingetInstall "Gyan.FFmpeg"       "ffmpeg"
WingetInstall "astral-sh.uv"      "uv"
if (Test-Path "$env:LOCALAPPDATA\Obsidian\Obsidian.exe") { Info "Obsidian already installed" } else { WingetInstall "Obsidian.Obsidian" $null }
if (-not (Has python3)) {
    # uv-managed python ships python3.exe, which the plugin hooks call
    Info "Installing python3 via uv"
    uv python install --default | Out-Null
    RefreshPath
}
if (Has whisper)  { Info "whisper already installed" }  else { uv tool install openai-whisper | Out-Null; RefreshPath }
if (Has graphify) { Info "graphify already installed" } else { uv tool install graphifyy | Out-Null; RefreshPath }

# --- 2. Claude Code plugins ---
Section "Claude Code plugins"
function InstallPlugin($name) {
    # --yes for new CLIs, plain for old ones
    $out = claude plugin install $name --yes 2>&1
    if ($LASTEXITCODE -ne 0) { $out = claude plugin install $name 2>&1 }
    return ($LASTEXITCODE -eq 0)
}
claude plugin marketplace add peleg-jpg/brain 2>&1 | Out-Null
if (InstallPlugin "brain@brain") { Info "brain plugin OK (10 skills + 4 hooks)" } else { Err "brain plugin install failed" }
claude plugin marketplace add thedotmack/claude-mem 2>&1 | Out-Null
if (InstallPlugin "claude-mem@thedotmack") { Info "claude-mem plugin OK" } else { Warn "claude-mem install failed - install later with: claude plugin install claude-mem@thedotmack" }

# --- 3. graphify skill ---
if (Has graphify) {
    graphify install --platform claude 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Info "graphify skill registered" } else { Warn "graphify install --platform claude failed" }
}

# --- 4. vault ---
Section "Vault -> $Vault"
if ((Test-Path $Vault) -and (Get-ChildItem $Vault -Force | Select-Object -First 1)) {
    Warn "Vault exists and is not empty - leaving it as is"
} else {
    New-Item -ItemType Directory -Force -Path $Vault | Out-Null
    Copy-Item -Path "$Plugin\content\starter-vault\*" -Destination $Vault -Recurse -Force
    $n = (Get-ChildItem $Vault -Recurse -Filter *.md | Measure-Object).Count
    Info "Starter vault copied: $n notes"
}

# --- 5. config ---
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude" | Out-Null
$ver = (Get-Content "$Plugin\.claude-plugin\plugin.json" -Raw | ConvertFrom-Json).version
@{ vault_path = ($Vault -replace '\\', '/'); version = $ver } | ConvertTo-Json | Set-Content "$env:USERPROFILE\.claude\brain-config.json" -Encoding UTF8
Info "Wrote ~\.claude\brain-config.json"

# --- 6. CLAUDE.md ---
Section "Framework rules -> $ClaudeMd"
if ((Test-Path $ClaudeMd) -and (Select-String -Path $ClaudeMd -Pattern "BRAIN-FRAMEWORK-START" -Quiet)) {
    Info "Already merged - skipping"
} else {
    if ((Test-Path $ClaudeMd) -and (Get-Item $ClaudeMd).Length -gt 0) { Add-Content $ClaudeMd "" -Encoding UTF8 }
    Get-Content "$Plugin\templates\claude-md-additions.md" -Raw | Add-Content $ClaudeMd -Encoding UTF8
    Info "Merged (wrapped in BRAIN-FRAMEWORK markers, remove that block to undo)"
}

# --- done ---
Section "Done"
foreach ($t in "yt-dlp", "ffmpeg", "whisper", "graphify", "python3") {
    if (Has $t) { Write-Host "  OK   $t" -ForegroundColor Green } else { Write-Host "  MISS $t" -ForegroundColor Red }
}
Write-Host @"

Next:
  1. Close and reopen your terminal so PATH changes apply
  2. Open Obsidian -> "Open folder as vault" -> $Vault
  3. Run: claude
  4. Paste a YouTube URL, or type: /yt-capture <url>
  5. Weekly: /brain-doctor

"@

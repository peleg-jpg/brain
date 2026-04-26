#!/usr/bin/env python3
"""Fetch a YouTube video's transcript + metadata and save it as a markdown note
into a brain vault's raw/ staging folder.

Usage:
  yt-to-raw.py <URL> [vault-path]

Default vault: ~/obsidian-brain. Auto-detects raw/ vs _raw/ convention.

Requires yt-dlp in PATH (run install-deps.sh first).
If auto-captions are unavailable, falls back to whisper transcription.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")[:80]


def detect_raw_folder(vault: Path) -> Path:
    if (vault / "raw").is_dir():
        return vault / "raw"
    if (vault / "_raw").is_dir():
        return vault / "_raw"
    raise SystemExit(f"ERROR: no raw/ or _raw/ folder in {vault}. Run /brain-init first.")


def fetch_metadata(url: str) -> dict:
    result = subprocess.run(
        [
            "yt-dlp",
            "--print",
            "%(title)s|||%(uploader)s|||%(duration)s|||%(upload_date)s|||%(id)s",
            "--skip-download",
            url,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    parts = result.stdout.strip().split("|||")
    return {
        "title": parts[0],
        "uploader": parts[1],
        "duration": parts[2],
        "upload_date": parts[3],
        "id": parts[4],
    }


def fetch_auto_captions(url: str, staging: Path, video_id: str) -> Path | None:
    subprocess.run(
        [
            "yt-dlp",
            "--write-auto-sub",
            "--skip-download",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            url,
            "-o", str(staging / f"{video_id}.%(ext)s"),
        ],
        check=True,
        capture_output=True,
    )
    vtt = staging / f"{video_id}.en.vtt"
    return vtt if vtt.exists() else None


def fetch_audio_for_whisper(url: str, staging: Path, video_id: str) -> Path:
    audio_path = staging / f"{video_id}.m4a"
    subprocess.run(
        [
            "yt-dlp",
            "-x", "--audio-format", "m4a",
            url,
            "-o", str(staging / f"{video_id}.%(ext)s"),
        ],
        check=True,
        capture_output=True,
    )
    return audio_path


def transcribe_with_whisper(audio_path: Path) -> str:
    result = subprocess.run(
        [
            "whisper", str(audio_path),
            "--model", "small",
            "--output_format", "txt",
            "--output_dir", str(audio_path.parent),
            "--language", "en",
            "--verbose", "False",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    txt_path = audio_path.with_suffix(".txt")
    if not txt_path.exists():
        raise SystemExit("ERROR: whisper produced no output")
    text = txt_path.read_text(encoding="utf-8")
    txt_path.unlink()
    audio_path.unlink()
    return text.strip()


def clean_vtt(vtt_path: Path) -> str:
    text = vtt_path.read_text(encoding="utf-8")
    out: list[str] = []
    for line in text.splitlines():
        if "-->" in line:
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if not line.strip():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"&[a-z]+;", "", line)
        out.append(line.strip())
    dedup: list[str] = []
    for l in out:
        if not dedup or dedup[-1] != l:
            dedup.append(l)
    return "\n".join(dedup)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "vault",
        nargs="?",
        default=str(Path.home() / "obsidian-brain"),
        help="Path to brain vault (default: ~/obsidian-brain)",
    )
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        raise SystemExit(f"ERROR: vault not found: {vault}. Run /brain-init first.")

    raw_dir = detect_raw_folder(vault)

    print(f"-> Fetching metadata for {args.url}", file=sys.stderr)
    meta = fetch_metadata(args.url)

    upload = meta["upload_date"]
    if upload and len(upload) == 8:
        upload_human = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}"
    else:
        upload_human = upload or "unknown"

    duration_raw = meta["duration"]
    try:
        minutes = int(duration_raw) // 60
        duration_human = f"{minutes} min"
    except (TypeError, ValueError):
        duration_human = duration_raw or "unknown"

    print(f"-> Title: {meta['title']}", file=sys.stderr)
    print(f"-> Trying auto-captions first", file=sys.stderr)

    vtt = fetch_auto_captions(args.url, raw_dir, meta["id"])
    if vtt:
        transcript = clean_vtt(vtt)
        vtt.unlink()
        source_method = "yt-dlp auto-captions"
    else:
        print(f"-> No auto-captions, falling back to whisper", file=sys.stderr)
        if not subprocess.run(["which", "whisper"], capture_output=True).returncode == 0:
            raise SystemExit("ERROR: no captions and whisper not installed. Run install-deps.sh.")
        audio = fetch_audio_for_whisper(args.url, raw_dir, meta["id"])
        transcript = transcribe_with_whisper(audio)
        source_method = "whisper transcription"

    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(meta["title"])
    note_path = raw_dir / f"yt-{today}-{slug}.md"

    body = (
        f"# {meta['title']}\n\n"
        f"**Source:** YouTube\n"
        f"**URL:** {args.url}\n"
        f"**Channel:** {meta['uploader']}\n"
        f"**Uploaded:** {upload_human}\n"
        f"**Duration:** {duration_human}\n"
        f"**Captured:** {today}\n"
        f"**Transcribed via:** {source_method}\n\n"
        f"---\n\n"
        f"## Transcript\n\n"
        f"{transcript}\n"
    )
    note_path.write_text(body, encoding="utf-8")

    print(f"{note_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

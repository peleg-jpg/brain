#!/usr/bin/env python3
"""strip_transcripts.py - evict embedded <details> transcript blocks from vault notes.

Keeps everything outside the block (the curated note IS what stays), moves the
transcript body to the archive mirror, and leaves a one-line pointer. Reversible:
nothing is deleted, only relocated.

Usage:
  strip_transcripts.py <vault_root> <subdir> <archive_root> [--apply]

Default is dry-run: prints what would change, writes nothing.
"""
import re
import sys
from pathlib import Path

BLOCK_RE = re.compile(
    r"<details>\s*<summary>[^<]*transcript[^<]*</summary>(.*?)</details>\n?",
    re.IGNORECASE | re.DOTALL,
)


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    vault_root = Path(sys.argv[1]).expanduser()
    subdir = sys.argv[2]
    archive_root = Path(sys.argv[3]).expanduser()
    apply = "--apply" in sys.argv

    changed = 0
    saved_bytes = 0
    for note in sorted((vault_root / subdir).rglob("*.md")):
        text = note.read_text(encoding="utf-8", errors="ignore")
        m = BLOCK_RE.search(text)
        if not m:
            continue
        rel = note.relative_to(vault_root)
        arc_path = archive_root / rel
        transcript = m.group(0)
        pointer = f"_Transcript archived: {arc_path}_\n"
        new_text = text[: m.start()] + pointer + text[m.end():]
        changed += 1
        saved_bytes += len(transcript) - len(pointer)
        if apply:
            arc_path.parent.mkdir(parents=True, exist_ok=True)
            arc_path.write_text(transcript, encoding="utf-8")
            note.write_text(new_text, encoding="utf-8")
        else:
            print(f"DRY {rel}: strip {len(transcript)//1024}KB, keep {len(new_text)//1024}KB")

    mode = "APPLIED" if apply else "DRY-RUN"
    print(f"\n{mode}: {changed} notes, {saved_bytes // 1024} KB evicted -> {archive_root}")


if __name__ == "__main__":
    main()

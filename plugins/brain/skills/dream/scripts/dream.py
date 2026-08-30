#!/usr/bin/env python3
"""dream - deterministic Claude Code auto-memory consolidator (v1, cut-to-3 core).

Operates ONLY on a single auto-memory directory (the one holding MEMORY.md +
topic *.md files). It does NOT read session transcripts, does NOT touch
claude-mem / Obsidian / CLAUDE.md, and uses NO LLM judgment. Every operation is
mechanical and lossless: content is moved, never silently dropped.

Subcommands
  audit   <memory-dir>            read-only integrity + budget report
  rebuild <memory-dir> [--apply]  prune + rebuild MEMORY.md; DRY-RUN unless --apply

Deterministic operations (rebuild)
  1. strip a stale harness "# Environment" system-preamble trailer (the known bug)
  2. em-dash / en-dash -> hyphen sweep (no em/en dashes rule)
  3. merge split "X" + "X (cont)" sections
  4. re-index orphan files (on disk, missing from the index) under "## Unsorted"
  5. drop ghost links (index entry -> a file that no longer exists)
  6. collapse decorative blank-line padding
  7. budget enforcer: if still over 200 lines OR 25000 bytes, demote the largest
     inline-prose sections into their own topic files (lossless) until under budget

Safety
  - tarball snapshot to ~/.claude/.dream-snapshots/ (OUTSIDE the target dir) is the
    first action on --apply; restore command is printed
  - dry-run is the default; writes require --apply
  - mtime-recheck-abort: re-stat every source file before writing; abort if anything
    changed since the snapshot (guards against a parallel session clobber)
  - new files written first, MEMORY.md replaced last via atomic os.replace
  - idempotent: a second rebuild on a clean dir is a byte-identical no-op
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

LINE_LIMIT = 200
BYTE_LIMIT = 25000
LONG_LINE = 200            # soft: flag index lines longer than this
DEMOTE_MIN_LINES = 6       # only demote inline-prose sections at least this tall
EMDASH = "—"          # ---
ENDASH = "–"          # --

LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")
SECTION_RE = re.compile(r"^##\s+(.*)$")
ENV_MARKER = "invoked in the following environment"


# ----------------------------------------------------------------------------- helpers
def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower())
    s = re.sub(r"[\s-]+", "_", s).strip("_")
    return s[:60] or "section"


def sweep_dashes(text: str) -> str:
    return (
        text.replace(f" {EMDASH} ", " - ")
        .replace(f" {ENDASH} ", " - ")
        .replace(EMDASH, "-")
        .replace(ENDASH, "-")
    )


def clean_desc(s: str, limit: int = 110) -> str:
    """One-line pointer description: strip markdown noise, truncate on a word
    boundary, never leave a dangling backtick."""
    s = re.sub(r"[\[\]]", "", s).strip()
    if len(s) > limit:
        cut = s[:limit]
        sp = cut.rfind(" ")
        s = (cut[:sp] if sp > 40 else cut).rstrip(" -,:;")
    if s.count("`") % 2 == 1:
        s = s.rsplit("`", 1)[0].rstrip(" -,:;")
    return s


def read_frontmatter(path: Path) -> dict:
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not txt.startswith("---"):
        return {}
    end = txt.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in txt[3:end].splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def local_md_targets(text: str) -> set[str]:
    """Pure-filename (no slash) *.md targets referenced as markdown links."""
    out = set()
    for t in LINK_RE.findall(text):
        if "/" not in t and not t.startswith("http"):
            out.add(t)
    return out


def trim_blanks(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if ln.strip() == "":
            if out and out[-1].strip() == "":
                continue
            out.append("")
        else:
            out.append(ln)
    while out and out[0].strip() == "":
        out.pop(0)
    while out and out[-1].strip() == "":
        out.pop()
    return out


# ----------------------------------------------------------------------------- model
class Index:
    def __init__(self, preamble: list[str], sections: list[list]):
        self.preamble = preamble                 # list[str]
        self.sections = sections                 # list[[title, content_lines]]

    @classmethod
    def parse(cls, text: str) -> "Index":
        preamble: list[str] = []
        sections: list[list] = []
        cur = None
        for ln in text.splitlines():
            m = SECTION_RE.match(ln)
            if m:
                cur = [m.group(1).strip(), []]
                sections.append(cur)
            elif cur is None:
                preamble.append(ln)
            else:
                cur[1].append(ln)
        return cls(preamble, sections)

    def render(self) -> str:
        parts = list(trim_blanks(self.preamble))
        for title, content in self.sections:
            parts.append("")
            parts.append("## " + title)
            parts.extend(trim_blanks(content))
        return "\n".join(parts).rstrip("\n") + "\n"

    def lines(self) -> int:
        return self.render().count("\n")

    def nbytes(self) -> int:
        return len(self.render().encode("utf-8"))


def section_pointer_count(content: list[str]) -> int:
    return sum(1 for ln in content if local_md_targets(ln))


# ----------------------------------------------------------------------------- env trailer
def strip_env_trailer(text: str):
    """Remove an appended harness '# Environment' system-preamble block. Returns
    (clean_text, removed_block_or_None)."""
    idx = text.find(ENV_MARKER)
    if idx == -1:
        return text, None
    head = text[:idx]
    cut = head.rfind("\n# Environment")
    if cut == -1:
        cut = head.rfind("# Environment")
    if cut == -1:
        cut = head.rfind("\n")  # fall back: cut at start of the marker's line
    removed = text[cut:].strip("\n")
    return text[:cut].rstrip("\n") + "\n", removed


# ----------------------------------------------------------------------------- analysis
def analyze(memory_dir: Path) -> dict:
    mem = memory_dir / "MEMORY.md"
    raw = mem.read_text(encoding="utf-8")
    clean, env_block = strip_env_trailer(raw)

    disk = sorted(
        p.name for p in memory_dir.glob("*.md")
        if p.name != "MEMORY.md"
    )
    referenced = local_md_targets(clean)
    orphans = sorted(set(disk) - referenced)
    ghosts = sorted(t for t in referenced if not (memory_dir / t).exists())

    idx = Index.parse(clean)
    cont_sections = [t for t, _ in idx.sections if re.search(r"\(cont\)\s*$", t)]
    long_lines = [
        ln for ln in clean.splitlines() if len(ln) > LONG_LINE
    ]
    emdashes = raw.count(EMDASH) + raw.count(ENDASH)

    return {
        "memory_dir": str(memory_dir),
        "raw_lines": raw.count("\n"),
        "raw_bytes": len(raw.encode("utf-8")),
        "clean_lines": clean.count("\n"),
        "clean_bytes": len(clean.encode("utf-8")),
        "line_limit": LINE_LIMIT,
        "byte_limit": BYTE_LIMIT,
        "over_line_limit": raw.count("\n") > LINE_LIMIT,
        "over_byte_limit": len(raw.encode("utf-8")) > BYTE_LIMIT,
        "env_trailer_present": env_block is not None,
        "env_trailer_preview": (env_block.splitlines()[0] if env_block else None),
        "emdash_count": emdashes,
        "disk_file_count": len(disk),
        "orphans": orphans,
        "ghost_links": ghosts,
        "cont_sections": cont_sections,
        "section_count": len(idx.sections),
        "long_line_count": len(long_lines),
    }


# ----------------------------------------------------------------------------- rebuild
def build_new_index(memory_dir: Path):
    """Returns (new_index_text, new_files: dict[name->text], report: dict)."""
    mem = memory_dir / "MEMORY.md"
    raw = mem.read_text(encoding="utf-8")
    report = {"actions": []}

    # 1. strip env trailer
    clean, env_block = strip_env_trailer(raw)
    if env_block:
        report["actions"].append(f"stripped stale '# Environment' trailer ({env_block.count(chr(10)) + 1} lines)")

    # 2. em-dash sweep
    before_dash = clean.count(EMDASH) + clean.count(ENDASH)
    clean = sweep_dashes(clean)
    if before_dash:
        report["actions"].append(f"swept {before_dash} em/en-dash -> hyphen")

    idx = Index.parse(clean)
    for sec in idx.sections:
        sec[0] = sweep_dashes(sec[0])
        sec[1] = [sweep_dashes(ln) for ln in sec[1]]
    idx.preamble = [sweep_dashes(ln) for ln in idx.preamble]

    # 3. merge "X (cont)" into "X"
    merged = []
    by_title = {}
    for title, content in idx.sections:
        base = re.sub(r"\s*\(cont\)\s*$", "", title)
        if base != title and base in by_title:
            by_title[base][1].extend([""] + content)
            report["actions"].append(f"merged '{title}' into '{base}'")
        else:
            sec = [title, content]
            by_title[title] = sec
            merged.append(sec)
    idx.sections = merged

    # 5. drop ghost links (before orphan/budget so counts are real)
    ghosts = []
    for _, content in idx.sections:
        kept = []
        for ln in content:
            tgts = local_md_targets(ln)
            missing = [t for t in tgts if not (memory_dir / t).exists()]
            if missing and tgts and all(not (memory_dir / t).exists() for t in tgts):
                ghosts.extend(missing)
                continue
            kept.append(ln)
        content[:] = kept
    if ghosts:
        report["actions"].append(f"dropped {len(ghosts)} ghost link(s): {', '.join(ghosts)}")
    report["ghost_links"] = ghosts

    # 4. re-index orphans under "## Unsorted (re-indexed by dream)"
    disk = sorted(p.name for p in memory_dir.glob("*.md") if p.name != "MEMORY.md")
    referenced = local_md_targets(idx.render())
    orphans = sorted(set(disk) - referenced)
    if orphans:
        bullets = []
        for f in orphans:
            fm = read_frontmatter(memory_dir / f)
            title = fm.get("name", Path(f).stem)
            desc = fm.get("description", "(re-indexed by dream; add a description)")
            bullets.append(f"- [{title}]({f}) - {desc}")
        idx.sections.append(["Unsorted (re-indexed by dream)", bullets])
        report["actions"].append(f"re-indexed {len(orphans)} orphan(s): {', '.join(orphans)}")
    report["orphans"] = orphans

    # 7. budget enforcer via lossless demotion of inline-prose sections
    new_files: dict[str, str] = {}
    demoted = []
    existing = set(disk) | {"MEMORY.md"}

    def over_budget() -> bool:
        return idx.lines() > LINE_LIMIT or idx.nbytes() > BYTE_LIMIT

    if over_budget():
        candidates = []
        for sec in idx.sections:
            title, content = sec
            if section_pointer_count(content) == 0 and len(trim_blanks(content)) >= DEMOTE_MIN_LINES:
                candidates.append(sec)
        candidates.sort(key=lambda s: len(trim_blanks(s[1])), reverse=True)
        for sec in candidates:
            if not over_budget():
                break
            title, content = sec
            slug = slugify(title)
            fname = f"inline_{slug}.md"
            n = 2
            while fname in existing or fname in new_files:
                fname = f"inline_{slug}_{n}.md"
                n += 1
            existing.add(fname)
            body = "\n".join(trim_blanks(content))
            raw_first = next((ln.strip(" -*#") for ln in trim_blanks(content) if ln.strip()), title)
            first = clean_desc(raw_first)
            new_files[fname] = (
                f"---\nname: {Path(fname).stem}\n"
                f"description: {title} - {first}\n"
                f"metadata:\n  type: reference\n---\n\n# {title}\n\n{body}\n"
            )
            sec[1] = [f"- [{title}]({fname}) - {first}"]
            demoted.append((title, fname))
        if demoted:
            report["actions"].append(
                "demoted inline-prose section(s) to topic files: "
                + ", ".join(f"{t} -> {f}" for t, f in demoted)
            )
    report["demoted"] = [{"section": t, "file": f} for t, f in demoted]

    new_text = idx.render()
    report["final_lines"] = new_text.count("\n")
    report["final_bytes"] = len(new_text.encode("utf-8"))
    report["under_budget"] = new_text.count("\n") <= LINE_LIMIT and len(new_text.encode("utf-8")) <= BYTE_LIMIT
    report["new_files"] = list(new_files.keys())
    return new_text, new_files, report


# ----------------------------------------------------------------------------- io / safety
def snapshot(memory_dir: Path) -> Path:
    # snapshot OUTSIDE the target dir so a bad glob inside it can't destroy its own
    # rollback. Override with DREAM_SNAPSHOT_DIR (set per-environment in SKILL.md).
    base = os.environ.get("DREAM_SNAPSHOT_DIR")
    snap_dir = Path(base).expanduser() if base else Path.home() / ".dream-snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = snap_dir / f"{memory_dir.name}-{ts}.tgz"
    with tarfile.open(out, "w:gz") as tar:
        for p in sorted(memory_dir.glob("*.md")):
            tar.add(p, arcname=p.name)
    # keep last 10
    snaps = sorted(snap_dir.glob(f"{memory_dir.name}-*.tgz"))
    for old in snaps[:-10]:
        old.unlink()
    return out


def file_mtimes(memory_dir: Path) -> dict:
    return {p.name: p.stat().st_mtime_ns for p in memory_dir.glob("*.md")}


def atomic_write(path: Path, text: str):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".dreamtmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# ----------------------------------------------------------------------------- commands
def cmd_audit(memory_dir: Path, as_json: bool):
    a = analyze(memory_dir)
    if as_json:
        print(json.dumps(a, ensure_ascii=False, indent=2))
        return
    print(f"# dream audit - {a['memory_dir']}\n")
    flag = lambda b: "FAIL" if b else "ok"
    print(f"index size        : {a['raw_lines']} lines / {a['raw_bytes']} bytes")
    print(f"  line budget (<{LINE_LIMIT}) : {flag(a['over_line_limit'])}")
    print(f"  byte budget (<{BYTE_LIMIT}): {flag(a['over_byte_limit'])}")
    print(f"  after cleanup est : {a['clean_lines']} lines / {a['clean_bytes']} bytes (env trailer removed)")
    print(f"env trailer (bug) : {'PRESENT - ' + str(a['env_trailer_preview']) if a['env_trailer_present'] else 'none'}")
    print(f"em/en-dashes      : {a['emdash_count']} (no em/en dashes rule)")
    print(f"sections          : {a['section_count']}")
    print(f"topic files       : {a['disk_file_count']}")
    print(f"orphans (dark)    : {len(a['orphans'])}  {a['orphans']}")
    print(f"ghost links       : {len(a['ghost_links'])}  {a['ghost_links']}")
    print(f"split (cont) secs : {a['cont_sections']}")
    print(f"over-long lines   : {a['long_line_count']} (> {LONG_LINE} chars)")


def cmd_rebuild(memory_dir: Path, apply: bool):
    mem = memory_dir / "MEMORY.md"
    old = mem.read_text(encoding="utf-8")
    pre_mtimes = file_mtimes(memory_dir)
    new_text, new_files, report = build_new_index(memory_dir)

    print(f"# dream rebuild {'(APPLY)' if apply else '(DRY-RUN)'} - {memory_dir}\n")
    for act in report["actions"]:
        print(f"  - {act}")
    print(f"\nindex: {old.count(chr(10))} -> {report['final_lines']} lines, "
          f"{len(old.encode('utf-8'))} -> {report['final_bytes']} bytes "
          f"(budget {LINE_LIMIT} lines / {BYTE_LIMIT} bytes: "
          f"{'OK' if report['under_budget'] else 'STILL OVER - LLM consolidation needed'})")
    if report["new_files"]:
        print(f"new topic files: {report['new_files']}")

    if not apply:
        print("\n--- MEMORY.md unified diff (first 120 lines) ---")
        diff = list(difflib.unified_diff(
            old.splitlines(), new_text.splitlines(),
            fromfile="MEMORY.md (current)", tofile="MEMORY.md (after dream)", lineterm=""))
        for ln in diff[:120]:
            print(ln)
        if len(diff) > 120:
            print(f"... (+{len(diff) - 120} more diff lines)")
        print("\nDRY-RUN: nothing written. Re-run with --apply (or say 'go') to commit.")
        return

    # APPLY path
    snap = snapshot(memory_dir)
    print(f"\nsnapshot: {snap}")
    print(f"restore : tar xzf {snap} -C {memory_dir}")

    if file_mtimes(memory_dir) != pre_mtimes:
        sys.exit("ABORT: a file changed under dream since the snapshot (parallel session?). "
                 "Nothing written beyond the snapshot. Re-run.")

    for name, text in new_files.items():
        atomic_write(memory_dir / name, text)
    atomic_write(mem, new_text)
    print(f"\nwrote {len(new_files)} new file(s) + MEMORY.md. "
          f"Final: {report['final_lines']} lines / {report['final_bytes']} bytes.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit")
    a.add_argument("memory_dir")
    a.add_argument("--json", action="store_true")
    r = sub.add_parser("rebuild")
    r.add_argument("memory_dir")
    r.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    memory_dir = Path(args.memory_dir).expanduser().resolve()
    if not (memory_dir / "MEMORY.md").exists():
        sys.exit(f"ERROR: no MEMORY.md in {memory_dir}")

    if args.cmd == "audit":
        cmd_audit(memory_dir, args.json)
    elif args.cmd == "rebuild":
        cmd_rebuild(memory_dir, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())

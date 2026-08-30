#!/usr/bin/env python3
"""brain_scan.py - deterministic health scanner for the second brain.

Scans the Obsidian vault(s) + Claude Code auto-memory + claude-mem and prints a
JSON report to stdout (use --pretty for a human-readable summary instead).

Vault discovery, in order: $BRAIN_VAULT, ~/.claude/brain-config.json (vault_path),
--vault PATH (repeatable), else ~/obsidian-brain.

No third-party deps. Read-only: this script never modifies anything.
"""
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

HOME = Path.home()
NOW = time.time()
DAY = 86400

def _vault_roots():
    roots = []
    env = os.environ.get("BRAIN_VAULT")
    if env:
        roots.append(Path(env).expanduser())
    cfg = HOME / ".claude" / "brain-config.json"
    if cfg.exists():
        try:
            vp = json.loads(cfg.read_text(encoding="utf-8")).get("vault_path")
            if vp:
                roots.append(Path(vp).expanduser())
        except (OSError, ValueError):
            pass
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--vault" and i + 1 < len(args):
            roots.append(Path(args[i + 1]).expanduser())
    if not roots:
        roots.append(HOME / "obsidian-brain")
    out = []
    for r in roots:
        if r not in out:
            out.append(r)
    return out


def _vault_cfg(root: Path):
    index = "_vault-index.md" if (root / "_vault-index.md").exists() else "wiki/index.md"
    return {"root": root, "index": index, "raw_dirs": ["raw", "_raw", "transcripts"], "log": "_log.md"}


VAULTS = {r.name: _vault_cfg(r) for r in _vault_roots()}

SKIP_DIRS = {".obsidian", ".lint", ".git", ".tools", "graphify-out", "node_modules", ".trash"}
# machine-generated append-only folders: excluded from index-drift checks
INDEX_EXEMPT = {"whisper"}

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
# placeholder targets used as examples inside schema/template control files -
# not real broken links, so they should not inflate the count every run
PLACEHOLDER_TARGETS = {
    "note-name", "path/to/note", "links", "link", "wikilinks", "..",
    "note-a", "note-b", "their-name", "name",
}

unreadable_files = []


def md_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".md"):
                yield Path(dirpath) / f


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        unreadable_files.append(f"{path}: {e}")
        return None


def age_days(path: Path):
    try:
        return round((NOW - path.stat().st_mtime) / DAY, 1)
    except OSError:
        return None


def notes_stats(root: Path, notes):
    folders = {}
    recent_30d = 0
    newest_mtime = 0.0
    fm_count = 0
    transcript_notes = 0
    basenames = set()
    for n in notes:
        rel = n.relative_to(root)
        top = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        folders[top] = folders.get(top, 0) + 1
        mt = n.stat().st_mtime
        newest_mtime = max(newest_mtime, mt)
        if NOW - mt <= 30 * DAY:
            recent_30d += 1
        basenames.add(n.stem.lower())
        text = read_text(n)
        if text is None:
            continue
        if text.startswith("---"):
            fm_count += 1
        if "<details>" in text and "transcript" in text.lower():
            transcript_notes += 1
    return {
        "folders": dict(sorted(folders.items(), key=lambda kv: -kv[1])),
        "notes_modified_30d": recent_30d,
        "frontmatter_coverage": f"{fm_count}/{len(notes)}",
        "notes_with_embedded_transcripts": transcript_notes,
        "_newest_mtime": newest_mtime,
        "_basenames": basenames,
    }


def staging_backlog(root: Path, raw_dirs):
    backlog = []
    for rd in raw_dirs:
        rdir = root / rd
        if not rdir.exists():
            continue
        files = [f for f in rdir.rglob("*") if f.is_file() and f.name not in ("README.md", ".DS_Store")]
        if files:
            backlog.append({
                "dir": rd,
                "files": len(files),
                "oldest_days": max(age_days(f) or 0 for f in files),
                "size_kb": sum(f.stat().st_size for f in files) // 1024,
            })
    return backlog


def broken_links(root: Path, notes, basenames):
    found = {}
    for n in notes:
        text = read_text(n)
        if text is None:
            continue
        rel = str(n.relative_to(root))
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip()
            if not target or target.lower() in PLACEHOLDER_TARGETS:
                continue
            if target.endswith("/"):
                kind = "folder-link"  # Obsidian cannot resolve folder links
            elif Path(target).stem.lower() in basenames:
                continue
            else:
                kind = "missing"
            found.setdefault((rel, target), kind)
    return [{"file": f, "target": t, "kind": k} for (f, t), k in found.items()]


def index_drift(root: Path, index_rel, folders):
    idx_path = root / index_rel
    if not idx_path.exists():
        return {"index_missing_folders": [{"folder": "(index file missing)", "notes": 0}]}
    idx_text = (read_text(idx_path) or "").lower()
    drift = [
        {"folder": folder, "notes": count}
        for folder, count in folders.items()
        if count >= 3
        and folder != "(root)"
        and folder not in INDEX_EXEMPT
        and not folder.startswith(("_", "."))
        and folder.lower() not in idx_text
    ]
    return {"index_missing_folders": drift, "index_age_days": age_days(idx_path)}


def graph_state(root: Path, newest_note_mtime):
    gjson = root / "graphify-out" / "graph.json"
    if not gjson.exists():
        return {"graph_stale": None, "graph_age_days": None}
    graph_mtime = gjson.stat().st_mtime
    return {
        "graph_age_days": round((NOW - graph_mtime) / DAY, 1),
        "graph_stale_vs_notes_days": round((newest_note_mtime - graph_mtime) / DAY, 1),
        "graph_stale": newest_note_mtime - graph_mtime > 2 * DAY,
    }


def cruft(root: Path):
    hits = []
    for pat in ("**/.DS_Store", "**/Untitled.md"):
        for f in root.glob(pat):
            if f.is_file() and (f.name == ".DS_Store" or f.stat().st_size == 0):
                hits.append(str(f.relative_to(root)))
    return hits


def scan_vault(name, cfg):
    root = cfg["root"]
    if not root.exists():
        return {"name": name, "root": str(root), "error": "missing"}
    notes = list(md_files(root))
    stats = notes_stats(root, notes)
    links = broken_links(root, notes, stats.pop("_basenames"))
    newest = stats.pop("_newest_mtime")
    log = root / cfg["log"]
    return {
        "name": name,
        "root": str(root),
        "total_notes": len(notes),
        **stats,
        "staging_backlog": staging_backlog(root, cfg["raw_dirs"]),
        "broken_links": links,
        "broken_links_count": len(links),
        **index_drift(root, cfg["index"], stats["folders"]),
        **graph_state(root, newest),
        "log_age_days": age_days(log) if log.exists() else None,
        "cruft": cruft(root),
    }


def scan_memory():
    out = {}
    projects = HOME / ".claude" / "projects"
    over, topic_files, biggest = [], 0, 0
    for memory_md in projects.glob("*/memory/MEMORY.md"):
        lines = len((read_text(memory_md) or "").splitlines())
        biggest = max(biggest, lines)
        topic_files += max(len(list(memory_md.parent.glob("*.md"))) - 1, 0)
        if lines > 200:
            over.append({"project": memory_md.parent.parent.name, "lines": lines})
    out["memory_md_lines"] = biggest
    out["memory_md_over_budget"] = bool(over)
    out["memory_over_budget_projects"] = over
    out["topic_files"] = topic_files

    db = HOME / ".claude-mem/claude-mem.db"
    if db.exists():
        out["claude_mem_db_mb"] = db.stat().st_size // (1024 * 1024)
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        except sqlite3.Error as e:
            out["claude_mem_error"] = str(e)
            return out
        try:
            cur = con.cursor()
            for table in ("observations", "pending_messages"):
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 - fixed table names
                    out[table] = cur.fetchone()[0]
                except sqlite3.Error as e:
                    out[f"{table}_error"] = str(e)
        finally:
            con.close()
    return out


def print_pretty(report):
    for name, v in report["vaults"].items():
        print(f"\n== {name} ==")
        for k, val in v.items():
            if k == "broken_links":
                print(f"  {k}: {len(val)} (first 10)")
                for b in val[:10]:
                    print(f"    - {b['file']} -> [[{b['target']}]] ({b['kind']})")
            elif k != "folders":
                print(f"  {k}: {val}")
    print("\n== memory ==")
    for k, val in report["memory"].items():
        print(f"  {k}: {val}")
    if report["unreadable_files"]:
        print(f"\n!! unreadable files: {report['unreadable_files']}")


def main():
    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "vaults": {name: scan_vault(name, cfg) for name, cfg in VAULTS.items()},
        "memory": scan_memory(),
        "unreadable_files": unreadable_files,
    }
    if "--pretty" in sys.argv:
        print_pretty(report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

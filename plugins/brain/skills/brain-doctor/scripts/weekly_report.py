#!/usr/bin/env python3
"""weekly_report.py - format a brain_scan report into a short scorecard.

Reads brain_scan.py JSON on stdin, prints a compact human scorecard to stdout,
and exits 0 if healthy, 1 if any issue needs an interactive /brain-doctor run.
Pipe it into any notifier you like. Read-only: never edits anything.
"""
import json
import sys


def vault_issues(v):
    """Return a list of human-readable problems for one vault (empty = healthy)."""
    issues = []
    backlog = sum(b["files"] for b in v.get("staging_backlog", []))
    if backlog:
        issues.append(f"{backlog} files in staging backlog")
    if v.get("graph_stale"):
        issues.append(f"graph {v.get('graph_age_days')}d stale")
    if v.get("broken_links_count"):
        issues.append(f"{v['broken_links_count']} broken links")
    if v.get("index_missing_folders"):
        issues.append(f"{len(v['index_missing_folders'])} folders missing from index")
    if v.get("notes_with_embedded_transcripts"):
        issues.append(f"{v['notes_with_embedded_transcripts']} notes embed transcripts")
    return issues


def section(lines, header, issues):
    """Append a '<header>: OK/NEEDS FIX' line plus one indented line per issue."""
    lines.append(f"\n{header}: {'OK' if not issues else 'NEEDS FIX'}")
    lines.extend(f"  - {i}" for i in issues)
    return bool(issues)


def memory_issues(mem):
    issues = []
    if mem.get("memory_md_over_budget"):
        issues.append(f"MEMORY.md {mem['memory_md_lines']} lines (over 200)")
    if (mem.get("pending_messages") or 0) > 20000:
        issues.append(f"claude-mem queue {mem['pending_messages']}")
    return issues


def main():
    report = json.load(sys.stdin)
    lines = ["Brain Doctor weekly"]
    any_issue = False

    for v in report["vaults"].values():
        if v.get("error"):
            lines.append(f"\n{v['name']}: MISSING")
            any_issue = True
            continue
        header = f"{v['name']} ({v['total_notes']} notes)"
        any_issue |= section(lines, header, vault_issues(v))

    any_issue |= section(lines, "memory", memory_issues(report["memory"]))

    if any_issue:
        lines.append("\nRun /brain-doctor to fix.")
    print("\n".join(lines))
    return 1 if any_issue else 0


if __name__ == "__main__":
    sys.exit(main())

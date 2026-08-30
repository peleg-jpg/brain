#!/usr/bin/env python3
"""Transcript memory - local RAG over completed Claude Code transcripts.

Modeled on the Hermes agent's holographic memory provider (SQLite + FTS5,
BM25 retrieval, retrieval counting) adapted to Claude Code:

  - Ingests session transcript .jsonl files from ~/.claude/projects/
  - Chunks them into user<->assistant exchanges with project/branch/time metadata
  - Indexes into SQLite FTS5 for BM25 full-text retrieval (Hebrew-safe)
  - Designed to run from a SessionEnd hook (reads hook JSON on stdin)

Zero dependencies: Python 3 stdlib only.

Commands:
  ingest [PATH] [--hook]   ingest one transcript (PATH, or hook JSON on stdin)
  backfill [--force]       ingest every transcript under ~/.claude/projects
  search QUERY [...]       BM25 search over all exchanges
  session SESSION_ID       list a session's exchanges
  show CHUNK_ID            print one full exchange
  stats                    corpus statistics
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "TRANSCRIPT_MEMORY_DB",
    Path.home() / ".claude" / "transcript-memory" / "transcripts.db",
))
PROJECTS_DIR = Path.home() / ".claude" / "projects"
# ~/.claude/projects/<slug> encodes the cwd; strip the home prefix for display.
_HOME_SLUG = re.sub(r"[^A-Za-z0-9]+", "-", str(Path.home())) + "-"

# Obsidian vaults indexed alongside transcripts (D1): whisper notes and wiki
# notes surface in the same recall/search path under one synthetic project.
VAULT_PROJECT = "obsidian-vault"


def _vault_roots():
    """Vault discovery: $BRAIN_VAULT, then ~/.claude/brain-config.json, else ~/obsidian-brain."""
    roots = []
    env = os.environ.get("BRAIN_VAULT")
    if env:
        roots.append(Path(env).expanduser())
    cfg = Path.home() / ".claude" / "brain-config.json"
    if cfg.exists():
        try:
            vp = json.loads(cfg.read_text(encoding="utf-8")).get("vault_path")
            if vp:
                roots.append(Path(vp).expanduser())
        except (OSError, ValueError):
            pass
    if not roots:
        roots.append(Path.home() / "obsidian-brain")
    out = []
    for r in roots:
        if r not in out:
            out.append(r)
    return tuple(out)


VAULT_ROOTS = _vault_roots()
_VAULT_SKIP_DIRS = frozenset((".obsidian", ".graphify", ".lint"))

USER_TEXT_CAP = 4000
ASSISTANT_TEXT_CAP = 32000

# Machine-generated session dirs that would pollute retrieval (e.g. claude-mem
# observer agents re-narrating primary sessions already indexed here).
EXCLUDED_PROJECT_MARKERS = ("claude-mem-observer-sessions",)


def _project_excluded(project: str) -> bool:
    return any(m in project for m in EXCLUDED_PROJECT_MARKERS)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    project     TEXT,
    path        TEXT,
    file_mtime  REAL,
    file_size   INTEGER,
    chunk_count INTEGER DEFAULT 0,
    summary     TEXT DEFAULT '',
    goal        TEXT DEFAULT '',
    first_ts    TEXT,
    last_ts     TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recall_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id  TEXT,
    terms       TEXT,
    injected    TEXT,
    prompt_snip TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    project         TEXT,
    git_branch      TEXT,
    ts              TEXT,
    user_text       TEXT DEFAULT '',
    assistant_text  TEXT DEFAULT '',
    tools           TEXT DEFAULT '',
    retrieval_count INTEGER DEFAULT 0,
    UNIQUE (session_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_session ON chunks(session_id);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project);
CREATE INDEX IF NOT EXISTS idx_chunks_ts      ON chunks(ts);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    user_text, assistant_text, tools,
    content=chunks, content_rowid=chunk_id,
    tokenize="unicode61 remove_diacritics 2"
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, user_text, assistant_text, tools)
        VALUES (new.chunk_id, new.user_text, new.assistant_text, new.tools);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, user_text, assistant_text, tools)
        VALUES ('delete', old.chunk_id, old.user_text, old.assistant_text, old.tools);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, user_text, assistant_text, tools)
        VALUES ('delete', old.chunk_id, old.user_text, old.assistant_text, old.tools);
    INSERT INTO chunks_fts(rowid, user_text, assistant_text, tools)
        VALUES (new.chunk_id, new.user_text, new.assistant_text, new.tools);
END;
"""

_RE_SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
# Harness-injected "user" messages that are not real user turns; an exchange
# stays open across them so assistant text lands under the real question.
_RE_INJECTED_USER = re.compile(
    r"^(Base directory for this skill\b|Tool loaded\b|Caveat: the messages below)"
)
_RE_COMMAND_TAGS = re.compile(
    r"<(command-name|command-message|command-args|local-command-stdout)>"
    r".*?</\1>",
    re.DOTALL,
)
# IDE/editor and local-command wrappers that ride inside a real user turn but
# are not the user's prose - stripped so goals/snippets stay clean.
_RE_WRAPPER_TAGS = re.compile(
    r"<(ide_[a-z_]+|local-command-caveat)>.*?</\1>", re.DOTALL
)
# Harness-generated "user" turns that survive the filters but make meaningless
# session goals (kept as searchable chunks, just never picked as the goal).
_RE_PSEUDO_GOAL = re.compile(
    r"^(A session-scoped Stop hook is now active|#\s*/|<[a-z_-]+>)"
)


def open_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for DBs created before newer columns existed."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    if "goal" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN goal TEXT DEFAULT ''")
        conn.commit()
    if "harvest_status" not in cols:
        # '' = never reviewed, 'harvested' / 'skipped' = decided (see harvest-mark)
        conn.execute("ALTER TABLE sessions ADD COLUMN harvest_status TEXT DEFAULT ''")
        conn.commit()


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    text = _RE_SYSTEM_REMINDER.sub("", text)
    text = _RE_COMMAND_TAGS.sub("", text)
    text = _RE_WRAPPER_TAGS.sub("", text)
    return text.strip()


# Transcripts routinely contain pasted keys/tokens; this DB is read back into a
# browser dashboard (claude os). Scrub known secret shapes before they land.
_RE_SECRETS = re.compile(
    r"""(
        sk-ant-[A-Za-z0-9_-]{20,}                                       # anthropic
      | sk-[A-Za-z0-9]{20,}                                             # openai
      | gh[posru]_[A-Za-z0-9]{20,}                                      # github token
      | github_pat_[A-Za-z0-9_]{20,}
      | AKIA[0-9A-Z]{16}                                                # aws key id
      | AIza[0-9A-Za-z_-]{35}                                           # google api key
      | xox[baprs]-[A-Za-z0-9-]{10,}                                    # slack
      | eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}    # jwt
      | -----BEGIN[^-]+PRIVATE\ KEY-----.*?-----END[^-]+PRIVATE\ KEY-----
      | \b[0-9a-f]{32}\b                                                # bare md5-shaped api key (kie etc.)
    )""",
    re.VERBOSE | re.DOTALL,
)
_RE_SECRET_KV = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd|access[_-]?token)\b"
    r"\s*[:=]\s*[\"']?([A-Za-z0-9_\-./+]{12,})[\"']?"
)


def _redact(text: str) -> str:
    text = _RE_SECRETS.sub("[REDACTED]", text)
    return _RE_SECRET_KV.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)


def _user_text_from_message(message: dict) -> str:
    """Real user prose from a user line; '' for tool results / hook noise."""
    content = message.get("content")
    if isinstance(content, str):
        return _clean_text(content)
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return ""
        parts = [
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return _clean_text("\n".join(p for p in parts if p))
    return ""


def _assistant_parts_from_message(message: dict) -> "tuple[list[str], list[str]]":
    """(text blocks, tool names) from an assistant line. Thinking is skipped."""
    texts: list[str] = []
    tools: list[str] = []
    content = message.get("content")
    if isinstance(content, str):
        if content.strip():
            texts.append(content.strip())
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text", "").strip():
                texts.append(block["text"].strip())
            elif block.get("type") == "tool_use" and block.get("name"):
                tools.append(block["name"])
    return texts, tools


def parse_transcript(path: Path) -> dict:
    """Parse one transcript .jsonl into exchanges + session metadata."""
    exchanges: list[dict] = []
    current: "dict | None" = None
    session_id = path.stem
    summary = ""
    first_ts = last_ts = None
    # Post-compaction resumes replay earlier exchanges verbatim; dedup within
    # the file so the same Q/A is not indexed twice.
    seen_hashes: set = set()

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        current["user_text"] = _redact(current["user_text"][:USER_TEXT_CAP])
        current["assistant_text"] = _redact(
            "\n\n".join(current["assistant_texts"])[:ASSISTANT_TEXT_CAP]
        )
        seen: set[str] = set()
        tools = [t for t in current["tools"] if not (t in seen or seen.add(t))]
        current["tools"] = " ".join(tools)[:500]
        if current["user_text"] or current["assistant_text"]:
            key = hash((current["user_text"][:200], current["assistant_text"][:200]))
            if key not in seen_hashes:
                seen_hashes.add(key)
                exchanges.append(current)
        current = None

    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                line = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(line, dict):
                continue

            ltype = line.get("type")
            if ltype == "summary":
                summary = line.get("summary", "") or summary
                continue
            if line.get("isSidechain"):
                continue
            if ltype not in ("user", "assistant"):
                continue
            if "attachment" in line:
                continue

            message = line.get("message") or {}
            ts = line.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            sid = line.get("sessionId")
            if sid:
                session_id = sid

            if ltype == "user":
                text = _user_text_from_message(message)
                if not text or _RE_INJECTED_USER.match(text):
                    continue
                flush()
                current = {
                    "user_text": text,
                    "assistant_texts": [],
                    "tools": [],
                    "ts": ts,
                    "git_branch": line.get("gitBranch") or "",
                }
            elif ltype == "assistant" and current is not None:
                texts, tools = _assistant_parts_from_message(message)
                current["assistant_texts"].extend(texts)
                current["tools"].extend(tools)

    flush()
    # Session goal = first real user prompt (extractive, no LLM). Powers the
    # coarse "what was this session about" line in recall output. Harness
    # turns that read as "user" (Stop-hook continuations, injected skill
    # bodies) and sub-5-char prompts ("go") make meaningless goals - skip to
    # the first real one.
    goal = ""
    for ex in exchanges:
        t = ex["user_text"]
        if len(t) >= 5 and not _RE_PSEUDO_GOAL.match(t):
            goal = t[:300]
            break
    return {
        "session_id": session_id,
        "summary": summary,
        "goal": goal,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "exchanges": exchanges,
    }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_file(conn: sqlite3.Connection, path: Path, force: bool = False) -> "tuple[str, int]":
    """Ingest one transcript. Returns (status, chunk_count).

    status: 'ingested' | 'unchanged' | 'missing'
    Re-ingestion of a grown session replaces its chunks (sessions resume).
    """
    if not path.exists():
        return "missing", 0

    stat = path.stat()
    project = path.parent.name if path.parent != path else ""
    if _project_excluded(project):
        return "excluded", 0
    parsed_probe_id = path.stem

    if not force:
        row = conn.execute(
            "SELECT file_mtime, file_size FROM sessions WHERE session_id = ? OR path = ?",
            (parsed_probe_id, str(path)),
        ).fetchone()
        if row and row["file_mtime"] == stat.st_mtime and row["file_size"] == stat.st_size:
            return "unchanged", 0

    parsed = parse_transcript(path)
    session_id = parsed["session_id"]

    with conn:
        conn.execute("DELETE FROM chunks WHERE session_id = ?", (session_id,))
        for index, ex in enumerate(parsed["exchanges"]):
            conn.execute(
                """
                INSERT INTO chunks (session_id, chunk_index, project, git_branch,
                                    ts, user_text, assistant_text, tools)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, index, project, ex["git_branch"],
                    ex["ts"], ex["user_text"], ex["assistant_text"], ex["tools"],
                ),
            )
        conn.execute(
            """
            INSERT INTO sessions (session_id, project, path, file_mtime, file_size,
                                  chunk_count, summary, goal, first_ts, last_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                project     = excluded.project,
                path        = excluded.path,
                file_mtime  = excluded.file_mtime,
                file_size   = excluded.file_size,
                chunk_count = excluded.chunk_count,
                summary     = excluded.summary,
                goal        = excluded.goal,
                first_ts    = excluded.first_ts,
                last_ts     = excluded.last_ts,
                ingested_at = CURRENT_TIMESTAMP
            """,
            (
                session_id, project, str(path), stat.st_mtime, stat.st_size,
                len(parsed["exchanges"]), parsed["summary"], parsed["goal"],
                parsed["first_ts"], parsed["last_ts"],
            ),
        )
    return "ingested", len(parsed["exchanges"])


def cmd_ingest(args: argparse.Namespace) -> int:
    path = None
    if args.path:
        path = Path(args.path)
    elif not sys.stdin.isatty():
        # SessionEnd hook mode: hook JSON arrives on stdin.
        try:
            hook = json.loads(sys.stdin.read() or "{}")
            transcript_path = hook.get("transcript_path")
            if transcript_path:
                path = Path(transcript_path)
        except (json.JSONDecodeError, OSError):
            pass
    if path is None:
        print("no transcript path (arg or hook stdin)", file=sys.stderr)
        return 0 if args.hook else 1

    try:
        conn = open_db()
        status, count = ingest_file(conn, path, force=args.force)
        conn.close()
        if not args.hook:
            print(f"{status}: {path.name} ({count} exchanges)")
    except Exception as exc:  # a hook must never block session teardown
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 0 if args.hook else 1
    return 0


def _vault_note_files():
    for root in VAULT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            if not _VAULT_SKIP_DIRS.intersection(path.parts):
                yield path


def ingest_vault_note(conn: sqlite3.Connection, path: Path, force: bool = False) -> "tuple[str, int]":
    """Index one vault note. A note is one 'session' keyed by its path, so an
    edited note replaces its old chunks instead of duplicating them."""
    stat = path.stat()
    session_id = f"vault:{path}"
    if not force:
        row = conn.execute(
            "SELECT file_mtime, file_size FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row and row["file_mtime"] == stat.st_mtime and row["file_size"] == stat.st_size:
            return "unchanged", 0

    text = _redact(path.read_text(encoding="utf-8", errors="replace").strip())
    title = str(path.relative_to(Path.home()))
    ts = datetime.fromtimestamp(stat.st_mtime).isoformat()
    # Title rides in user_text (BM25-weighted 3x), body in assistant_text.
    pieces = [text[i:i + ASSISTANT_TEXT_CAP]
              for i in range(0, len(text), ASSISTANT_TEXT_CAP)] or [""]

    with conn:
        conn.execute("DELETE FROM chunks WHERE session_id = ?", (session_id,))
        for index, piece in enumerate(pieces):
            conn.execute(
                """
                INSERT INTO chunks (session_id, chunk_index, project, git_branch,
                                    ts, user_text, assistant_text, tools)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, index, VAULT_PROJECT, "", ts, title, piece, ""),
            )
        conn.execute(
            """
            INSERT INTO sessions (session_id, project, path, file_mtime, file_size,
                                  chunk_count, summary, goal, first_ts, last_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                path        = excluded.path,
                file_mtime  = excluded.file_mtime,
                file_size   = excluded.file_size,
                chunk_count = excluded.chunk_count,
                goal        = excluded.goal,
                last_ts     = excluded.last_ts,
                ingested_at = CURRENT_TIMESTAMP
            """,
            (session_id, VAULT_PROJECT, str(path), stat.st_mtime, stat.st_size,
             len(pieces), "", title, ts, ts),
        )
    return "ingested", len(pieces)


def backfill_vaults(conn: sqlite3.Connection, force: bool = False) -> "tuple[int, int, int, int]":
    """Incremental vault sweep. Returns (ingested, unchanged, failed, chunks).
    Notes deleted or renamed on disk are pruned so stale copies never rank."""
    ingested = unchanged = failed = total_chunks = 0
    seen: set = set()
    for path in _vault_note_files():
        seen.add(f"vault:{path}")
        try:
            status, count = ingest_vault_note(conn, path, force=force)
        except Exception as exc:
            failed += 1
            print(f"  FAIL {path.name}: {exc}", file=sys.stderr)
            continue
        if status == "ingested":
            ingested += 1
            total_chunks += count
        else:
            unchanged += 1
    stale = [
        r["session_id"] for r in conn.execute(
            "SELECT session_id FROM sessions WHERE project = ?", (VAULT_PROJECT,)
        ) if r["session_id"] not in seen
    ]
    with conn:
        for sid in stale:
            conn.execute("DELETE FROM chunks WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
    return ingested, unchanged, failed, total_chunks


def cmd_backfill(args: argparse.Namespace) -> int:
    conn = open_db()
    files = sorted(PROJECTS_DIR.glob("*/*.jsonl"))
    ingested = unchanged = failed = total_chunks = 0
    for i, path in enumerate(files, 1):
        try:
            status, count = ingest_file(conn, path, force=args.force)
        except Exception as exc:
            failed += 1
            print(f"  FAIL {path.name}: {exc}", file=sys.stderr)
            continue
        if status == "ingested":
            ingested += 1
            total_chunks += count
        else:
            unchanged += 1
        if i % 250 == 0:
            print(f"  ... {i}/{len(files)}")
    v_in, v_un, v_fail, v_chunks = backfill_vaults(conn, force=args.force)
    failed += v_fail
    conn.close()
    print(
        f"backfill done: {ingested} ingested ({total_chunks} exchanges), "
        f"{unchanged} unchanged, {failed} failed, {len(files)} files total"
    )
    print(
        f"vault: {v_in} notes ingested ({v_chunks} chunks), "
        f"{v_un} unchanged, {v_fail} failed"
    )
    return 1 if failed and not ingested else 0


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

# --- FTS5 query building (Hebrew-particle aware) --------------------------
_HEB = re.compile(r"[֐-׿]")
# Single-letter clitic particles Hebrew fuses onto the front of a word
# (ha-, we-, be-, le-, mi-, ke-, she-). unicode61 tokenizes the fused form as
# one token, so "קרוסלה" would never match "הקרוסלה" without expansion.
_HEB_PREFIXES = ("ו", "ה", "ב", "ל", "מ", "כ", "ש")


def _expand_term(tok: str) -> str:
    """One query token -> an FTS5 sub-clause tolerant of Hebrew particles."""
    tok = tok.replace('"', "")
    if not tok:
        return ""
    if not _HEB.search(tok):
        return f'"{tok}"'
    bases = {tok}
    b = tok
    for _ in range(2):  # strip up to two fused particles: "ולכלב" -> "כלב"
        if len(b) > 3 and b[0] in _HEB_PREFIXES:
            b = b[1:]
            bases.add(b)
        else:
            break
    variants = set(bases)
    for base in list(bases):
        for p in _HEB_PREFIXES:  # also add fused forms of the bare word
            variants.add(p + base)
    # suffix wildcard catches inflected endings (קרוסלה -> קרוסלות)
    clause = " OR ".join(f'"{v}"*' for v in sorted(variants))
    return f"({clause})"


def _build_match(terms: list, mode: str = "and") -> str:
    groups = [g for g in (_expand_term(t) for t in terms) if g]
    if not groups:
        return ""
    return (" AND " if mode == "and" else " OR ").join(groups)


def _fts_rows(conn, match, current_session=None, project=None, since=None,
              pool=24, highlight=True):
    """BM25-ordered candidate pool, joined to session goal. Empty match -> []."""
    if not match:
        return []
    m1, m2 = (">>", "<<") if highlight else ("", "")
    where = ["chunks_fts MATCH ?"]
    params: list = [match]
    if current_session:
        where.append("c.session_id != ?")
        params.append(current_session)
    if project:
        where.append("c.project LIKE ?")
        params.append(f"%{project}%")
    if since:
        where.append("c.ts >= ?")
        params.append(since)
    params.append(pool)
    sql = f"""
        SELECT c.chunk_id, c.session_id, c.project, c.ts, c.tools,
               c.retrieval_count, s.goal AS goal,
               snippet(chunks_fts, 0, '{m1}', '{m2}', ' ... ', 18) AS u_snip,
               snippet(chunks_fts, 1, '{m1}', '{m2}', ' ... ', 24) AS a_snip
        FROM chunks_fts
        JOIN chunks c ON c.chunk_id = chunks_fts.rowid
        LEFT JOIN sessions s ON s.session_id = c.session_id
        WHERE {' AND '.join(where)}
        ORDER BY bm25(chunks_fts, 3.0, 1.0, 0.5)
        LIMIT ?
    """
    return conn.execute(sql, params).fetchall()


def _blend(rows, current_project=None, limit=8):
    """Rank-blend BM25 relevance with recency, same-project and proven-useful
    boosts. Lower blended score = better. Avoids the old hard recency re-sort
    that let a weak-but-recent hit outrank a strong-but-older one."""
    if not rows:
        return []
    rel = {r["chunk_id"]: i for i, r in enumerate(rows)}  # bm25 order (best=0)
    by_ts = sorted(rows, key=lambda r: (r["ts"] or ""), reverse=True)
    rec = {r["chunk_id"]: i for i, r in enumerate(by_ts)}
    scored = []
    for r in rows:
        cid = r["chunk_id"]
        b = 0.65 * rel[cid] + 0.35 * rec[cid]
        if current_project and r["project"] == current_project:
            b -= 1.5
        b -= min(r["retrieval_count"] or 0, 5) * 0.15
        scored.append((b, r))
    scored.sort(key=lambda x: x[0])
    return [r for _, r in scored[:limit]]


def _retrieve(conn, terms, current_session=None, current_project=None,
              project=None, since=None, limit=8, force_or=False, highlight=True):
    """AND-first retrieval with an OR fallback when AND is too sparse."""
    mode = "or" if force_or else "and"
    rows = _fts_rows(conn, _build_match(terms, mode), current_session,
                     project, since, highlight=highlight)
    if not force_or and len(rows) < 3:
        rows = _fts_rows(conn, _build_match(terms, "or"), current_session,
                         project, since, highlight=highlight)
    return _blend(rows, current_project, limit)


def cmd_search(args: argparse.Namespace) -> int:
    conn = open_db()
    terms = re.findall(r"\w+", args.query)
    if not terms:
        print("empty query")
        conn.close()
        return 1

    rows = _retrieve(conn, terms, project=args.project, since=args.since,
                     limit=args.limit, force_or=args.any)

    if args.json:
        # Machine consumer (claude os dashboard): one query path, no count bump
        # (UI queries are not a proven-useful signal like recall injections).
        out = [
            {k: r[k] for k in ("chunk_id", "session_id", "project", "ts",
                               "goal", "u_snip", "a_snip")}
            for r in rows
        ]
        print(json.dumps(out, ensure_ascii=False))
        conn.close()
        return 0

    if not rows:
        print("no results")
        conn.close()
        return 0

    ids = [r["chunk_id"] for r in rows]
    conn.execute(
        f"UPDATE chunks SET retrieval_count = retrieval_count + 1 "
        f"WHERE chunk_id IN ({','.join('?' * len(ids))})",
        ids,
    )
    conn.commit()

    for r in rows:
        date = (r["ts"] or "")[:10]
        proj = (r["project"] or "").replace(_HOME_SLUG, "")
        goal = _oneline(r["goal"] or "", 80)
        head = f"[{r['chunk_id']}] {date} {proj} (session {r['session_id'][:8]})"
        if goal:
            head += f"  ·  {goal}"
        print(head)
        if r["u_snip"]:
            print(f"  Q: {_oneline(r['u_snip'])}")
        if r["a_snip"]:
            print(f"  A: {_oneline(r['a_snip'])}")
        print()
    conn.close()
    return 0


def _oneline(text: str, cap: int = 300) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:cap]


# Recall-intent markers: the UserPromptSubmit hook only injects context when
# the prompt signals the user is reaching for past work. Anything else stays
# silent so no context is wasted on ordinary prompts.
_RE_RECALL_INTENT = re.compile(
    r"(did we|have we|last time|previous(ly)? (session|time)|we already|"
    r"remember (when|how|the)|what did (we|i) do|search (my |the )?transcripts|"
    r"how did we|how we (fixed|solved|built|did)|the (approach|fix|way) we|"
    r"we (used|tried|built|solved|fixed)|our previous|back (when|then)|"
    r"בפעם שעברה|פעם קודמת|כבר (עשינו|פתרנו|בנינו|תיקנו)|מה עשינו|"
    r"מה היה ה|איך (פתרנו|תיקנו|בנינו|עשינו|עשית)|זוכר (איך|את|ש))",
    re.IGNORECASE,
)

# Prompts from automated jobs start with fixed machine preambles - recall
# injection there only wastes their context. Add your own cron preambles here.
_CRON_PREAMBLES = (
    "You are reviewing a finished Claude Code session",
)

_STOPWORDS = frozenset(
    "the a an and or but for with this that what how did have was were are is "
    "you your our we they them then than from into onto over under about when "
    "where why who whom will would could should can may might must not don "
    "dont doesn didn its it's все את של מה זה על אני אתה אנחנו כבר איך למה "
    "אבל עם לא כן יש אין רק גם או אם כי אז".split()
)


def _recall_terms(prompt: str, cap: int = 12) -> list:
    """Distinctive query tokens from a prompt (stopwords and short words out)."""
    terms = []
    for tok in re.findall(r"\w+", prompt):
        low = tok.lower()
        if len(low) >= 3 and low not in _STOPWORDS and low not in terms:
            terms.append(low)
    return terms[:cap]


def cmd_recall(args: argparse.Namespace) -> int:
    """UserPromptSubmit hook: marker-gated retrieval, stdout becomes context.

    Always exits 0 - a recall failure must never block a prompt.
    """
    try:
        hook = json.loads(sys.stdin.read() or "{}") if not args.prompt else {}
        prompt = args.prompt or hook.get("prompt", "")
        current_session = hook.get("session_id", "")
        cwd = hook.get("cwd", "")
        # Reconstruct the project-dir slug so same-project hits get boosted.
        current_project = re.sub(r"[^A-Za-z0-9]+", "-", cwd).strip("-") if cwd else None

        if not prompt or any(prompt.lstrip().startswith(p) for p in _CRON_PREAMBLES):
            return 0
        if not args.always and not _RE_RECALL_INTENT.search(prompt):
            return 0
        terms = _recall_terms(prompt)
        if not terms:
            return 0

        conn = open_db()
        rows = _retrieve(conn, terms, current_session=current_session,
                         current_project=current_project, limit=3, highlight=False)
        if not rows:
            conn.close()
            return 0

        # Close the feedback loop: bump retrieval_count (feeds the proven-useful
        # ranking boost) and log what was injected for later gate/rank tuning.
        ids = [r["chunk_id"] for r in rows]
        conn.execute(
            f"UPDATE chunks SET retrieval_count = retrieval_count + 1 "
            f"WHERE chunk_id IN ({','.join('?' * len(ids))})",
            ids,
        )
        conn.execute(
            "INSERT INTO recall_log (session_id, terms, injected, prompt_snip) "
            "VALUES (?, ?, ?, ?)",
            (current_session, " ".join(terms), ",".join(map(str, ids)),
             _oneline(prompt, 160)),
        )
        conn.commit()
        conn.close()

        lines = ["[transcript-memory] related past work found:"]
        for r in rows:
            proj = (r["project"] or "").replace(_HOME_SLUG, "")
            date = (r["ts"] or "")[:10]
            goal = _oneline(r["goal"] or "", 90)
            head = f"- {date} {proj} (chunk {r['chunk_id']})"
            if goal:
                head += f" [goal: {goal}]"
            lines.append(head)
            lines.append(
                f"    Q: {_oneline(r['u_snip'], 120)} | A: {_oneline(r['a_snip'], 160)}"
            )
        lines.append(
            f'Full context: python3 "{Path(__file__).resolve()}" '
            "show <chunk> | session <id>"
        )
        print("\n".join(lines))
    except Exception:
        pass
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    conn = open_db()
    rows = conn.execute(
        """
        SELECT chunk_id, chunk_index, ts, user_text, assistant_text
        FROM chunks
        WHERE session_id LIKE ?
        ORDER BY chunk_index
        LIMIT ?
        """,
        (f"{args.session_id}%", args.limit),
    ).fetchall()
    if not rows:
        print("no such session")
        conn.close()
        return 1
    for r in rows:
        print(f"[{r['chunk_id']}] #{r['chunk_index']} {(r['ts'] or '')[:19]}")
        print(f"  Q: {_oneline(r['user_text'], 200)}")
        print(f"  A: {_oneline(r['assistant_text'], 200)}")
        print()
    conn.close()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = open_db()
    r = conn.execute(
        "SELECT * FROM chunks WHERE chunk_id = ?", (args.chunk_id,)
    ).fetchone()
    if r is None:
        print("no such chunk")
        conn.close()
        return 1
    print(f"chunk {r['chunk_id']}  session {r['session_id']}  #{r['chunk_index']}")
    print(f"project {r['project']}  branch {r['git_branch']}  ts {r['ts']}")
    if r["tools"]:
        print(f"tools: {r['tools']}")
    print("\n--- USER ---")
    print(r["user_text"])
    print("\n--- ASSISTANT ---")
    print(r["assistant_text"])
    conn.close()
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    conn = open_db()
    sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"db: {DB_PATH}")
    size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    print(f"size: {size / 1_048_576:.1f} MB")
    print(f"sessions: {sessions}   exchanges: {chunks}")
    print("\ntop projects:")
    for r in conn.execute(
        """
        SELECT project, COUNT(*) AS n FROM chunks
        GROUP BY project ORDER BY n DESC LIMIT 12
        """
    ):
        proj = (r["project"] or "?").replace(_HOME_SLUG, "")
        print(f"  {r['n']:>6}  {proj}")

    recalls = conn.execute("SELECT COUNT(*) FROM recall_log").fetchone()[0]
    print(f"\nrecall injections logged: {recalls}")
    top = conn.execute(
        "SELECT chunk_id, retrieval_count, project FROM chunks "
        "WHERE retrieval_count > 0 ORDER BY retrieval_count DESC LIMIT 8"
    ).fetchall()
    if top:
        print("most-retrieved chunks:")
        for r in top:
            proj = (r["project"] or "?").replace(_HOME_SLUG, "")
            print(f"  {r['retrieval_count']:>4}x  [{r['chunk_id']}] {proj}")
    conn.close()
    return 0


# ---------------------------------------------------------------------------
# Harvest nomination (feeds the Obsidian harvest skill)
# ---------------------------------------------------------------------------

# Signals that a session ended with work actually shipped, not just discussed.
_RE_SHIP_SIGNAL = re.compile(
    r"(commit(ted)?\s+[0-9a-f]{7}|pushed to|git push|deployed|merged|shipped|"
    r"went live|live at|now live|all tests? pass|tests? pass(ed|ing)|"
    r"backfill (completed|done)|launchctl load|עלה לאוויר|באוויר|נפרס)",
    re.IGNORECASE,
)


def cmd_harvest_candidates(args: argparse.Namespace) -> int:
    """Nominate finished-looking sessions for the Obsidian harvest skill.

    Pure heuristic, no LLM: a session qualifies when it has a goal, real
    volume, is at least a day old (not mid-flight), and its assistant text
    contains shipped-work signals. Grouped per project, capped, read-only -
    re-nomination is harmless because the harvest skill updates over creates.
    """
    conn = open_db()
    rows = conn.execute(
        """
        SELECT session_id, project, goal, last_ts, chunk_count FROM sessions
        WHERE harvest_status = '' AND goal != '' AND chunk_count >= 3
          AND length(project) > 1 AND project != ?
          AND last_ts <= datetime('now', '-1 day')
          AND last_ts >= datetime('now', ?)
        ORDER BY last_ts DESC
        """,
        (VAULT_PROJECT, f"-{args.days} days",),
    ).fetchall()

    projects: dict = {}
    for r in rows:
        text = "\n".join(
            c["assistant_text"] for c in conn.execute(
                "SELECT assistant_text FROM chunks WHERE session_id = ?",
                (r["session_id"],),
            )
        )
        signals = len(_RE_SHIP_SIGNAL.findall(text))
        if signals < args.min_signals:
            continue
        projects.setdefault(r["project"], []).append({
            "session_id": r["session_id"],
            "goal": _redact(_oneline(r["goal"], 200)),
            "last_ts": r["last_ts"],
            "chunks": r["chunk_count"],
            "signals": signals,
        })
    conn.close()

    # Cap sessions per project (strongest first). Truncated ones re-surface on
    # later runs as marked ones drain - the queue empties itself.
    ranked = sorted(
        (
            {"project": p, "total_signals": sum(s["signals"] for s in ss),
             "sessions": sorted(ss, key=lambda s: s["signals"], reverse=True)[:6]}
            for p, ss in projects.items()
        ),
        key=lambda c: c["total_signals"],
        reverse=True,
    )
    dropped = ranked[args.limit:]
    ranked = ranked[:args.limit]

    if args.json:
        print(json.dumps(ranked, ensure_ascii=False, indent=1))
    else:
        for c in ranked:
            print(f"{c['project']}  (signals: {c['total_signals']})")
            for s in c["sessions"]:
                print(f"  {s['session_id'][:8]}  {s['last_ts'][:10]}  "
                      f"sig={s['signals']}  {s['goal'][:100]}")
        if dropped:
            print(f"[capped: {len(dropped)} more project(s) dropped, "
                  f"rerun with --limit {args.limit + len(dropped)}]",
                  file=sys.stderr)
    return 0


def cmd_harvest_mark(args: argparse.Namespace) -> int:
    """Record a harvest decision so sessions stop being re-nominated."""
    if args.status not in ("harvested", "skipped", ""):
        print("status must be: harvested | skipped | '' (requeue)", file=sys.stderr)
        return 1
    conn = open_db()
    n = 0
    for sid in args.session_ids:
        n += conn.execute(
            "UPDATE sessions SET harvest_status = ? WHERE session_id LIKE ?",
            (args.status, sid + "%"),
        ).rowcount
    conn.commit()
    conn.close()
    print(f"marked {n} session(s) {args.status or 'requeued'}")
    return 0 if n else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="transcript-memory",
        description="Local RAG over completed Claude Code transcripts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="ingest one transcript (path or hook stdin)")
    p.add_argument("path", nargs="?")
    p.add_argument("--hook", action="store_true", help="hook mode: silent, always exit 0")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("backfill", help="ingest all transcripts in ~/.claude/projects")
    p.add_argument("--force", action="store_true", help="re-ingest unchanged files too")
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("search", help="BM25 search over exchanges")
    p.add_argument("query")
    p.add_argument("--project", help="filter by project slug substring")
    p.add_argument("--since", help="ISO date lower bound, e.g. 2026-06-01")
    p.add_argument("--limit", type=int, default=8)
    p.add_argument("--any", action="store_true", help="OR terms instead of AND")
    p.add_argument("--json", action="store_true", help="emit JSON rows (no count bump)")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("recall", help="hook mode: marker-gated context injection")
    p.add_argument("prompt", nargs="?", help="prompt text (default: hook JSON stdin)")
    p.add_argument("--always", action="store_true", help="skip intent-marker gate")
    p.set_defaults(func=cmd_recall)

    p = sub.add_parser("session", help="list a session's exchanges")
    p.add_argument("session_id")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_session)

    p = sub.add_parser("show", help="print one full exchange")
    p.add_argument("chunk_id", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("stats", help="corpus statistics")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("harvest-candidates",
                       help="nominate shipped-looking sessions for vault harvest")
    p.add_argument("--days", type=int, default=14, help="lookback window")
    p.add_argument("--min-signals", type=int, default=3,
                   help="min shipped-work signals per session")
    p.add_argument("--limit", type=int, default=5, help="max projects")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_harvest_candidates)

    p = sub.add_parser("harvest-mark",
                       help="record harvest decision for sessions")
    p.add_argument("status", help="harvested | skipped | '' (requeue)")
    p.add_argument("session_ids", nargs="+", help="session id or unique prefix")
    p.set_defaults(func=cmd_harvest_mark)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

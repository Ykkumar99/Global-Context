"""SQLite-backed context store.

Tables
------
profiles   : one JSON snapshot per GLID (seller profile / buyer getContext)
events     : append-only, one row per activity on any channel
sections   : cached rendered section per (glid, section)  -> incremental refresh
docs       : the latest rendered .md per GLID with version + token count
freshness  : per live event: when it arrived, when the .md reflected it
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator

from .config import get_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
  glid INTEGER PRIMARY KEY, role TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  glid INTEGER NOT NULL, ts TEXT NOT NULL, channel TEXT NOT NULL,
  kind TEXT, text TEXT, meta TEXT, live INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_events_glid_ts ON events(glid, ts);
CREATE INDEX IF NOT EXISTS ix_events_channel ON events(channel);
CREATE TABLE IF NOT EXISTS sections (
  glid INTEGER, section TEXT, content TEXT, updated_at TEXT,
  PRIMARY KEY (glid, section)
);
CREATE TABLE IF NOT EXISTS docs (
  glid INTEGER PRIMARY KEY, role TEXT, md TEXT, version INTEGER, tokens INTEGER,
  updated_at TEXT, llm_enriched INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS freshness (
  event_id INTEGER PRIMARY KEY, glid INTEGER, channel TEXT,
  received_at REAL, doc_at REAL, llm_at REAL, sections TEXT
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""

ISO = "%Y-%m-%d %H:%M:%S"


def to_ts(dt: datetime) -> str:
    return dt.strftime(ISO)


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s[:19], ISO)


class Store:
    def __init__(self, path: str | Path | None = None):
        cfg = get_config()
        self.path = Path(path) if path else cfg.path("db_path")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.lock = threading.RLock()
        with self.conn() as c:
            c.executescript(SCHEMA)

    # one connection per thread (FastAPI runs handlers in a threadpool)
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            self._local.c = c
        return c

    # ---------------------------------------------------------------- meta
    def set_meta(self, k: str, v) -> None:
        with self.lock, self.conn() as c:
            c.execute("REPLACE INTO meta VALUES (?,?)", (k, json.dumps(v)))

    def get_meta(self, k: str, default=None):
        r = self.conn().execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else default

    # ------------------------------------------------------------ profiles
    def put_profiles(self, rows: Iterable[tuple[int, str, dict]]) -> None:
        with self.lock, self.conn() as c:
            c.executemany(
                "REPLACE INTO profiles VALUES (?,?,?,?)",
                [(g, role, json.dumps(d, default=str), None) for g, role, d in rows],
            )

    def profile(self, glid: int) -> tuple[str, dict] | None:
        r = self.conn().execute("SELECT role, data FROM profiles WHERE glid=?", (glid,)).fetchone()
        return (r["role"], json.loads(r["data"])) if r else None

    def glids(self, role: str | None = None) -> list[int]:
        q = "SELECT glid FROM profiles" + (" WHERE role=?" if role else "") + " ORDER BY glid"
        return [r[0] for r in self.conn().execute(q, (role,) if role else ())]

    # -------------------------------------------------------------- events
    def add_events(self, rows: Iterable[tuple]) -> None:
        """rows: (glid, ts_str, channel, kind, text, meta_dict, live)"""
        with self.lock, self.conn() as c:
            c.executemany(
                "INSERT INTO events (glid, ts, channel, kind, text, meta, live) VALUES (?,?,?,?,?,?,?)",
                [(g, ts, ch, k, t, json.dumps(m or {}, default=str), lv) for g, ts, ch, k, t, m, lv in rows],
            )

    def add_event(self, glid: int, ts: datetime, channel: str, kind: str, text: str,
                  meta: dict | None = None, live: int = 1) -> int:
        with self.lock, self.conn() as c:
            cur = c.execute(
                "INSERT INTO events (glid, ts, channel, kind, text, meta, live) VALUES (?,?,?,?,?,?,?)",
                (glid, to_ts(ts), channel, kind, text, json.dumps(meta or {}), live),
            )
            return cur.lastrowid

    def events(self, glid: int, as_of: datetime, since: datetime | None = None,
               channels: Iterable[str] | None = None) -> list[dict]:
        q = "SELECT * FROM events WHERE glid=? AND ts<=?"
        args: list = [glid, to_ts(as_of)]
        if since is not None:
            q += " AND ts>=?"
            args.append(to_ts(since))
        if channels:
            chs = list(channels)
            q += f" AND channel IN ({','.join('?' * len(chs))})"
            args += chs
        q += " ORDER BY ts DESC, id DESC"
        out = []
        for r in self.conn().execute(q, args):
            d = dict(r)
            d["ts"] = parse_ts(d["ts"])
            d["meta"] = json.loads(d["meta"] or "{}")
            out.append(d)
        return out

    def max_event_ts(self) -> datetime | None:
        r = self.conn().execute("SELECT MAX(ts) FROM events WHERE live=0").fetchone()
        return parse_ts(r[0]) if r and r[0] else None

    def event_count(self) -> int:
        return self.conn().execute("SELECT COUNT(*) FROM events").fetchone()[0]

    # ------------------------------------------------------ sections / docs
    def put_section(self, glid: int, name: str, content: str) -> bool:
        """Returns True if the section content changed."""
        with self.lock, self.conn() as c:
            old = c.execute("SELECT content FROM sections WHERE glid=? AND section=?", (glid, name)).fetchone()
            if old and old[0] == content:
                return False
            c.execute("REPLACE INTO sections VALUES (?,?,?,datetime('now'))", (glid, name, content))
            return True

    def sections(self, glid: int) -> dict[str, str]:
        return {r[0]: r[1] for r in self.conn().execute(
            "SELECT section, content FROM sections WHERE glid=?", (glid,))}

    def put_doc(self, glid: int, role: str, md: str, tokens: int, llm: bool) -> int:
        with self.lock, self.conn() as c:
            r = c.execute("SELECT version FROM docs WHERE glid=?", (glid,)).fetchone()
            ver = (r[0] if r else 0) + 1
            c.execute("REPLACE INTO docs VALUES (?,?,?,?,?,datetime('now'),?)",
                      (glid, role, md, ver, tokens, int(llm)))
            return ver

    def doc(self, glid: int) -> dict | None:
        r = self.conn().execute("SELECT * FROM docs WHERE glid=?", (glid,)).fetchone()
        return dict(r) if r else None

    # ----------------------------------------------------------- freshness
    def log_fresh(self, event_id: int, glid: int, channel: str, received: float,
                  doc_at: float | None = None, llm_at: float | None = None,
                  sections: list[str] | None = None) -> None:
        with self.lock, self.conn() as c:
            old = c.execute("SELECT * FROM freshness WHERE event_id=?", (event_id,)).fetchone()
            if old:
                received = old["received_at"] or received
                channel = old["channel"] or channel
                doc_at = doc_at or old["doc_at"]
                llm_at = llm_at or old["llm_at"]
                sections = sections or json.loads(old["sections"] or "[]")
            c.execute("REPLACE INTO freshness VALUES (?,?,?,?,?,?,?)",
                      (event_id, glid, channel, received, doc_at, llm_at, json.dumps(sections or [])))

    def freshness_rows(self, limit: int = 5000) -> list[dict]:
        return [dict(r) for r in self.conn().execute(
            "SELECT * FROM freshness ORDER BY event_id DESC LIMIT ?", (limit,))]

    def reset(self) -> None:
        with self.lock, self.conn() as c:
            for t in ("profiles", "events", "sections", "docs", "freshness", "meta"):
                c.execute(f"DELETE FROM {t}")


class Clock:
    """'data' mode: now = end of dataset + wall time elapsed since start."""

    def __init__(self, store: Store):
        cfg = get_config()
        self.mode = cfg.clock or "data"
        fixed = cfg.as_of
        self.base = parse_ts(fixed.replace("T", " ")) if fixed else None
        if self.base is None and self.mode == "data":
            self.base = store.max_event_ts() or datetime.now()
        self.started = datetime.now()

    def now(self) -> datetime:
        if self.mode == "wall":
            return datetime.now()
        return self.base + (datetime.now() - self.started) + timedelta(seconds=1)


def iter_chunks(seq: list, n: int) -> Iterator[list]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]

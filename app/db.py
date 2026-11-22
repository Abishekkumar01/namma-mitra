"""SQLite access layer. One connection per thread, WAL mode, tiny helper API.

Tables
  sessions  - one row per chat (language, state, in-progress flow JSON)
  messages  - full chat history, both directions (restored on page refresh)
  traces    - one row per user action (message, panel submit, payment...)
  calls     - every @logged function call inside a trace (args, result, error, ms)
  records   - generic persisted objects created in the demo (applications, bookings...)
  payments  - simulated payment intents
  docs      - generated documents (rank cards, certificates, tickets) rendered at /doc/<id>
"""
import json
import sqlite3
import threading
import time

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, lang TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'idle',
  flow TEXT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, dir TEXT, payload TEXT,
  trace_id INTEGER, ts REAL);
CREATE INDEX IF NOT EXISTS ix_messages_session ON messages(session_id);
CREATE TABLE IF NOT EXISTS traces(
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, kind TEXT, input TEXT,
  status TEXT, error TEXT, output TEXT, started_at REAL, duration_ms REAL);
CREATE INDEX IF NOT EXISTS ix_traces_session ON traces(session_id);
CREATE TABLE IF NOT EXISTS calls(
  id INTEGER PRIMARY KEY AUTOINCREMENT, trace_id INTEGER, seq INTEGER, depth INTEGER,
  module TEXT, func TEXT, args TEXT, result TEXT, error TEXT, duration_ms REAL, ts REAL);
CREATE INDEX IF NOT EXISTS ix_calls_trace ON calls(trace_id);
CREATE TABLE IF NOT EXISTS records(
  kind TEXT, ref TEXT, session_id TEXT, data TEXT, created_at REAL, updated_at REAL,
  PRIMARY KEY(kind, ref));
CREATE TABLE IF NOT EXISTS payments(
  id TEXT PRIMARY KEY, session_id TEXT, service TEXT, purpose TEXT, amount REAL,
  ref TEXT, context TEXT, status TEXT, method TEXT, txn_id TEXT,
  created_at REAL, paid_at REAL);
CREATE TABLE IF NOT EXISTS docs(
  id TEXT PRIMARY KEY, session_id TEXT, kind TEXT, filename TEXT, data TEXT, created_at REAL);
"""

_write_lock = threading.Lock()


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(config.DB_PATH), timeout=15, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        _local.conn = c
    return c


def init():
    with _write_lock:
        conn().executescript(SCHEMA)
        conn().commit()


def execute(sql, params=()):
    with _write_lock:
        c = conn()
        cur = c.execute(sql, params)
        c.commit()
        return cur


def executemany(sql, rows):
    with _write_lock:
        c = conn()
        c.executemany(sql, rows)
        c.commit()


def query(sql, params=()):
    return [dict(r) for r in conn().execute(sql, params).fetchall()]


def one(sql, params=()):
    r = conn().execute(sql, params).fetchone()
    return dict(r) if r else None


def now():
    return time.time()


# ---- generic records -------------------------------------------------------

def rec_get(kind, ref):
    r = one("SELECT * FROM records WHERE kind=? AND ref=?", (kind, ref))
    if not r:
        return None
    data = json.loads(r["data"] or "{}")
    data["_created_at"] = r["created_at"]
    data["_updated_at"] = r["updated_at"]
    return data


def rec_put(kind, ref, data, session_id=None):
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    ts = now()
    existing = one("SELECT created_at FROM records WHERE kind=? AND ref=?", (kind, ref))
    if existing:
        execute("UPDATE records SET data=?, updated_at=? WHERE kind=? AND ref=?",
                (json.dumps(clean, ensure_ascii=False), ts, kind, ref))
    else:
        execute("INSERT INTO records(kind, ref, session_id, data, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (kind, ref, session_id, json.dumps(clean, ensure_ascii=False), ts, ts))
    return rec_get(kind, ref)

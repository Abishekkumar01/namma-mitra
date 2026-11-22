"""Function-level tracing. This is what makes one-line bug reports possible.

Every user action (sending a message, submitting a panel, paying) opens a *trace*.
Every function decorated with @logged that runs inside it is recorded as a *call*:
module, function, arguments, return value or exception, duration and nesting depth.
Calls are buffered in memory and flushed in one write when the trace ends.

The trace id is shown under each bot bubble in the UI (#123) and in /logs.
Tester says "trace 123: expected X" -> open /logs?trace=123 and see everything.
"""
import contextvars
import dataclasses
import functools
import inspect
import json
import logging
import time
from logging.handlers import RotatingFileHandler

from . import config, db

_current = contextvars.ContextVar("nm_trace", default=None)

config.LOG_DIR.mkdir(parents=True, exist_ok=True)
file_log = logging.getLogger("namma_mitra")
if not file_log.handlers:
    file_log.setLevel(logging.INFO)
    h = RotatingFileHandler(config.LOG_DIR / "namma_mitra.log", maxBytes=5_000_000,
                            backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    file_log.addHandler(h)

SENSITIVE_KEYS = ("aadhaar",)


class Trace:
    def __init__(self, tid, session_id):
        self.id = tid
        self.session_id = session_id
        self.depth = 0
        self.seq = 0
        self.calls = []
        self.start = time.perf_counter()
        self.token = None


def _mask(value):
    s = str(value)
    return ("X" * max(len(s) - 4, 0)) + s[-4:] if s else s


def _scrub(obj, key=""):
    """Mask Aadhaar-like values anywhere in nested args (by key name)."""
    if any(k in key.lower() for k in SENSITIVE_KEYS) and isinstance(obj, (str, int)):
        return _mask(obj)
    if isinstance(obj, dict):
        return {k: _scrub(v, str(k)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(v, key) for v in obj]
    return obj


def _default(o):
    if hasattr(o, "__log__"):
        return o.__log__()
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    return str(o)[:300]


def dump(obj):
    try:
        s = json.dumps(_scrub(obj), default=_default, ensure_ascii=False)
    except Exception as e:  # never let logging break the app
        s = json.dumps(f"<unserialisable: {e}>")
    if len(s) > config.LOG_TRUNCATE:
        s = s[: config.LOG_TRUNCATE] + '..."<truncated>"'
    return s


def begin(session_id, kind, payload):
    cur = db.execute(
        "INSERT INTO traces(session_id, kind, input, status, started_at) VALUES(?,?,?,?,?)",
        (session_id, kind, dump(payload), "running", time.time()))
    t = Trace(cur.lastrowid, session_id)
    t.token = _current.set(t)
    return t


def end(t, status="ok", error=None, output=None):
    dur = (time.perf_counter() - t.start) * 1000
    try:
        if t.calls:
            db.executemany(
                "INSERT INTO calls(trace_id, seq, depth, module, func, args, result, error, "
                "duration_ms, ts) VALUES(?,?,?,?,?,?,?,?,?,?)",
                [(t.id, c["seq"], c["depth"], c["module"], c["func"], c["args"],
                  c.get("result"), c.get("error"), c.get("duration_ms"), c["ts"])
                 for c in t.calls])
        db.execute("UPDATE traces SET status=?, error=?, output=?, duration_ms=? WHERE id=?",
                   (status, error, dump(output) if output is not None else None, dur, t.id))
    finally:
        _current.reset(t.token)
    file_log.info("trace=%s session=%s status=%s calls=%d %.1fms%s", t.id, t.session_id,
                  status, len(t.calls), dur, f" error={error}" if error else "")


def current_id():
    t = _current.get()
    return t.id if t else None


def logged(fn):
    """Decorator: record this call inside the active trace (no-op outside a trace)."""
    module = fn.__module__.replace("app.", "")
    name = fn.__qualname__
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        sig = None

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        t = _current.get()
        if t is None:
            return fn(*args, **kwargs)
        try:
            bound = sig.bind(*args, **kwargs) if sig else None
            arg_map = dict(bound.arguments) if bound else {"args": args, "kwargs": kwargs}
        except TypeError:
            arg_map = {"args": args, "kwargs": kwargs}
        arg_map.pop("self", None)
        if "ctx" in arg_map:
            arg_map["ctx"] = getattr(arg_map["ctx"], "lang", "?")
        t.seq += 1
        rec = {"seq": t.seq, "depth": t.depth, "module": module, "func": name,
               "args": dump(arg_map), "ts": time.time()}
        t.calls.append(rec)
        t.depth += 1
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            rec["result"] = dump(result)
            return result
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
            raise
        finally:
            t.depth -= 1
            rec["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)

    wrapper.__nm_logged__ = True
    return wrapper

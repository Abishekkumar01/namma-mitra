"""Simulated payment gateway (no real money). A service creates an intent, the chat shows a
"Pay ₹X" button, the browser shows a UPI sheet, and on success the service's on_payment()
issues the receipt/ticket."""
import json
import random
import time

from . import db
from .tracer import logged


@logged
def create(session_id, service, purpose, amount, ref, context=None):
    pid = "PAY" + time.strftime("%y%m%d") + "".join(str(random.randint(0, 9)) for _ in range(6))
    db.execute("INSERT INTO payments(id, session_id, service, purpose, amount, ref, context, status, "
               "created_at) VALUES(?,?,?,?,?,?,?,?,?)",
               (pid, session_id, service, purpose, float(amount), ref,
                json.dumps(context or {}, ensure_ascii=False), "pending", time.time()))
    return pid


@logged
def get(pid):
    p = db.one("SELECT * FROM payments WHERE id=?", (pid,))
    if p:
        p["context"] = json.loads(p.get("context") or "{}")
    return p


@logged
def mark_paid(pid, method):
    txn = "".join(str(random.randint(0, 9)) for _ in range(12))
    db.execute("UPDATE payments SET status='paid', method=?, txn_id=?, paid_at=? WHERE id=?",
               (method, txn, time.time(), pid))
    return get(pid)

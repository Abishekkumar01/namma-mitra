"""HTTP layer (standard library only - nothing to pip install).

POST /api/session        {session_id}                         -> history + ui strings
POST /api/message        {session_id, text, payload?}         -> bot messages
POST /api/panel/open     {session_id, service?, prefill?}     -> panel spec
POST /api/panel/service  {session_id, service}                -> fields for a service
POST /api/panel/submit   {session_id, service, screen, values}-> close+messages | next screen | errors
POST /api/payment/info   {session_id, payment_id}
POST /api/payment/pay    {session_id, payment_id, method}     -> receipt messages
GET  /doc/<id>           printable document
GET  /logs               trace viewer;  GET /api/traces, /api/logs?trace=N
GET  /api/health

Every POST runs inside a trace (tracer.begin/end). Any exception is caught, logged with
its traceback, the session flow is reset and the user gets a friendly message - the demo
never hangs on a crash.
"""
import json
import mimetypes
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config, db, docs, engine, pdf, tracer
from .i18n import t, ui_strings

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def _persist(session_id, direction, msg, trace_id):
    payload = {k: v for k, v in msg.items() if k not in ("dir", "trace_id", "ts")}
    db.execute("INSERT INTO messages(session_id, dir, payload, trace_id, ts) VALUES(?,?,?,?,?)",
               (session_id, direction, json.dumps(payload, ensure_ascii=False), trace_id, time.time()))


def _inbound_for(route, body):
    if route == "/api/message":
        if body.get("payload"):
            return {"type": "text", "text": body.get("label") or body.get("text") or "", "button": True}
        return {"type": "text", "text": body.get("text", "")}
    return None


ROUTES = {
    "/api/session": lambda b: engine.start_session(b["session_id"]),
    "/api/message": lambda b: engine.handle_message(b["session_id"], b.get("text", ""), b.get("payload")),
    "/api/panel/open": lambda b: engine.panel_open(b["session_id"], b.get("service"), b.get("prefill")),
    "/api/panel/service": lambda b: engine.panel_service(b["session_id"], b["service"]),
    "/api/panel/submit": lambda b: engine.panel_submit(b["session_id"], b["service"], b.get("screen", "main"), b.get("values") or {}),
    "/api/payment/info": lambda b: engine.payment_info(b["session_id"], b["payment_id"]),
    "/api/payment/pay": lambda b: engine.pay(b["session_id"], b["payment_id"], b.get("method", "UPI")),
}


def run_route(route, body):
    sid = str(body.get("session_id") or "anon")[:64]
    body["session_id"] = sid
    tr = tracer.begin(sid, route.replace("/api/", ""), body)
    now = time.time()
    try:
        inbound = _inbound_for(route, body)
        if inbound and inbound.get("text"):
            _persist(sid, "in", inbound, tr.id)
        result = ROUTES[route](body) or {}
        if result.get("inbound"):
            _persist(sid, "in", result["inbound"], tr.id)
            result["inbound"].update(trace_id=tr.id, ts=now)
        for m in result.get("messages", []):
            m["trace_id"], m["ts"], m["dir"] = tr.id, now, "out"
            _persist(sid, "out", m, tr.id)
        lang, ui = engine.ui_for(sid)
        result.update(trace_id=tr.id, lang=lang, ui=ui, services=engine.services_for(sid))
        tracer.end(tr, "ok", output={"n_messages": len(result.get("messages", [])),
                                     "keys": sorted(k for k in result if k != "ui")})
        return 200, result
    except Exception as e:
        tb = traceback.format_exc()
        tracer.file_log.error("trace=%s %s", tr.id, tb)
        try:
            s = engine.load_session(sid)
            engine.reset_flow(s)
            engine.save_session(s)
            lang = s["lang"]
        except Exception:
            lang = config.DEFAULT_LANG
        msg = {"type": "text", "text": t("error_generic", lang) + f"\n\n_ref #{tr.id}_",
               "buttons": [{"label": t("main_menu", lang), "payload": "menu"}],
               "trace_id": tr.id, "ts": now, "dir": "out"}
        try:
            _persist(sid, "out", msg, tr.id)
        except Exception:
            pass
        tracer.end(tr, "error", error=f"{type(e).__name__}: {e}\n{tb[-1500:]}")
        return 200, {"messages": [msg], "close": True, "trace_id": tr.id, "lang": lang,
                     "ui": ui_strings(lang), "error": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "NammaMitra/" + config.APP_VERSION

    def log_message(self, fmt, *args):
        tracer.file_log.debug("http " + fmt, *args)

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else (
            json.dumps(body, ensure_ascii=False).encode("utf-8") if not isinstance(body, str) else body.encode("utf-8"))
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _static(self, rel):
        root = config.STATIC_DIR.resolve()
        path = (root / rel).resolve()
        if root not in path.parents and path != root or not path.is_file():
            return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self._send(200, path.read_bytes(), ctype)

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        try:
            if p in ("/", "/index.html"):
                return self._static("index.html")
            if p == "/logs":
                return self._static("logs.html")
            if p.startswith("/static/"):
                return self._static(p[len("/static/"):])
            if p.startswith("/doc/"):
                did = p[len("/doc/"):]
                if did.endswith(".pdf"):
                    did = did[:-4]
                    doc = docs.get(did)
                    html = docs.render(did, for_pdf=True)
                    path = pdf.render_pdf(did, html) if html else None
                    if not path:
                        self.send_response(302)
                        self.send_header("Location", f"/doc/{did}")
                        self.end_headers()
                        return
                    return self._send(200, path.read_bytes(), "application/pdf",
                                      {"Content-Disposition": f'inline; filename="{doc["filename"]}"'})
                html = docs.render(did)
                return self._send(200 if html else 404, html or "<h3>Document not found</h3>", "text/html; charset=utf-8")
            if p == "/api/health":
                return self._send(200, {"ok": True, "version": config.APP_VERSION})
            if p == "/api/traces":
                limit = int(q.get("limit", ["100"])[0])
                sid = q.get("session", [None])[0]
                sql = "SELECT id, session_id, kind, input, status, error, duration_ms, started_at FROM traces"
                rows = (db.query(sql + " WHERE session_id=? ORDER BY id DESC LIMIT ?", (sid, limit)) if sid
                        else db.query(sql + " ORDER BY id DESC LIMIT ?", (limit,)))
                return self._send(200, {"traces": rows})
            if p == "/api/logs":
                tid = int(q.get("trace", ["0"])[0])
                trace = db.one("SELECT * FROM traces WHERE id=?", (tid,))
                calls = db.query("SELECT seq, depth, module, func, args, result, error, duration_ms FROM calls "
                                 "WHERE trace_id=? ORDER BY seq", (tid,))
                msgs = db.query("SELECT dir, payload FROM messages WHERE trace_id=? ORDER BY id", (tid,))
                return self._send(200, {"trace": trace, "calls": calls, "messages": msgs})
            if p == "/favicon.ico":
                return self._static("img/gok_logo.jpg")
            self._send(404, {"error": "not found"})
        except Exception as e:
            tracer.file_log.error("GET %s failed: %s", p, traceback.format_exc())
            self._send(500, {"error": str(e)})

    def do_POST(self):
        route = urlparse(self.path).path
        if route not in ROUTES:
            return self._send(404, {"error": "unknown route"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}
        except Exception:
            return self._send(400, {"error": "invalid json"})
        code, result = run_route(route, body)
        self._send(code, result)


def serve(host, port):
    db.init()
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd

"""Conversation engine - the brain. Pure Python, no HTTP.

Entry points (each called inside a trace by server.py):
  start_session(sid)                        -> session + history
  handle_message(sid, text, payload)        -> chat text or quick-reply button
  panel_open / panel_service / panel_submit -> the right-side Flow panel
  pay(sid, payment_id, method)              -> simulated payment completion

Session state machine
  idle       : waiting; free text -> command / service intent / fallback
  text_flow  : asking the fields of a service one at a time in chat (flow JSON in session)
  (panel multi-screen state is also kept in session.flow with mode='panel')
"""
import json
import time

from . import config, db, nlu, payments, ui
from . import flowkit as fk
from .i18n import STR, t, tr, ui_strings
from .services import REGISTRY, all_services, get
from .services.base import Ctx, Errors, Reply, Screen
from .tracer import logged

LOGO = "/static/img/gok_logo.jpg"


# ---- session -------------------------------------------------------------

@logged
def load_session(sid):
    s = db.one("SELECT * FROM sessions WHERE id=?", (sid,))
    if not s:
        ts = time.time()
        db.execute("INSERT INTO sessions(id, lang, state, flow, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                   (sid, config.DEFAULT_LANG, "idle", None, ts, ts))
        s = {"id": sid, "lang": config.DEFAULT_LANG, "state": "idle", "flow": None}
    s["flow"] = json.loads(s["flow"]) if s.get("flow") else None
    return s


@logged
def save_session(s):
    db.execute("UPDATE sessions SET lang=?, state=?, flow=?, updated_at=? WHERE id=?",
               (s["lang"], s["state"], json.dumps(s["flow"], ensure_ascii=False) if s["flow"] else None,
                time.time(), s["id"]))


def reset_flow(s):
    s["state"], s["flow"] = "idle", None


def ctx_of(s):
    return Ctx(s["id"], s["lang"])


@logged
def start_session(sid):
    s = load_session(sid)
    rows = db.query("SELECT dir, payload, trace_id, ts FROM messages WHERE session_id=? ORDER BY id", (sid,))
    history = []
    for r in rows:
        m = json.loads(r["payload"])
        m.update(dir=r["dir"], trace_id=r["trace_id"], ts=r["ts"])
        history.append(m)
    return {"session_id": sid, "lang": s["lang"], "history": history}


# ---- welcome ---------------------------------------------------------------

@logged
def welcome(ctx):
    return [ui.image(LOGO, t("welcome", ctx.lang), footer=t("welcome_hint", ctx.lang),
                     cta=ui.cta_panel(t("choose_service", ctx.lang)))]


# ---- chat ---------------------------------------------------------------

@logged
def handle_message(sid, text, payload=None):
    s = load_session(sid)
    if payload:
        out = _handle_payload(s, payload)
    else:
        out = _handle_text(s, text or "")
    save_session(s)
    return {"messages": out}


def _handle_payload(s, payload):
    ctx = ctx_of(s)
    if payload == "menu":
        reset_flow(s)
        return welcome(ctx)
    if payload.startswith("svc:"):
        _, key, arg = payload.split(":", 2)
        svc = get(key)
        if svc:
            reset_flow(s)
            outcome = svc.on_button(ctx, arg)
            if isinstance(outcome, Reply):
                return outcome.messages
            if isinstance(outcome, Errors):
                return [ui.text("\n".join(ctx.t(v) for v in outcome.errors.values()),
                                buttons=[ui.button(ctx.s("main_menu"), "menu")])]
    return _fallback(ctx)


def _handle_text(s, text):
    ctx = ctx_of(s)
    cmd = nlu.command(text)
    if cmd in ("lang_en", "lang_kn"):
        s["lang"] = "en" if cmd == "lang_en" else "kn"
        reset_flow(s)
        ctx = ctx_of(s)
        return [ui.system(t("lang_changed", ctx.lang))] + welcome(ctx)
    if cmd == "abort":
        if s["state"] == "text_flow":
            reset_flow(s)
            return [ui.text(t("flow_aborted", ctx.lang))]
        return [ui.text(t("nothing_to_abort", ctx.lang))]
    if cmd == "greet":
        reset_flow(s)
        return welcome(ctx)
    if s["state"] == "text_flow" and s.get("flow"):
        return _text_flow_reply(s, text)
    key, score = nlu.detect_service(text)
    if key:
        return _start_text_flow(s, get(key), text)
    return _fallback(ctx)


def _fallback(ctx):
    return [ui.text(t("fallback", ctx.lang), cta=ui.cta_panel(t("choose_service", ctx.lang)))]


# ---- text-mode flow --------------------------------------------------------

@logged
def _start_text_flow(s, svc, text):
    ctx = ctx_of(s)
    fields = svc.fields(ctx)
    by_id = {f["id"]: f for f in fields}
    prefill = {}
    for k, v in (svc.prefill(text) or {}).items():
        if k in by_id:
            clean, err = fk.validate(by_id[k], v, ctx.lang)
            if not err:
                prefill[k] = clean
    flow = {"mode": "text", "service": svc.key, "screen": "main", "fields": fields,
            "values": prefill, "data": {}, "asking": None, "shown": []}
    intro = ui.text(t("intent_start", ctx.lang, title=ctx.t(svc.title)),
                    cta=ui.cta_panel(t("open_form", ctx.lang), svc.key, prefill))
    return [intro] + _advance(s, flow)


@logged
def _advance(s, flow):
    """Ask the next unanswered visible field, or submit when all are answered."""
    ctx = ctx_of(s)
    out = []
    for _ in range(10):  # bounded: a submit can return a new Screen
        visible = fk.visible_fields(flow["fields"], flow["values"])
        pending = None
        for f in visible:
            if f["type"] == "info":
                if f["id"] not in flow["shown"]:
                    out.append(ui.text(ctx.t(f["text"])))
                    flow["shown"].append(f["id"])
                continue
            if f["id"] not in flow["values"]:
                pending = f
                break
        if pending:
            flow["asking"] = pending["id"]
            s["state"], s["flow"] = "text_flow", flow
            out.append(ui.text(fk.prompt_for(pending, ctx.lang), footer=t("abort_hint", ctx.lang)))
            return out
        svc = get(flow["service"])
        clean, errors = fk.validate_all(flow["fields"], flow["values"], ctx.lang)
        if errors:
            for k in errors:
                flow["values"].pop(k, None)
            continue
        outcome = svc.submit(ctx, flow["screen"], clean, flow["data"])
        if isinstance(outcome, Reply):
            reset_flow(s)
            return out + outcome.messages
        if isinstance(outcome, Screen):
            flow = {"mode": "text", "service": svc.key, "screen": outcome.id, "fields": outcome.fields,
                    "values": {}, "data": outcome.data, "asking": None, "shown": []}
            out.append(ui.text(f"*{ctx.t(outcome.title)}*"))
            continue
        if isinstance(outcome, Errors):
            field_ids = {f["id"] for f in flow["fields"]}
            msgs = []
            for k, v in outcome.errors.items():
                msgs.append(ctx.t(v))
                flow["values"].pop(k, None)
            out.append(ui.text("\n".join(msgs)))
            if not any(k in field_ids for k in outcome.errors):
                reset_flow(s)
                return out
            continue
        reset_flow(s)
        return out
    reset_flow(s)
    return out + [ui.text(t("error_generic", ctx.lang))]


@logged
def _text_flow_reply(s, text):
    ctx = ctx_of(s)
    flow = s["flow"]
    field = next((f for f in flow["fields"] if f["id"] == flow.get("asking")), None)
    if not field:
        reset_flow(s)
        return _fallback(ctx)
    raw = text.strip()
    prompt = fk.prompt_for(field, ctx.lang)
    if not field.get("required", True) and raw.upper() in ("SKIP", "ಬಿಡಿ", "-"):
        value = ""
    elif field["type"] in ("radio", "dropdown"):
        value = fk.match_option(field, raw, ctx.lang)
        if value is None:
            return [ui.text(t("invalid_option", ctx.lang) + "\n\n" + prompt, footer=t("abort_hint", ctx.lang))]
    else:
        value, err = fk.validate(field, raw, ctx.lang)
        if err:
            return [ui.text(err + "\n\n" + prompt, footer=t("abort_hint", ctx.lang))]
    flow["values"][field["id"]] = value
    return _advance(s, flow)


# ---- panel (WhatsApp Flow) -------------------------------------------------

def _service_list(ctx):
    return [{"key": svc.key, "icon": svc.icon, "title": ctx.t(svc.title), "subtitle": ctx.t(svc.subtitle),
             "dept": ctx.t(svc.dept), "sevaone": [ctx.t(x) for x in svc.sevaone]}
            for svc in all_services()]


@logged
def panel_open(sid, service=None, prefill=None):
    s = load_session(sid)
    ctx = ctx_of(s)
    spec = {"screen": "main", "services": _service_list(ctx), "service": None, "fields": [], "values": {}}
    svc = get(service) if service else None
    if svc:
        spec.update(service=svc.key, fields=fk.localize_fields(svc.fields(ctx), ctx.lang), values=prefill or {})
    return {"panel": spec}


@logged
def panel_service(sid, service):
    s = load_session(sid)
    ctx = ctx_of(s)
    svc = get(service)
    if not svc:
        return {"fields": []}
    return {"fields": fk.localize_fields(svc.fields(ctx), ctx.lang)}


@logged
def panel_submit(sid, service, screen, values):
    s = load_session(sid)
    ctx = ctx_of(s)
    svc = get(service)
    if not svc:
        return {"errors": {"_": t("select_option", ctx.lang)}}
    if screen == "main":
        fields, data = svc.fields(ctx), {}
    else:
        flow = s.get("flow") or {}
        if flow.get("mode") != "panel" or flow.get("service") != service or flow.get("screen") != screen:
            reset_flow(s)
            save_session(s)
            return {"close": True, "messages": [ui.text(t("error_generic", ctx.lang))]}
        fields, data = flow["fields"], flow["data"]
    clean, errors = fk.validate_all(fields, values or {}, ctx.lang)
    if errors:
        return {"errors": errors}
    prior = [] if screen == "main" else list((s.get("flow") or {}).get("answers") or [])
    answers = prior + _summarize(fields, clean, ctx.lang)
    outcome = svc.submit(ctx, screen, clean, data)
    result = _apply_panel_outcome(s, svc, outcome, answers)
    save_session(s)
    return result


def _summarize(fields, clean, lang):
    """Label/value pairs of what the citizen submitted, for the 'View response' sheet."""
    out = []
    for f in fk.visible_fields(fields, clean):
        if f["type"] == "info" or f["id"] not in clean or clean[f["id"]] in ("", None):
            continue
        v = clean[f["id"]]
        if f["type"] in ("radio", "dropdown"):
            v = fk.option_title(f, v, lang)
        elif f["type"] == "date":
            v = "-".join(reversed(str(v).split("-")))
        elif "aadhaar" in f["id"]:
            v = "XXXX XXXX " + str(v)[-4:]
        out.append({"label": tr(f["label"], lang), "value": str(v)})
    return out


def _apply_panel_outcome(s, svc, outcome, answers=None):
    ctx = ctx_of(s)
    if isinstance(outcome, Reply):
        reset_flow(s)
        inbound = {"type": "flow_response", "text": ctx.t(svc.title), "sub": t("form_submitted", ctx.lang),
                   "answers": answers or []}
        return {"close": True, "inbound": inbound, "messages": outcome.messages}
    if isinstance(outcome, Screen):
        s["state"] = "idle"
        s["flow"] = {"mode": "panel", "service": svc.key, "screen": outcome.id,
                     "fields": outcome.fields, "data": outcome.data, "answers": answers or []}
        return {"panel": {"screen": outcome.id, "service": svc.key, "title": ctx.t(outcome.title),
                          "fields": fk.localize_fields(outcome.fields, ctx.lang),
                          "submit": ctx.t(outcome.submit) if outcome.submit else None}}
    if isinstance(outcome, Errors):
        return {"errors": {k: ctx.t(v) for k, v in outcome.errors.items()}}
    reset_flow(s)
    return {"close": True, "messages": [ui.text(t("error_generic", ctx.lang))]}


# ---- payments --------------------------------------------------------------

@logged
def pay(sid, payment_id, method="UPI"):
    s = load_session(sid)
    ctx = ctx_of(s)
    p = payments.get(payment_id)
    if not p:
        return {"messages": [ui.text(t("payment_missing", ctx.lang))]}
    if p["status"] == "paid":
        return {"messages": [ui.text(t("already_paid", ctx.lang))]}
    p = payments.mark_paid(payment_id, method)
    svc = get(p["service"])
    return {"messages": svc.on_payment(ctx, p) if svc else [], "paid": True}


@logged
def payment_info(sid, payment_id):
    p = payments.get(payment_id)
    if not p:
        return {"payment": None}
    return {"payment": {"id": p["id"], "amount": p["amount"], "purpose": p["purpose"], "status": p["status"]}}


def ui_for(sid):
    s = load_session(sid)
    return s["lang"], ui_strings(s["lang"])


def services_for(sid):
    """Service list in the session's current language (keeps the side panel in step with the chat)."""
    return _service_list(ctx_of(load_session(sid)))

"""Declarative form fields - the equivalent of a WhatsApp Flow screen.

One field list drives BOTH interaction modes (exactly the Mana Mitra split):
  * Panel mode  - the right-side "Service Selection" form (browser renders all visible fields)
  * Text mode   - free-text entry ("i want to pay electricity bill") asks one field at a time

Field dict keys
  id, type (radio|dropdown|text|textarea|number|date|info), label, required,
  show_if {other_field: value | [values]}  -> field is visible only when all match,
  placeholder, helper, pattern (regex checked after transform), error,
  transform (upper|digits|upper_nospace), min_len, max_len, min, max,
  min_days/max_days (date window relative to today), options [{id,title,description}], text (info)
"""
import datetime as _dt
import difflib
import re

from .i18n import L, STR, tr, loc
from .tracer import logged

# ---- builders -------------------------------------------------------------


def opt(id, title, description=None):
    o = {"id": id, "title": title}
    if description is not None:
        o["description"] = description
    return o


def _field(type_, id, label, show_if=None, required=True, **kw):
    f = {"id": id, "type": type_, "label": label, "required": required}
    if show_if:
        f["show_if"] = show_if
    f.update({k: v for k, v in kw.items() if v is not None})
    return f


def radio(id, label, options, show_if=None, required=True, **kw):
    return _field("radio", id, label, show_if, required, options=options, **kw)


def dropdown(id, label, options, show_if=None, required=True, **kw):
    return _field("dropdown", id, label, show_if, required, options=options, **kw)


TITLE_FIELDS = {"name", "father", "taluk", "hobli", "village", "pname", "dname", "gotra", "caste"}


def text(id, label, show_if=None, required=True, placeholder=None, pattern=None, error=None,
         transform=None, min_len=None, max_len=None, helper=None, input_mode=None):
    if transform is None and id in TITLE_FIELDS:
        transform = "title"          # "thunkkur" -> "Thunkkur", "h d kote" -> "H D Kote"
    return _field("text", id, label, show_if, required, placeholder=placeholder, pattern=pattern,
                  error=error, transform=transform, min_len=min_len, max_len=max_len,
                  helper=helper, input_mode=input_mode)


def textarea(id, label, show_if=None, required=True, placeholder=None, min_len=None, max_len=500):
    return _field("textarea", id, label, show_if, required, placeholder=placeholder,
                  min_len=min_len, max_len=max_len)


def number(id, label, min=None, max=None, show_if=None, required=True, placeholder=None, helper=None, error=None):
    return _field("number", id, label, show_if, required, min=min, max=max,
                  placeholder=placeholder, helper=helper, error=error)


def date(id, label, min_days=0, max_days=30, show_if=None, required=True, helper=None, error=None):
    return _field("date", id, label, show_if, required, min_days=min_days, max_days=max_days,
                  helper=helper, error=error)


def info(id, text_, show_if=None):
    return _field("info", id, L(""), show_if, False, text=text_)


# ---- visibility -----------------------------------------------------------


def is_visible(field, values, by_id):
    cond = field.get("show_if")
    if not cond:
        return True
    for ref, expected in cond.items():
        parent = by_id.get(ref)
        if parent is not None and not is_visible(parent, values, by_id):
            return False
        val = values.get(ref)
        allowed = expected if isinstance(expected, list) else [expected]
        if val not in allowed:
            return False
    return True


def visible_fields(fields, values):
    by_id = {f["id"]: f for f in fields}
    return [f for f in fields if is_visible(f, values, by_id)]


# ---- validation -----------------------------------------------------------


def _today():
    return _dt.date.today()


def apply_transform(field, raw):
    s = str(raw).strip()
    tf = field.get("transform")
    if tf == "upper":
        s = s.upper()
    elif tf == "upper_nospace":
        s = re.sub(r"[\s\-]", "", s.upper())
    elif tf == "digits":
        s = re.sub(r"[\s\-]", "", s)
    elif tf == "title":
        s = " ".join(w if not w.isascii() else (w.upper() if len(w) <= 2 else w.capitalize()) for w in s.split())
    return s


def parse_date(raw):
    s = str(raw).strip().lower()
    today = _today()
    if s in ("today", "ಇಂದು"):
        return today
    if s in ("tomorrow", "ನಾಳೆ"):
        return today + _dt.timedelta(days=1)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def date_window(field):
    today = _today()
    return (today + _dt.timedelta(days=field.get("min_days", 0)),
            today + _dt.timedelta(days=field.get("max_days", 30)))


def validate(field, raw, lang):
    """Return (clean_value, error_or_None). Options are matched by id."""
    ftype = field["type"]
    empty = raw is None or str(raw).strip() == ""
    if empty:
        if field.get("required", True) and ftype != "info":
            key = "select_option" if ftype in ("radio", "dropdown") else "required"
            return None, tr(STR[key], lang)
        return "", None

    if ftype in ("radio", "dropdown"):
        ids = [o["id"] for o in field.get("options", [])]
        if raw not in ids:
            return None, tr(STR["select_option"], lang)
        return raw, None

    if ftype == "number":
        try:
            n = int(float(str(raw).replace(",", "").strip()))
        except ValueError:
            return None, tr(STR["invalid_format"], lang)
        lo, hi = field.get("min"), field.get("max")
        if (lo is not None and n < lo) or (hi is not None and n > hi):
            return None, tr(field.get("error") or STR["number_range"], lang).format(min=lo, max=hi)
        return n, None

    if ftype == "date":
        d = parse_date(raw)
        if not d:
            return None, tr(STR["date_invalid"], lang)
        lo, hi = date_window(field)
        if d < lo or d > hi:
            return None, tr(field.get("error") or STR["date_range"], lang).format(
                a=lo.strftime("%d-%m-%Y"), b=hi.strftime("%d-%m-%Y"))
        return d.isoformat(), None

    s = apply_transform(field, raw)
    if field.get("min_len") and len(s) < field["min_len"]:
        return None, tr(STR["min_length"], lang).format(n=field["min_len"])
    if field.get("max_len") and len(s) > field["max_len"]:
        s = s[: field["max_len"]]
    if field.get("pattern") and not re.fullmatch(field["pattern"], s):
        return None, tr(field.get("error") or STR["invalid_format"], lang)
    return s, None


@logged
def validate_all(fields, values, lang):
    clean, errors = {}, {}
    for f in visible_fields(fields, values):
        if f["type"] == "info":
            continue
        v, err = validate(f, values.get(f["id"]), lang)
        if err:
            errors[f["id"]] = err
        else:
            clean[f["id"]] = v
    return clean, errors


# ---- text-mode helpers ----------------------------------------------------


def option_title(field, oid, lang):
    for o in field.get("options", []):
        if o["id"] == oid:
            return tr(o["title"], lang)
    return oid


def match_option(field, reply, lang):
    """Map a chat reply ('2', 'Mysuru', 'ಮೈಸೂರು') to an option id."""
    opts = field.get("options", [])
    s = str(reply).strip()
    if s.isdigit() and 1 <= int(s) <= len(opts):
        return opts[int(s) - 1]["id"]
    low = s.lower()
    titles = {}
    for o in opts:
        for lg in ("en", "kn"):
            t = str(tr(o["title"], lg)).lower()
            titles[t] = o["id"]
            if low and (low == t or (len(low) >= 3 and low in t)):
                return o["id"]
        if low == o["id"].lower():
            return o["id"]
    close = difflib.get_close_matches(low, list(titles.keys()), n=1, cutoff=0.75)
    return titles[close[0]] if close else None


def prompt_for(field, lang):
    """The chat prompt for one field in text mode."""
    label = tr(field["label"], lang)
    lines = [f"*{label}*"]
    if field["type"] in ("radio", "dropdown"):
        lines.append("")
        for i, o in enumerate(field.get("options", []), 1):
            desc = tr(o.get("description"), lang)
            lines.append(f"{i}. {tr(o['title'], lang)}" + (f" - _{desc}_" if desc else ""))
        lines.append("")
        lines.append(tr(STR["reply_number"], lang))
    else:
        if field.get("helper"):
            lines.append(f"_{tr(field['helper'], lang)}_")
        if field.get("placeholder"):
            ex = str(tr(field["placeholder"], lang))
            already = ex.lower().startswith("e.g.") or ex.startswith("ಉದಾ")
            lines.append(ex if already else ("e.g. " if lang == "en" else "ಉದಾ: ") + ex)
        if field["type"] == "date":
            lo, _ = date_window(field)
            lines.append(tr(STR["date_hint"], lang).format(ex=lo.strftime("%d-%m-%Y")))
        if field["type"] == "number" and field.get("min") is not None:
            lines.append(f"({field.get('min')} - {field.get('max')})")
    if not field.get("required", True):
        lines.append(tr(STR["optional_skip"], lang))
    return "\n".join(lines)


def localize_fields(fields, lang):
    out = []
    for f in fields:
        lf = loc(f, lang)
        if f["type"] == "date":
            lo, hi = date_window(f)
            lf["min_date"], lf["max_date"] = lo.isoformat(), hi.isoformat()
        out.append(lf)
    return out

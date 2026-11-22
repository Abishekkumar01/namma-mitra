"""Service framework.

A Service declares:
  key, order, icon, title, subtitle, keywords      -> menu entry + free-text routing
  fields(ctx)                                     -> first screen (flowkit fields)
  submit(ctx, screen, values, data)               -> Outcome
  on_payment(ctx, payment)                        -> list of messages after a successful payment
  on_button(ctx, arg)                             -> Outcome for quick-reply buttons "svc:<key>:<arg>"
  prefill(text)                                   -> values guessed from free text ("income certificate")

Outcomes
  Reply(*messages)          close the panel / end the text flow, post messages
  Screen(id, title, fields, data)  show another screen (multi-step flow); data is carried forward
  Errors({field: message})  stay on the screen, show inline errors (or re-ask in text mode)

Every public method of every subclass is wrapped with @logged automatically.
"""
import time

from .. import config, ui
from ..i18n import L, STR, tr
from ..tracer import logged


class Reply:
    def __init__(self, *messages):
        self.messages = [m for m in messages if m]

    def __log__(self):
        return {"Reply": [m.get("type") + ":" + str(m.get("text", ""))[:80] for m in self.messages]}


class Screen:
    def __init__(self, id, title, fields, data=None, submit=None):
        self.id, self.title, self.fields, self.data, self.submit = id, title, fields, data or {}, submit

    def __log__(self):
        return {"Screen": self.id, "fields": [f["id"] for f in self.fields]}


class Errors:
    def __init__(self, errors):
        self.errors = errors

    def __log__(self):
        return {"Errors": {k: tr(v, "en") for k, v in self.errors.items()}}


class Ctx:
    def __init__(self, session_id, lang):
        self.session_id, self.lang = session_id, lang

    def t(self, obj):
        return tr(obj, self.lang)

    def s(self, key, **kw):
        v = tr(STR[key], self.lang)
        return v.format(**kw) if kw else v

    @property
    def kn(self):
        return self.lang == "kn"

    def __log__(self):
        return self.lang


class Service:
    key = ""
    order = 100
    icon = ""
    title = L("")
    subtitle = L("")
    dept = L("")          # Seva One department name (as listed on sevaone.karnataka.gov.in)
    sevaone = []          # exact Seva One service names this module covers
    keywords = []

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        for name, val in list(cls.__dict__.items()):
            if callable(val) and not name.startswith("__") and not getattr(val, "__nm_logged__", False):
                setattr(cls, name, logged(val))

    # --- overridable -----------------------------------------------------
    def fields(self, ctx):
        return []

    def prefill(self, text):
        return {}

    def submit(self, ctx, screen, values, data):
        raise NotImplementedError

    def on_payment(self, ctx, payment):
        return []

    def on_button(self, ctx, arg):
        return None

    # --- helpers shared by services ---------------------------------------
    def menu_buttons(self, ctx, *extra):
        return list(extra) + [ui.button(ctx.s("main_menu"), "menu")]

    def btn(self, label, arg):
        return ui.button(label, f"svc:{self.key}:{arg}")


def masked_aadhaar(a):
    return "XXXX XXXX " + str(a)[-4:]


def stage_from_elapsed(created_at, n_stages, start=0):
    """Index of current stage for objects created during the demo."""
    elapsed = time.time() - (created_at or time.time())
    return min(n_stages - 1, start + int(elapsed // config.STAGE_SECONDS))


def timeline(ctx, stages, current, dates=None):
    """done / current / pending lines."""
    lines = []
    for i, st in enumerate(stages):
        mark = "✔" if i < current or (i == current == len(stages) - 1) else ("▸" if i == current else "○")
        d = f"  _{dates[i]}_" if dates and i <= current and dates[i] else ""
        lines.append(f"{mark} {ctx.t(st)}{d}")
    return "\n".join(lines)

"""Builders for outgoing chat messages (the JSON the browser renders).

Message shape:
  {type: text|image|system|document|flow_response, text, image, footer,
   cta: {label, action:{kind: panel|pay|link, ...}},
   buttons: [{label, payload}],      # WhatsApp quick-reply buttons
   doc: {id, name, meta}}
Text supports WhatsApp formatting: *bold*, _italic_, ~strike~, ```mono```.
"""


def text(body, buttons=None, cta=None, footer=None):
    m = {"type": "text", "text": body}
    if footer:
        m["footer"] = footer
    if cta:
        m["cta"] = cta
    if buttons:
        m["buttons"] = buttons
    return m


def image(src, caption, footer=None, cta=None):
    m = {"type": "image", "image": src, "text": caption}
    if footer:
        m["footer"] = footer
    if cta:
        m["cta"] = cta
    return m


def system(body):
    return {"type": "system", "text": body}


def document(doc_id, filename, caption=None, meta="1 page · PDF", buttons=None):
    m = {"type": "document", "doc": {"id": doc_id, "name": filename, "meta": meta}}
    if caption:
        m["text"] = caption
    if buttons:
        m["buttons"] = buttons
    return m


def button(label, payload):
    return {"label": label, "payload": payload}


def cta_panel(label, service=None, prefill=None):
    return {"label": label, "icon": "list",
            "action": {"kind": "panel", "service": service, "prefill": prefill or {}}}


def cta_pay(label, payment_id):
    return {"label": label, "icon": "pay", "action": {"kind": "pay", "payment_id": payment_id}}

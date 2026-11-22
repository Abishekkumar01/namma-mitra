"""Official documents (certificates, rank cards, RTC, e-tickets, receipts).

A service calls create(...) with localised content. The chat shows a WhatsApp document bubble.
  /doc/<id>      printable A4 HTML page (with a "Download PDF" button)
  /doc/<id>.pdf  real PDF produced by headless Chrome/Edge (see pdf.py)

data = {
  dept, dept_sub, title, subtitle, ref_label, ref, lang, place,
  sections: [ {heading, rows:[[k,v],...]} | {heading, table:{cols:[...], rows:[[...]]}} | {heading, text} ],
  notes: [str], signatory: {name, designation}, highlight: {label, value}, verify_url
}
"""
import hashlib
import html
import json
import random
import time

from . import db
from .tracer import logged


@logged
def create(session_id, kind, filename, data):
    did = hashlib.sha1(f"{time.time()}{random.random()}".encode()).hexdigest()[:12]
    data.setdefault("issued_at", time.strftime("%d-%m-%Y"))
    data.setdefault("issued_time", time.strftime("%H:%M"))
    db.execute("INSERT INTO docs(id, session_id, kind, filename, data, created_at) VALUES(?,?,?,?,?,?)",
               (did, session_id, kind, filename, json.dumps(data, ensure_ascii=False), time.time()))
    return did


def get(did):
    d = db.one("SELECT * FROM docs WHERE id=?", (did,))
    if d:
        d["data"] = json.loads(d["data"])
    return d


def _qr_svg(seed, size=25, px=3):
    """QR-style verification pattern derived from the document id (not a scannable code)."""
    r = random.Random(seed)
    cells = [[r.random() < 0.47 for _ in range(size)] for _ in range(size)]

    def finder(x0, y0):
        for y in range(7):
            for x in range(7):
                cells[y0 + y][x0 + x] = x in (0, 6) or y in (0, 6) or (2 <= x <= 4 and 2 <= y <= 4)
        for i in range(-1, 8):
            for (x, y) in ((x0 + i, y0 - 1), (x0 + i, y0 + 7), (x0 - 1, y0 + i), (x0 + 7, y0 + i)):
                if 0 <= x < size and 0 <= y < size:
                    cells[y][x] = False

    finder(0, 0), finder(size - 7, 0), finder(0, size - 7)
    rects = "".join(f'<rect x="{x * px}" y="{y * px}" width="{px}" height="{px}"/>'
                    for y in range(size) for x in range(size) if cells[y][x])
    dim = size * px
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{dim}" height="{dim}" viewBox="0 0 {dim} {dim}" '
            f'fill="#111" shape-rendering="crispEdges">{rects}</svg>')


def _e(s):
    return html.escape(str(s if s is not None else ""))


_LOGO = None


def logo_data_uri():
    """The state seal as a data URI, so the page renders identically in the browser and in headless PDF."""
    global _LOGO
    if _LOGO is None:
        import base64
        from . import config
        p = config.STATIC_DIR / "img" / "gok_logo.jpg"
        _LOGO = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    return _LOGO


def render(did, for_pdf=False):
    d = get(did)
    if not d:
        return None
    x = d["data"]
    lang = x.get("lang", "en")
    kn = lang == "kn"
    secs = []
    for s in x.get("sections", []):
        h = f'<h3>{_e(s.get("heading"))}</h3>' if s.get("heading") else ""
        if "rows" in s:
            body = "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in s["rows"])
            secs.append(f'{h}<table class="kv">{body}</table>')
        elif "table" in s:
            cols = "".join(f"<th>{_e(c)}</th>" for c in s["table"]["cols"])
            rows = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>" for r in s["table"]["rows"])
            secs.append(f'{h}<table class="grid"><thead><tr>{cols}</tr></thead><tbody>{rows}</tbody></table>')
        elif "text" in s:
            secs.append(f'{h}<p class="para">{_e(s["text"])}</p>')
    hl = x.get("highlight")
    highlight = (f'<div class="hl"><span>{_e(hl["label"])}</span><b>{_e(hl["value"])}</b></div>' if hl else "")
    notes = "".join(f"<li>{_e(n)}</li>" for n in x.get("notes", []))
    sig = x.get("signatory") or {}
    place = x.get("place") or ("ಬೆಂಗಳೂರು" if kn else "Bengaluru")
    L_ = (lambda en, k: k if kn else en)
    toolbar = "" if for_pdf else f"""<div class="bar"><span>{_e(d['filename'])}</span>
      <a class="btn" href="/doc/{did}.pdf" target="_blank">{L_('Download PDF', 'PDF ಡೌನ್‌ಲೋಡ್')}</a>
      <button class="btn ghost" onclick="window.print()">{L_('Print', 'ಮುದ್ರಿಸಿ')}</button></div>"""
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(d['filename'])}</title>
<style>
@page {{ size: A4; margin: 0; }}
:root{{--ink:#1a1a1a;--muted:#555;--line:#cfcfcf;--navy:#14365d;--gold:#b8860b;}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:#e8e8e8;font-family:"Segoe UI","Nirmala UI","Noto Sans Kannada","Noto Sans",Arial,sans-serif;color:var(--ink);font-size:12.5px;line-height:1.5}}
.bar{{position:sticky;top:0;z-index:5;background:#14365d;color:#fff;padding:9px 16px;display:flex;align-items:center;gap:10px;font-size:13px}}
.bar span{{flex:1;opacity:.9}}
.btn{{background:#fff;color:#14365d;border:0;border-radius:4px;padding:7px 14px;font-weight:600;font-size:13px;text-decoration:none;cursor:pointer}}
.btn.ghost{{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.6)}}
.page{{width:210mm;min-height:297mm;margin:16px auto;background:#fff;padding:16mm 18mm 14mm;position:relative;box-shadow:0 2px 14px rgba(0,0,0,.18)}}
.frame{{position:absolute;top:9mm;left:9mm;width:192mm;height:279mm;border:1.2px solid var(--navy);pointer-events:none}}
.frame::after{{content:"";position:absolute;top:1.6mm;left:1.6mm;right:1.6mm;bottom:1.6mm;border:.5px solid var(--gold)}}
header{{display:grid;grid-template-columns:70px 1fr 70px;align-items:center;gap:10px;padding-bottom:9px;border-bottom:2px solid var(--navy)}}
header img{{width:68px;height:68px;object-fit:contain}}
header .c{{text-align:center}}
header .k{{font-size:17px;font-weight:700;letter-spacing:.3px}}
header .en{{font-size:13.5px;font-weight:700;letter-spacing:1.6px;color:var(--navy)}}
header .dept{{font-size:13px;font-weight:600;margin-top:4px}}
header .sub{{font-size:11.5px;color:var(--muted)}}
header .motto{{font-size:9.5px;color:var(--muted);letter-spacing:.5px;text-align:center}}
h1{{text-align:center;font-size:18px;margin:16px 0 2px;letter-spacing:1.2px;color:var(--navy)}}
.sub2{{text-align:center;color:var(--muted);font-size:12px;margin-bottom:12px}}
.meta{{display:flex;justify-content:space-between;font-size:12px;margin:6px 0 10px;padding:6px 0;border-top:1px dotted var(--line);border-bottom:1px dotted var(--line)}}
.meta b{{color:var(--navy)}}
h3{{font-size:12px;margin:14px 0 5px;color:var(--navy);text-transform:uppercase;letter-spacing:.8px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
.kv th{{width:40%;text-align:left;background:#f4f6f9;font-weight:600}}
.kv th,.kv td,.grid th,.grid td{{border:1px solid var(--line);padding:5px 8px;vertical-align:top}}
.grid th{{background:var(--navy);color:#fff;font-weight:600;text-align:left}}
.grid tr:nth-child(even) td{{background:#f7f8fa}}
.para{{font-size:13.5px;line-height:1.85;text-align:justify;margin:14px 0}}
.hl{{margin:12px 0;border:1.5px solid var(--navy);padding:9px 14px;display:flex;justify-content:space-between;align-items:center;background:#f4f6f9}}
.hl span{{font-size:12.5px}} .hl b{{font-size:19px;color:var(--navy)}}
ul.notes{{font-size:11px;color:#444;padding-left:16px;margin:12px 0 0}}
.foot{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:26px}}
.qr{{font-size:9.5px;color:var(--muted);line-height:1.3}}
.qr svg{{display:block;margin-bottom:3px}}
.sig{{text-align:right;font-size:12px;min-width:230px}}
.sig .ds{{display:inline-block;text-align:left;border:1px solid #2e7d32;color:#1b5e20;font-size:9.5px;padding:4px 8px;margin-bottom:8px;line-height:1.35;background:#f3faf3}}
.sig b{{display:block;font-size:12.5px}}
.pd{{display:flex;gap:28px;font-size:12px;margin-top:14px}}
.gen{{position:absolute;left:18mm;right:18mm;bottom:11mm;font-size:9px;color:#777;border-top:1px solid var(--line);padding-top:4px;display:flex;justify-content:space-between}}
@media print{{.bar{{display:none}} body{{background:#fff}} .page{{margin:0;box-shadow:none;height:297mm;overflow:hidden}}}}
{'html,body{background:#fff;overflow:hidden;width:210mm;height:297mm} .page{width:210mm;height:297mm;min-height:0;margin:0;box-shadow:none;overflow:hidden;page-break-after:avoid} .frame{display:block}' if for_pdf else ''}
@media (max-width:820px){{.page{{width:auto;margin:8px;padding:14px}} .frame{{display:none}}}}
</style></head><body>{toolbar}
<div class="page"><div class="frame"></div>
<header><img src="{logo_data_uri()}" alt="">
<div class="c"><div class="k">ಕರ್ನಾಟಕ ಸರ್ಕಾರ</div><div class="en">GOVERNMENT OF KARNATAKA</div>
<div class="dept">{_e(x.get('dept'))}</div><div class="sub">{_e(x.get('dept_sub', ''))}</div></div>
<div class="motto">ಸತ್ಯಮೇವ ಜಯತೇ<br>Satyameva Jayate</div></header>
<h1>{_e(x.get('title'))}</h1><div class="sub2">{_e(x.get('subtitle', ''))}</div>
<div class="meta"><span><b>{_e(x.get('ref_label', 'Ref'))}:</b> {_e(x.get('ref'))}</span>
<span><b>{L_('Date', 'ದಿನಾಂಕ')}:</b> {_e(x.get('issued_at'))}</span>
<span><b>{L_('Place', 'ಸ್ಥಳ')}:</b> {_e(place)}</span></div>
{highlight}{''.join(secs)}
{f'<ul class="notes">{notes}</ul>' if notes else ''}
<div class="foot"><div class="qr">{_qr_svg(did)}{L_('Verification code', 'ಪರಿಶೀಲನಾ ಕೋಡ್')}: {did.upper()}<br>{_e(x.get('verify_url', 'sevasindhu.karnataka.gov.in'))}</div>
<div class="sig"><div class="ds">{L_('Digitally signed by', 'ಡಿಜಿಟಲ್ ಸಹಿ')} {_e(sig.get('name', ''))}<br>{L_('Date', 'ದಿನಾಂಕ')}: {_e(x.get('issued_at'))} {_e(x.get('issued_time'))} IST<br>{L_('Reason', 'ಕಾರಣ')}: {L_('Approved', 'ಅನುಮೋದಿತ')}</div>
<b>{_e(sig.get('name', ''))}</b>{_e(sig.get('designation', ''))}</div></div>
<div class="gen"><span>{L_('Computer-generated document issued through Namma Mitra, Government of Karnataka. No physical signature required.', 'ನಮ್ಮ ಮಿತ್ರ, ಕರ್ನಾಟಕ ಸರ್ಕಾರದ ಮೂಲಕ ನೀಡಲಾದ ಗಣಕೀಕೃತ ದಾಖಲೆ. ಭೌತಿಕ ಸಹಿ ಅಗತ್ಯವಿಲ್ಲ.')}</span><span>{L_('Demonstration copy', 'ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ಪ್ರತಿ')}</span></div>
</div></body></html>"""

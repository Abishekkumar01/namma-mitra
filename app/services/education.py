"""Karnataka School Examination and Assessment Board (KSEAB) - marks card services.

Seva One services covered: "Online Marks Card", "Issue of Duplicate Marks Card",
"SSLC Marks card Verification", "II PUC Marks Card Verification".
Online marks card: any well-formed register number produces a repeatable marks statement.
Duplicate marks card: apply -> fee -> acknowledgement -> live status -> duplicate marks card PDF.
"""
import datetime as dt
import time

from .. import db, docs, payments, ui
from .. import flowkit as fk
from ..data import gen
from ..i18n import L
from .base import Errors, Reply, Service, stage_from_elapsed, timeline

FEE = 150
DEPT = L("Karnataka School Examination and Assessment Board (KSEAB)", "ಕರ್ನಾಟಕ ಶಾಲಾ ಪರೀಕ್ಷೆ ಮತ್ತು ಮೌಲ್ಯನಿರ್ಣಯ ಮಂಡಳಿ (KSEAB)")
EXAMS = {"sslc": L("SSLC", "ಎಸ್‌ಎಸ್‌ಎಲ್‌ಸಿ"), "puc": L("II PUC", "ದ್ವಿತೀಯ ಪಿಯುಸಿ")}
YEARS = [fk.opt(str(y), L(str(y))) for y in range(2026, 2015, -1)]
REASONS = {"lost": L("Original lost", "ಮೂಲ ಪ್ರತಿ ಕಳೆದುಹೋಗಿದೆ"), "damaged": L("Original damaged", "ಮೂಲ ಪ್ರತಿ ಹಾಳಾಗಿದೆ"),
           "stolen": L("Original stolen (FIR available)", "ಮೂಲ ಪ್ರತಿ ಕಳವು (ಎಫ್‌ಐಆರ್ ಇದೆ)")}
STAGES = [L("Application submitted", "ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ"),
          L("Fee paid - sent to Board records section", "ಶುಲ್ಕ ಪಾವತಿ - ಮಂಡಳಿ ದಾಖಲೆ ವಿಭಾಗಕ್ಕೆ ರವಾನೆ"),
          L("Register verified against Board records", "ಮಂಡಳಿ ದಾಖಲೆಗಳೊಂದಿಗೆ ನೋಂದಣಿ ಪರಿಶೀಲನೆ"),
          L("Duplicate marks card issued (digitally signed)", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ವಿತರಣೆ (ಡಿಜಿಟಲ್ ಸಹಿ)")]


def _grade_class(pct):
    if pct >= 85:
        return L("DISTINCTION", "ಅತ್ಯುನ್ನತ ಶ್ರೇಣಿ")
    if pct >= 60:
        return L("FIRST CLASS", "ಪ್ರಥಮ ದರ್ಜೆ")
    if pct >= 50:
        return L("SECOND CLASS", "ದ್ವಿತೀಯ ದರ್ಜೆ")
    return L("PASS", "ಉತ್ತೀರ್ಣ")


def result(ctx, exam, reg_no, year):
    """Deterministic marks for a register number. Returns dict with name, marks, totals, combo."""
    r = gen.rng(exam, reg_no)
    name = ctx.t(gen.person(r)["name"])
    skill = r.uniform(0.45, 0.98)
    if exam == "sslc":
        subs = [(L("First Language - Kannada", "ಪ್ರಥಮ ಭಾಷೆ - ಕನ್ನಡ"), 125), (L("Second Language - English", "ದ್ವಿತೀಯ ಭಾಷೆ - ಇಂಗ್ಲಿಷ್"), 100),
                (L("Third Language - Hindi", "ತೃತೀಯ ಭಾಷೆ - ಹಿಂದಿ"), 100), (L("Mathematics", "ಗಣಿತ"), 100),
                (L("Science", "ವಿಜ್ಞಾನ"), 100), (L("Social Science", "ಸಮಾಜ ವಿಜ್ಞಾನ"), 100)]
        combo = None
    else:
        combo = r.choice(["PCMB", "PCMC", "CEBA", "HEPS"])
        core = {"PCMB": [("Physics", "ಭೌತಶಾಸ್ತ್ರ"), ("Chemistry", "ರಸಾಯನಶಾಸ್ತ್ರ"), ("Mathematics", "ಗಣಿತ"), ("Biology", "ಜೀವಶಾಸ್ತ್ರ")],
                "PCMC": [("Physics", "ಭೌತಶಾಸ್ತ್ರ"), ("Chemistry", "ರಸಾಯನಶಾಸ್ತ್ರ"), ("Mathematics", "ಗಣಿತ"), ("Computer Science", "ಗಣಕ ವಿಜ್ಞಾನ")],
                "CEBA": [("Computer Science", "ಗಣಕ ವಿಜ್ಞಾನ"), ("Economics", "ಅರ್ಥಶಾಸ್ತ್ರ"), ("Business Studies", "ವ್ಯವಹಾರ ಅಧ್ಯಯನ"), ("Accountancy", "ಲೆಕ್ಕಶಾಸ್ತ್ರ")],
                "HEPS": [("History", "ಇತಿಹಾಸ"), ("Economics", "ಅರ್ಥಶಾಸ್ತ್ರ"), ("Political Science", "ರಾಜ್ಯಶಾಸ್ತ್ರ"), ("Sociology", "ಸಮಾಜಶಾಸ್ತ್ರ")]}[combo]
        subs = [(L("Kannada", "ಕನ್ನಡ"), 100), (L("English", "ಇಂಗ್ಲಿಷ್"), 100)] + [(L(e, k), 100) for e, k in core]
    marks = []
    for label, mx in subs:
        m = max(int(mx * 0.36), min(mx, round(mx * skill + r.uniform(-12, 8))))
        marks.append((ctx.t(label), m, mx))
    total = sum(m for _, m, _ in marks)
    max_total = sum(mx for _, _, mx in marks)
    pct = round(total / max_total * 100, 2)
    title = (L(f"SSLC Examination, {year}", f"ಎಸ್‌ಎಸ್‌ಎಲ್‌ಸಿ ಪರೀಕ್ಷೆ, {year}") if exam == "sslc"
             else L(f"II PUC Examination, {year}", f"ದ್ವಿತೀಯ ಪಿಯುಸಿ ಪರೀಕ್ಷೆ, {year}"))
    return {"name": name, "marks": marks, "total": total, "max_total": max_total, "pct": pct,
            "cls": ctx.t(_grade_class(pct)), "combo": combo, "title": ctx.t(title), "school": r.randint(1001, 9999)}


class Education(Service):
    key = "education"
    order = 5
    icon = "education"
    title = L("KSEAB Marks Card Services", "KSEAB ಅಂಕಪಟ್ಟಿ ಸೇವೆಗಳು")
    subtitle = L("Online marks card, duplicate marks card (SSLC, II PUC)", "ಆನ್‌ಲೈನ್ ಅಂಕಪಟ್ಟಿ, ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ (SSLC, II PUC)")
    dept = DEPT
    sevaone = [L("Online Marks Card"), L("Issue of Duplicate Marks Card"), L("SSLC Marks card Verification"), L("II PUC Marks Card Verification")]
    keywords = ["marks card", "marks", "sslc", "puc", "result", "results", "kseab", "duplicate marks", "10th", "12th",
                "ಅಂಕಪಟ್ಟಿ", "ಅಂಕ", "ಫಲಿತಾಂಶ", "ಎಸ್‌ಎಸ್‌ಎಲ್‌ಸಿ", "ಪಿಯುಸಿ", "ದ್ವಿಪ್ರತಿ", "ನಕಲು"]

    def fields(self, ctx):
        need_reg = {"action": ["view", "duplicate"]}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("view", L("Online Marks Card", "ಆನ್‌ಲೈನ್ ಅಂಕಪಟ್ಟಿ")),
                fk.opt("duplicate", L("Issue of Duplicate Marks Card", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ವಿತರಣೆ")),
                fk.opt("track", L("Track Duplicate Marks Card Application", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ಅರ್ಜಿ ಸ್ಥಿತಿ"))]),
            fk.radio("exam", L("Select Examination", "ಪರೀಕ್ಷೆ ಆಯ್ಕೆಮಾಡಿ"), [fk.opt(k, v) for k, v in EXAMS.items()], show_if=need_reg),
            fk.dropdown("year", L("Year of Examination", "ಪರೀಕ್ಷೆಯ ವರ್ಷ"), YEARS, show_if=need_reg),
            fk.text("reg_no", L("Register Number", "ನೋಂದಣಿ ಸಂಖ್ಯೆ"), show_if=need_reg, placeholder="2026123456",
                    transform="digits", pattern=r"^\d{6,12}$", input_mode="numeric",
                    error=L("Register number must be 6-12 digits", "ನೋಂದಣಿ ಸಂಖ್ಯೆ 6-12 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.date("dob", L("Date of Birth", "ಜನ್ಮ ದಿನಾಂಕ"), min_days=-365 * 40, max_days=-365 * 13, show_if=need_reg),
            fk.radio("reason", L("Reason for Duplicate", "ದ್ವಿಪ್ರತಿಗೆ ಕಾರಣ"), [fk.opt(k, v) for k, v in REASONS.items()],
                     show_if={"action": "duplicate"}),
            fk.text("app_no", L("Enter Application Number", "ಅರ್ಜಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": "track"},
                    placeholder="KSEAB2611220001", transform="upper_nospace", pattern=r"^KSEAB\d{10}$",
                    error=L("Application number looks like KSEAB2611220001", "ಅರ್ಜಿ ಸಂಖ್ಯೆ KSEAB2611220001 ರೀತಿ ಇರುತ್ತದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        out = {}
        if "duplicate" in t or "ದ್ವಿಪ್ರತಿ" in t or "ನಕಲು" in t:
            out["action"] = "duplicate"
        elif "track" in t or "status" in t or "ಸ್ಥಿತಿ" in t:
            out["action"] = "track"
        else:
            out["action"] = "view"
        if "sslc" in t or "10th" in t or "ಎಸ್‌ಎಸ್‌ಎಲ್‌ಸಿ" in t:
            out["exam"] = "sslc"
        elif "puc" in t or "12th" in t or "ಪಿಯುಸಿ" in t:
            out["exam"] = "puc"
        return out

    def submit(self, ctx, screen, v, data):
        if v["action"] == "track":
            return self.track(ctx, v["app_no"])
        if gen.is_missing(v["reg_no"]):
            return Errors({"reg_no": L("No record found for this Register Number and Date of Birth.",
                                       "ಈ ನೋಂದಣಿ ಸಂಖ್ಯೆ ಮತ್ತು ಜನ್ಮ ದಿನಾಂಕಕ್ಕೆ ದಾಖಲೆ ಕಂಡುಬಂದಿಲ್ಲ.")})
        if v["action"] == "view":
            return self._view(ctx, v["exam"], v["reg_no"], v["dob"], v["year"])
        return self._apply(ctx, v)

    # ---------------------------------------------------------------------
    def _marks_doc(self, ctx, exam, reg_no, dob, year, res, duplicate=None):
        fname = f"{'Duplicate_' if duplicate else ''}{exam.upper()}_{year}_Marks_Card_{reg_no}.pdf"
        rows = [[ctx.t(L("Name", "ಹೆಸರು")), res["name"]], [ctx.t(L("Date of Birth", "ಜನ್ಮ ದಿನಾಂಕ")), gen.dmy(dob)],
                [ctx.t(L("School / College Code", "ಶಾಲೆ / ಕಾಲೇಜು ಸಂಕೇತ")), res["school"]]]
        if res["combo"]:
            rows.append([ctx.t(L("Combination", "ಸಂಯೋಜನೆ")), res["combo"]])
        if duplicate:
            rows.append([ctx.t(L("Duplicate issued against application", "ಅರ್ಜಿ ಆಧಾರದ ಮೇಲೆ ದ್ವಿಪ್ರತಿ ವಿತರಣೆ")), duplicate])
        doc_id = docs.create(ctx.session_id, "marks_card", fname, {
            "lang": ctx.lang, "verify_url": "kseab.karnataka.gov.in",
            "dept": ctx.t(DEPT), "dept_sub": ctx.t(L("Malleshwaram, Bengaluru", "ಮಲ್ಲೇಶ್ವರಂ, ಬೆಂಗಳೂರು")),
            "title": ctx.t(L("DUPLICATE MARKS CARD", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ")) if duplicate else ctx.t(L("MARKS CARD", "ಅಂಕಪಟ್ಟಿ")),
            "subtitle": res["title"], "ref_label": ctx.t(L("Register No", "ನೋಂದಣಿ ಸಂಖ್ಯೆ")), "ref": reg_no,
            "highlight": {"label": ctx.t(L("Result", "ಫಲಿತಾಂಶ")), "value": f"{res['cls']} - {res['pct']:.2f}%"},
            "sections": [{"rows": rows},
                         {"table": {"cols": [ctx.t(L("Subject", "ವಿಷಯ")), ctx.t(L("Marks", "ಅಂಕ")), ctx.t(L("Max", "ಗರಿಷ್ಠ"))],
                                    "rows": [list(m) for m in res["marks"]] + [[ctx.t(L("TOTAL", "ಒಟ್ಟು")), res["total"], res["max_total"]]]}}],
            "notes": [ctx.t(L("Online marks card issued by the Karnataka School Examination and Assessment Board. Verify at kseab.karnataka.gov.in.",
                              "ಕರ್ನಾಟಕ ಶಾಲಾ ಪರೀಕ್ಷೆ ಮತ್ತು ಮೌಲ್ಯನಿರ್ಣಯ ಮಂಡಳಿ ನೀಡಿರುವ ಆನ್‌ಲೈನ್ ಅಂಕಪಟ್ಟಿ. kseab.karnataka.gov.in ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ."))],
            "signatory": {"name": ctx.t(L("Director (Examinations)", "ನಿರ್ದೇಶಕರು (ಪರೀಕ್ಷೆಗಳು)")), "designation": "KSEAB, Bengaluru"}})
        return doc_id, fname

    def _view(self, ctx, exam, reg_no, dob, year):
        res = result(ctx, exam, reg_no, year)
        lines = "\n".join(f"• {s}: *{m}*/{mx}" for s, m, mx in res["marks"])
        combo_line = (ctx.t(L("Combination: ", "ಸಂಯೋಜನೆ: ")) + f"{res['combo']}\n") if res["combo"] else ""
        msg = ctx.t(L(f"*{res['title']} - Online Marks Card*\n\nCandidate: *{res['name']}*\nRegister No: {reg_no}\n{combo_line}\n{lines}\n\n"
                      f"Total: *{res['total']}/{res['max_total']}* ({res['pct']:.2f}%)\nResult: *{res['cls']}*",
                      f"*{res['title']} - ಆನ್‌ಲೈನ್ ಅಂಕಪಟ್ಟಿ*\n\nಅಭ್ಯರ್ಥಿ: *{res['name']}*\nನೋಂದಣಿ ಸಂಖ್ಯೆ: {reg_no}\n{combo_line}\n{lines}\n\n"
                      f"ಒಟ್ಟು: *{res['total']}/{res['max_total']}* ({res['pct']:.2f}%)\nಫಲಿತಾಂಶ: *{res['cls']}*"))
        doc_id, fname = self._marks_doc(ctx, exam, reg_no, dob, year, res)
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx)))

    def _apply(self, ctx, v):
        res = result(ctx, v["exam"], v["reg_no"], v["year"])
        app = "KSEAB" + dt.date.today().strftime("%y%m%d") + gen.ref_id("", 4)
        rec = {k: v[k] for k in ("exam", "reg_no", "dob", "year", "reason")}
        rec.update(name=res["name"], paid_at=None)
        db.rec_put("dup_mc", app, rec, ctx.session_id)
        pid = payments.create(ctx.session_id, self.key, ctx.t(L("Duplicate Marks Card fee", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ಶುಲ್ಕ")), FEE, app)
        msg = ctx.t(L(f"*Duplicate Marks Card - Application Submitted*\n\nApplication No: *{app}*\nCandidate: {res['name']}\n"
                      f"Examination: {ctx.t(EXAMS[v['exam']])} {v['year']}\nRegister No: {v['reg_no']}\nReason: {ctx.t(REASONS[v['reason']])}\n\n"
                      f"Fee: *₹{FEE}.00*\nPlease pay the fee to forward the application to the Board records section.",
                      f"*ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ - ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: *{app}*\nಅಭ್ಯರ್ಥಿ: {res['name']}\n"
                      f"ಪರೀಕ್ಷೆ: {ctx.t(EXAMS[v['exam']])} {v['year']}\nನೋಂದಣಿ ಸಂಖ್ಯೆ: {v['reg_no']}\nಕಾರಣ: {ctx.t(REASONS[v['reason']])}\n\n"
                      f"ಶುಲ್ಕ: *₹{FEE}.00*\nಅರ್ಜಿಯನ್ನು ಮಂಡಳಿ ದಾಖಲೆ ವಿಭಾಗಕ್ಕೆ ರವಾನಿಸಲು ದಯವಿಟ್ಟು ಶುಲ್ಕ ಪಾವತಿಸಿ."))
        return Reply(ui.text(msg, cta=ui.cta_pay(ctx.s("pay", amt=f"₹{FEE}.00"), pid),
                             buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"track:{app}"))))

    def on_payment(self, ctx, p):
        rec = db.rec_get("dup_mc", p["ref"])
        if not rec:
            return [ui.text(ctx.s("payment_missing"))]
        rec["paid_at"] = time.time()
        rec["txn"] = p["txn_id"]
        db.rec_put("dup_mc", p["ref"], rec)
        fname = f"KSEAB_Acknowledgement_{p['ref']}.pdf"
        doc_id = docs.create(ctx.session_id, "dup_mc_ack", fname, {
            "lang": ctx.lang, "verify_url": "kseab.karnataka.gov.in", "dept": ctx.t(DEPT),
            "dept_sub": ctx.t(L("Malleshwaram, Bengaluru", "ಮಲ್ಲೇಶ್ವರಂ, ಬೆಂಗಳೂರು")),
            "title": ctx.t(L("ACKNOWLEDGEMENT", "ಸ್ವೀಕೃತಿ ಪತ್ರ")), "subtitle": ctx.t(L("Issue of Duplicate Marks Card", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ವಿತರಣೆ")),
            "ref_label": ctx.t(L("Application No", "ಅರ್ಜಿ ಸಂಖ್ಯೆ")), "ref": p["ref"],
            "sections": [{"rows": [[ctx.t(L("Candidate", "ಅಭ್ಯರ್ಥಿ")), rec["name"]],
                                   [ctx.t(L("Examination", "ಪರೀಕ್ಷೆ")), f"{ctx.t(EXAMS[rec['exam']])} {rec['year']}"],
                                   [ctx.t(L("Register No", "ನೋಂದಣಿ ಸಂಖ್ಯೆ")), rec["reg_no"]],
                                   [ctx.t(L("Reason", "ಕಾರಣ")), ctx.t(REASONS[rec["reason"]])],
                                   [ctx.t(L("Fee paid", "ಪಾವತಿಸಿದ ಶುಲ್ಕ")), gen.inr(p["amount"])],
                                   [ctx.t(L("Transaction ID", "ವಹಿವಾಟು ಸಂಖ್ಯೆ")), p["txn_id"]]]}],
            "notes": [ctx.t(L("Sakala service guarantee: duplicate marks card within 15 working days.", "ಸಕಾಲ ಸೇವಾ ಖಾತರಿ: 15 ಕೆಲಸದ ದಿನಗಳೊಳಗೆ ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ."))],
            "signatory": {"name": ctx.t(L("Secretary", "ಕಾರ್ಯದರ್ಶಿ")), "designation": "KSEAB, Bengaluru"}})
        msg = ctx.t(L(f"*Payment received - ₹{FEE}.00*\nTxn ID: {p['txn_id']}\n\nApplication *{p['ref']}* has been forwarded to the Board records section.\nSakala guarantee: within *15 working days*.",
                      f"*ಪಾವತಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ - ₹{FEE}.00*\nವಹಿವಾಟು ಸಂಖ್ಯೆ: {p['txn_id']}\n\nಅರ್ಜಿ *{p['ref']}* ಅನ್ನು ಮಂಡಳಿ ದಾಖಲೆ ವಿಭಾಗಕ್ಕೆ ರವಾನಿಸಲಾಗಿದೆ.\nಸಕಾಲ ಖಾತರಿ: *15 ಕೆಲಸದ ದಿನಗಳೊಳಗೆ*."))
        return [ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"track:{p['ref']}")))]

    def track(self, ctx, app):
        if gen.is_missing(app[5:]):
            return Errors({"app_no": L("No application found with this number.", "ಈ ಸಂಖ್ಯೆಯ ಅರ್ಜಿ ಕಂಡುಬಂದಿಲ್ಲ.")})
        rec = db.rec_get("dup_mc", app)
        if rec and not rec.get("paid_at"):
            pid = payments.create(ctx.session_id, self.key, ctx.t(L("Duplicate Marks Card fee", "ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ಶುಲ್ಕ")), FEE, app)
            return Reply(ui.text(ctx.t(L(f"*Application {app}*\n\nStatus: *Payment pending*\nPay ₹{FEE}.00 to forward your application.",
                                         f"*ಅರ್ಜಿ {app}*\n\nಸ್ಥಿತಿ: *ಪಾವತಿ ಬಾಕಿ*\nಅರ್ಜಿ ರವಾನಿಸಲು ₹{FEE}.00 ಪಾವತಿಸಿ.")),
                                 cta=ui.cta_pay(ctx.s("pay", amt=f"₹{FEE}.00"), pid), buttons=self.menu_buttons(ctx)))
        if rec:
            stage = stage_from_elapsed(rec["paid_at"], len(STAGES), start=1)
            exam, reg_no, dob, year, name = rec["exam"], rec["reg_no"], rec["dob"], rec["year"], rec["name"]
        else:
            r = gen.rng("dupmc", app)
            stage, exam, year = r.choice([2, 3, 3]), r.choice(list(EXAMS)), str(r.randint(2016, 2025))
            reg_no, dob = gen.digits(r, 10), (gen.today() - dt.timedelta(days=365 * r.randint(17, 30))).isoformat()
            name = result(ctx, exam, reg_no, year)["name"]
        msg = ctx.t(L(f"*Duplicate Marks Card - Application Status*\n\nApplication No: {app}\nCandidate: {name}\nExamination: {ctx.t(EXAMS[exam])} {year}\n\n",
                      f"*ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ - ಅರ್ಜಿ ಸ್ಥಿತಿ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: {app}\nಅಭ್ಯರ್ಥಿ: {name}\nಪರೀಕ್ಷೆ: {ctx.t(EXAMS[exam])} {year}\n\n"))
        msg += timeline(ctx, STAGES, stage)
        if stage == len(STAGES) - 1:
            msg += ctx.t(L("\n\nYour duplicate marks card is ready. Download it below.", "\n\nನಿಮ್ಮ ದ್ವಿಪ್ರತಿ ಅಂಕಪಟ್ಟಿ ಸಿದ್ಧವಾಗಿದೆ. ಕೆಳಗೆ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ."))
            doc_id, fname = self._marks_doc(ctx, exam, reg_no, dob, year, result(ctx, exam, reg_no, year), duplicate=app)
            return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx)))
        msg += ctx.t(L("\n\n_Status updates automatically. Check again shortly._", "\n\n_ಸ್ಥಿತಿ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನವೀಕರಣಗೊಳ್ಳುತ್ತದೆ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪರಿಶೀಲಿಸಿ._"))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Refresh Status", "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ")), f"track:{app}"))))

    def on_button(self, ctx, arg):
        if arg.startswith("track:"):
            return self.track(ctx, arg.split(":", 1)[1])
        return None

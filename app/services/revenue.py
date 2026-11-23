"""Revenue Department - Nadakacheri (Atalji Janasnehi Kendra) certificates.

Apply (Caste / Income / Caste & Income / Residence) -> review & declaration -> ₹25 fee ->
acknowledgement PDF -> track (stages advance every STAGE_SECONDS) -> certificate PDF.
Tracking also works for ANY well-formed RD number (deterministic status).
"""
import datetime as dt
import time

from .. import docs, payments, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Screen, Service, stage_from_elapsed, timeline

FEE = 25
CERTS = {
    "caste": L("Caste Certificate", "ಜಾತಿ ಪ್ರಮಾಣಪತ್ರ"),
    "income": L("Income Certificate", "ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ"),
    "caste_income": L("Caste & Income Certificate", "ಜಾತಿ ಮತ್ತು ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ"),
    "residence": L("Residence Certificate", "ವಾಸಸ್ಥಳ ಪ್ರಮಾಣಪತ್ರ"),
}
CATEGORIES = [("sc", "Scheduled Caste (SC)", "ಪರಿಶಿಷ್ಟ ಜಾತಿ (SC)"), ("st", "Scheduled Tribe (ST)", "ಪರಿಶಿಷ್ಟ ಪಂಗಡ (ST)"),
              ("cat1", "Category-1", "ಪ್ರವರ್ಗ-1"), ("2a", "Category-2A", "ಪ್ರವರ್ಗ-2ಎ"), ("2b", "Category-2B", "ಪ್ರವರ್ಗ-2ಬಿ"),
              ("3a", "Category-3A", "ಪ್ರವರ್ಗ-3ಎ"), ("3b", "Category-3B", "ಪ್ರವರ್ಗ-3ಬಿ")]
CAT_NAME = {k: L(en, kn) for k, en, kn in CATEGORIES}
# Communities used only when generating a record for an unknown tracking number (demo data).
SAMPLE_CASTES = {"sc": ["Holeya", "Madiga", "Bhovi"], "st": ["Naikda", "Valmiki", "Soliga"],
                 "cat1": ["Uppara", "Gangamatha"], "2a": ["Kuruba", "Ediga", "Devanga"], "2b": ["Muslim"],
                 "3a": ["Vokkaliga"], "3b": ["Lingayat"]}
PURPOSES = {"education": L("Education", "ಶಿಕ್ಷಣ"), "employment": L("Employment", "ಉದ್ಯೋಗ"),
            "scholarship": L("Scholarship", "ವಿದ್ಯಾರ್ಥಿವೇತನ"), "scheme": L("Government Scheme", "ಸರ್ಕಾರಿ ಯೋಜನೆ")}
STAGES = [
    L("Application submitted", "ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ"),
    L("Fee paid - forwarded to Village Administrative Officer", "ಶುಲ್ಕ ಪಾವತಿ - ಗ್ರಾಮ ಆಡಳಿತ ಅಧಿಕಾರಿಗೆ ರವಾನೆ"),
    L("Field verification by Village Administrative Officer", "ಗ್ರಾಮ ಆಡಳಿತ ಅಧಿಕಾರಿಯಿಂದ ಸ್ಥಳ ಪರಿಶೀಲನೆ"),
    L("Revenue Inspector report submitted", "ಕಂದಾಯ ನಿರೀಕ್ಷಕರ ವರದಿ ಸಲ್ಲಿಕೆ"),
    L("Approved by Deputy Tahsildar", "ಉಪ ತಹಶೀಲ್ದಾರ್ ಅನುಮೋದನೆ"),
    L("Certificate issued (digitally signed)", "ಪ್ರಮಾಣಪತ್ರ ವಿತರಿಸಲಾಗಿದೆ (ಡಿಜಿಟಲ್ ಸಹಿ)"),
]
NAME_RE = r"^[A-Za-zಀ-೿ .']{3,60}$"


class Revenue(Service):
    key = "revenue"
    order = 1
    icon = "certificate"
    title = L("Revenue Department Certificates (AJSK)", "ಕಂದಾಯ ಇಲಾಖೆ ಪ್ರಮಾಣಪತ್ರಗಳು (AJSK)")
    subtitle = L("Caste, Income & Residence Certificates", "ಜಾತಿ, ಆದಾಯ ಮತ್ತು ವಾಸಸ್ಥಳ ಪ್ರಮಾಣಪತ್ರ")
    sevaone = [L("Caste Certificate (SC/ST)"), L("Caste Certificate (Cat-A)"), L("Income Certificate"),
               L("Caste and Income Certficate"), L("Residence Certificate")]
    dept = L("Revenue Department - Atalji Janasnehi Kendra", "ಕಂದಾಯ ಇಲಾಖೆ - ಅಟಲ್‌ಜೀ ಜನಸ್ನೇಹಿ ಕೇಂದ್ರ")
    keywords = ["certificate", "caste", "income", "residence", "nadakacheri", "ajsk", "tahsildar",
                "jati", "aadaya", "domicile", "ಪ್ರಮಾಣಪತ್ರ", "ಜಾತಿ", "ಆದಾಯ", "ವಾಸಸ್ಥಳ", "ನಾಡಕಚೇರಿ", "ಸರ್ಟಿಫಿಕೇಟ್"]

    def fields(self, ctx):
        apply = {"action": "apply"}
        return [
            fk.radio("action", L("What would you like to do?", "ನೀವು ಏನು ಮಾಡಲು ಬಯಸುತ್ತೀರಿ?"), [
                fk.opt("apply", L("Apply for a Certificate", "ಪ್ರಮಾಣಪತ್ರಕ್ಕೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ")),
                fk.opt("track", L("Track Application / Download Certificate", "ಅರ್ಜಿ ಸ್ಥಿತಿ / ಪ್ರಮಾಣಪತ್ರ ಡೌನ್‌ಲೋಡ್")),
            ]),
            fk.radio("cert", L("Select Certificate", "ಪ್ರಮಾಣಪತ್ರ ಆಯ್ಕೆಮಾಡಿ"),
                     [fk.opt(k, v) for k, v in CERTS.items()], show_if=apply),
            fk.text("name", L("Applicant Name (as per Aadhaar)", "ಅರ್ಜಿದಾರರ ಹೆಸರು (ಆಧಾರ್ ಪ್ರಕಾರ)"), show_if=apply,
                    placeholder=L("e.g. Ramesh Kumar", "ಉದಾ: ರಮೇಶ್ ಕುಮಾರ್"), pattern=NAME_RE,
                    error=L("Enter a valid name (letters only, min 3)", "ಮಾನ್ಯ ಹೆಸರು ನಮೂದಿಸಿ (ಅಕ್ಷರಗಳು ಮಾತ್ರ)")),
            fk.text("father", L("Father / Husband Name", "ತಂದೆ / ಪತಿಯ ಹೆಸರು"), show_if=apply, pattern=NAME_RE,
                    error=L("Enter a valid name", "ಮಾನ್ಯ ಹೆಸರು ನಮೂದಿಸಿ")),
            fk.radio("gender", L("Gender", "ಲಿಂಗ"), [fk.opt("M", L("Male", "ಪುರುಷ")), fk.opt("F", L("Female", "ಮಹಿಳೆ")),
                                                   fk.opt("O", L("Other", "ಇತರೆ"))], show_if=apply),
            fk.text("aadhaar", L("Aadhaar Number", "ಆಧಾರ್ ಸಂಖ್ಯೆ"), show_if=apply, placeholder="2345 6789 0123",
                    transform="digits", pattern=r"^\d{12}$", input_mode="numeric",
                    error=L("Aadhaar number must be exactly 12 digits", "ಆಧಾರ್ ಸಂಖ್ಯೆ ನಿಖರವಾಗಿ 12 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.dropdown("district", L("District", "ಜಿಲ್ಲೆ"), K.DISTRICT_OPTIONS, show_if=apply),
            fk.text("taluk", L("Taluk", "ತಾಲ್ಲೂಕು"), show_if=apply, min_len=3,
                    placeholder=L("e.g. Anekal", "ಉದಾ: ಆನೇಕಲ್")),
            fk.dropdown("category", L("Reservation Category", "ಮೀಸಲಾತಿ ಪ್ರವರ್ಗ"),
                        [fk.opt(k, L(en, kn)) for k, en, kn in CATEGORIES],
                        show_if={"action": "apply", "cert": ["caste", "caste_income"]}),
            fk.text("caste", L("Caste / Sub-caste", "ಜಾತಿ / ಉಪಜಾತಿ"), min_len=2,
                    show_if={"action": "apply", "cert": ["caste", "caste_income"]}),
            fk.number("income", L("Annual Family Income (₹)", "ವಾರ್ಷಿಕ ಕುಟುಂಬ ಆದಾಯ (₹)"), min=0, max=999999999,
                      error=L("Enter the annual family income in rupees, digits only.", "ವಾರ್ಷಿಕ ಕುಟುಂಬ ಆದಾಯವನ್ನು ರೂಪಾಯಿಗಳಲ್ಲಿ, ಅಂಕಿಗಳಲ್ಲಿ ಮಾತ್ರ ನಮೂದಿಸಿ."),
                      placeholder="120000", show_if={"action": "apply", "cert": ["income", "caste_income"]}),
            fk.radio("purpose", L("Purpose", "ಉದ್ದೇಶ"), [fk.opt(k, v) for k, v in PURPOSES.items()], show_if=apply),
            fk.text("app_no", L("Enter your Application Number", "ನಿಮ್ಮ ಅರ್ಜಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"),
                    show_if={"action": "track"}, placeholder="RD0052611224567", transform="upper_nospace",
                    pattern=r"^RD\d{13}$",
                    error=L("Application number starts with RD followed by 13 digits",
                            "ಅರ್ಜಿ ಸಂಖ್ಯೆ RD ನಂತರ 13 ಅಂಕಿಗಳನ್ನು ಹೊಂದಿರುತ್ತದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        out = {}
        if any(w in t for w in ("status", "track", "ಸ್ಥಿತಿ", "download")):
            out["action"] = "track"
        elif any(w in t for w in ("caste", "income", "residence", "ಜಾತಿ", "ಆದಾಯ", "ವಾಸಸ್ಥಳ", "apply", "certificate", "ಪ್ರಮಾಣಪತ್ರ")):
            out["action"] = "apply"
            caste = "caste" in t or "ಜಾತಿ" in t
            income = "income" in t or "ಆದಾಯ" in t
            if caste and income:
                out["cert"] = "caste_income"
            elif caste:
                out["cert"] = "caste"
            elif income:
                out["cert"] = "income"
            elif "residence" in t or "ವಾಸಸ್ಥಳ" in t:
                out["cert"] = "residence"
        return out

    # ---------------------------------------------------------------------
    def submit(self, ctx, screen, values, data):
        if screen == "main":
            if values["action"] == "track":
                return self.track(ctx, values["app_no"])
            return self._review(ctx, values)
        if screen == "review":
            return self._create(ctx, data)
        return Reply()

    def _summary_rows(self, ctx, v):
        rows = [(L("Certificate", "ಪ್ರಮಾಣಪತ್ರ"), ctx.t(CERTS[v["cert"]])),
                (L("Applicant", "ಅರ್ಜಿದಾರರು"), v["name"]),
                (L("Father / Husband", "ತಂದೆ / ಪತಿ"), v["father"]),
                (L("Aadhaar", "ಆಧಾರ್"), "XXXX XXXX " + v["aadhaar"][-4:]),
                (L("District / Taluk", "ಜಿಲ್ಲೆ / ತಾಲ್ಲೂಕು"), f"{ctx.t(K.DISTRICT_NAME[v['district']])} / {v['taluk']}")]
        if v.get("category"):
            rows.append((L("Category / Caste", "ಪ್ರವರ್ಗ / ಜಾತಿ"), f"{ctx.t(CAT_NAME[v['category']])} / {v.get('caste', '')}"))
        if v.get("income") not in (None, ""):
            rows.append((L("Annual Income", "ವಾರ್ಷಿಕ ಆದಾಯ"), gen.inr(v["income"], 0)))
        rows.append((L("Purpose", "ಉದ್ದೇಶ"), ctx.t(PURPOSES[v["purpose"]])))
        return [(ctx.t(k), val) for k, val in rows]

    def _review(self, ctx, v):
        lines = "\n".join(f"• {k}: *{val}*" for k, val in self._summary_rows(ctx, v))
        intro = L("Please review your application:", "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ಪರಿಶೀಲಿಸಿ:")
        fee = L(f"Service fee: ₹{FEE}.00 (payable after submission)", f"ಸೇವಾ ಶುಲ್ಕ: ₹{FEE}.00 (ಸಲ್ಲಿಕೆಯ ನಂತರ ಪಾವತಿಸಿ)")
        return Screen("review", L("Review & Submit", "ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಸಲ್ಲಿಸಿ"), [
            fk.info("summary", f"{ctx.t(intro)}\n\n{lines}\n\n{ctx.t(fee)}"),
            fk.radio("declare", L("Declaration", "ಘೋಷಣೆ"), [fk.opt("yes", L(
                "I declare that the information furnished above is true to the best of my knowledge.",
                "ಮೇಲೆ ನೀಡಿರುವ ಮಾಹಿತಿ ನನ್ನ ತಿಳುವಳಿಕೆಯ ಪ್ರಕಾರ ಸತ್ಯವಾಗಿದೆ ಎಂದು ಘೋಷಿಸುತ್ತೇನೆ."))]),
        ], data=v, submit=L("Submit Application", "ಅರ್ಜಿ ಸಲ್ಲಿಸಿ"))

    def _create(self, ctx, v):
        r = gen.rng(time.time())
        app_no = f"RD{K.DISTRICT_INDEX[v['district']]:03d}{dt.date.today():%y%m%d}{gen.digits(r, 4)}"
        rec = dict(v, app_no=app_no, paid_at=None, lang=ctx.lang)
        from .. import db
        db.rec_put("nk_app", app_no, rec, ctx.session_id)
        pid = payments.create(ctx.session_id, self.key, ctx.t(CERTS[v["cert"]]), FEE, app_no)
        msg = ctx.t(L(
            f"*Application submitted successfully*\n\nApplication No: *{app_no}*\n"
            f"Certificate: {ctx.t(CERTS[v['cert']])}\nApplicant: {v['name']}\nTaluk Office: {v['taluk']}, {ctx.t(K.DISTRICT_NAME[v['district']])}\n\n"
            f"Service fee: *₹{FEE}.00*\nPlease pay the fee to forward your application to the Village Administrative Officer.",
            f"*ಅರ್ಜಿಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: *{app_no}*\n"
            f"ಪ್ರಮಾಣಪತ್ರ: {ctx.t(CERTS[v['cert']])}\nಅರ್ಜಿದಾರರು: {v['name']}\nತಾಲ್ಲೂಕು ಕಚೇರಿ: {v['taluk']}, {ctx.t(K.DISTRICT_NAME[v['district']])}\n\n"
            f"ಸೇವಾ ಶುಲ್ಕ: *₹{FEE}.00*\nಗ್ರಾಮ ಆಡಳಿತ ಅಧಿಕಾರಿಗೆ ಅರ್ಜಿ ರವಾನಿಸಲು ದಯವಿಟ್ಟು ಶುಲ್ಕ ಪಾವತಿಸಿ."))
        return Reply(ui.text(msg, cta=ui.cta_pay(ctx.s("pay", amt=f"₹{FEE}.00"), pid),
                             buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"track:{app_no}"))))

    def on_payment(self, ctx, p):
        from .. import db
        rec = db.rec_get("nk_app", p["ref"])
        if not rec:
            return [ui.text(ctx.s("payment_missing"))]
        rec["paid_at"] = time.time()
        rec["txn"] = p["txn_id"]
        db.rec_put("nk_app", p["ref"], rec)
        rows = self._summary_rows(ctx, rec)
        doc_id = docs.create(ctx.session_id, "nk_ack", f"Acknowledgement_{p['ref']}.pdf", {
            "lang": ctx.lang, "place": rec["taluk"], "dept": ctx.t(self.dept),
            "dept_sub": ctx.t(L("Office of the Tahsildar, ", "ತಹಶೀಲ್ದಾರ್ ಕಚೇರಿ, ")) + rec["taluk"],
            "title": ctx.t(L("Acknowledgement", "ಸ್ವೀಕೃತಿ ಪತ್ರ")), "subtitle": ctx.t(CERTS[rec["cert"]]),
            "ref_label": ctx.t(L("Application No", "ಅರ್ಜಿ ಸಂಖ್ಯೆ")), "ref": p["ref"],
            "sections": [{"heading": ctx.t(L("Application Details", "ಅರ್ಜಿ ವಿವರಗಳು")), "rows": rows},
                         {"heading": ctx.t(L("Payment", "ಪಾವತಿ")), "rows": [
                             [ctx.t(L("Amount", "ಮೊತ್ತ")), gen.inr(p["amount"])],
                             [ctx.t(L("Transaction ID", "ವಹಿವಾಟು ಸಂಖ್ಯೆ")), p["txn_id"]],
                             [ctx.t(L("Mode", "ವಿಧಾನ")), p["method"]]]}],
            "notes": [ctx.t(L("Sakala service guarantee: certificate within 21 working days.",
                              "ಸಕಾಲ ಸೇವಾ ಖಾತರಿ: 21 ಕೆಲಸದ ದಿನಗಳೊಳಗೆ ಪ್ರಮಾಣಪತ್ರ."))],
            "signatory": {"name": "Atalji Janasnehi Kendra", "designation": rec["taluk"]}})
        msg = ctx.t(L(
            f"*Payment received - ₹{FEE}.00*\nTxn ID: {p['txn_id']}\n\n"
            f"Your application *{p['ref']}* has been forwarded to the Village Administrative Officer for verification.\n\n"
            "Sakala guarantee: within *21 working days*.\nYou will get updates here on WhatsApp.",
            f"*ಪಾವತಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ - ₹{FEE}.00*\nವಹಿವಾಟು ಸಂಖ್ಯೆ: {p['txn_id']}\n\n"
            f"ನಿಮ್ಮ ಅರ್ಜಿ *{p['ref']}* ಅನ್ನು ಪರಿಶೀಲನೆಗಾಗಿ ಗ್ರಾಮ ಆಡಳಿತ ಅಧಿಕಾರಿಗೆ ರವಾನಿಸಲಾಗಿದೆ.\n\n"
            "ಸಕಾಲ ಖಾತರಿ: *21 ಕೆಲಸದ ದಿನಗಳೊಳಗೆ*.\nನವೀಕರಣಗಳನ್ನು ಇಲ್ಲೇ ವಾಟ್ಸಾಪ್‌ನಲ್ಲಿ ಪಡೆಯುತ್ತೀರಿ."))
        return [ui.text(msg),
                ui.document(doc_id, f"Acknowledgement_{p['ref']}.pdf",
                            buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"track:{p['ref']}")))]

    def on_button(self, ctx, arg):
        if arg.startswith("track:"):
            return self.track(ctx, arg.split(":", 1)[1])
        return None

    # ---------------------------------------------------------------------
    def track(self, ctx, app_no):
        from .. import db
        if gen.is_missing(app_no[2:]):
            return Errors({"app_no": L("No application found with this number. Please check and re-enter.",
                                       "ಈ ಸಂಖ್ಯೆಯ ಯಾವುದೇ ಅರ್ಜಿ ಕಂಡುಬಂದಿಲ್ಲ. ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ನಮೂದಿಸಿ.")})
        rec = db.rec_get("nk_app", app_no)
        if rec:
            if not rec.get("paid_at"):
                pid = payments.create(ctx.session_id, self.key, ctx.t(CERTS[rec["cert"]]), FEE, app_no)
                msg = ctx.t(L(f"*Application {app_no}*\n\nStatus: *Payment pending*\nPay ₹{FEE}.00 to forward your application.",
                              f"*ಅರ್ಜಿ {app_no}*\n\nಸ್ಥಿತಿ: *ಪಾವತಿ ಬಾಕಿ*\nಅರ್ಜಿ ರವಾನಿಸಲು ₹{FEE}.00 ಪಾವತಿಸಿ."))
                return Reply(ui.text(msg, cta=ui.cta_pay(ctx.s("pay", amt=f"₹{FEE}.00"), pid), buttons=self.menu_buttons(ctx)))
            stage = stage_from_elapsed(rec["paid_at"], len(STAGES), start=1)
            applicant, cert, taluk, district = rec["name"], rec["cert"], rec["taluk"], rec["district"]
            father, gender, extra = rec["father"], rec["gender"], rec
        else:
            r = gen.rng("nk", app_no)
            stage = r.choice([2, 3, 4, 5, 5, 5])
            p = gen.person(r)
            applicant, gender = ctx.t(p["name"]), p["gender"]
            father = ctx.t(gen.person(r, "M")["name"])
            cert = r.choice(list(CERTS))
            district = r.choice(K.DISTRICTS)[0]
            taluk = ctx.t(K.DISTRICT_NAME[district])
            category = r.choice(CATEGORIES)[0]
            extra = {"income": r.choice([48000, 72000, 96000, 120000, 180000]),
                     "category": category, "caste": r.choice(SAMPLE_CASTES.get(category, ["Vokkaliga"]))}
        msg = ctx.t(L(f"*Application Status*\n\nApplication No: {app_no}\nCertificate: {ctx.t(CERTS[cert])}\nApplicant: {applicant}\n\n",
                      f"*ಅರ್ಜಿ ಸ್ಥಿತಿ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: {app_no}\nಪ್ರಮಾಣಪತ್ರ: {ctx.t(CERTS[cert])}\nಅರ್ಜಿದಾರರು: {applicant}\n\n"))
        msg += timeline(ctx, STAGES, stage)
        out = []
        if stage == len(STAGES) - 1:
            msg += "\n\n" + ctx.t(L("Your certificate is ready. Download it below.",
                                    "ನಿಮ್ಮ ಪ್ರಮಾಣಪತ್ರ ಸಿದ್ಧವಾಗಿದೆ. ಕೆಳಗೆ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ."))
            out.append(ui.text(msg))
            doc_id = self._certificate(ctx, app_no, cert, applicant, father, gender, taluk, district, extra)
            out.append(ui.document(doc_id, f"{cert.title().replace('_', '_and_')}_Certificate_{app_no}.pdf",
                                   buttons=self.menu_buttons(ctx)))
        else:
            msg += "\n\n" + ctx.t(L("_Status updates automatically. Check again shortly._",
                                    "_ಸ್ಥಿತಿ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನವೀಕರಣಗೊಳ್ಳುತ್ತದೆ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪರಿಶೀಲಿಸಿ._"))
            out.append(ui.text(msg, buttons=self.menu_buttons(
                ctx, self.btn(ctx.t(L("Refresh Status", "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ")), f"track:{app_no}"))))
        return Reply(*out)

    def _certificate(self, ctx, app_no, cert, name, father, gender, taluk, district, extra):
        rel = {"M": ("S/o", "ಮಗ"), "F": ("D/o", "ಮಗಳು"), "O": ("C/o", "")}.get(gender, ("S/o", "ಮಗ"))
        hon = {"M": ("Sri", "ಶ್ರೀ"), "F": ("Smt", "ಶ್ರೀಮತಿ")}.get(gender, ("Sri/Smt", "ಶ್ರೀ/ಶ್ರೀಮತಿ"))
        dist = ctx.t(K.DISTRICT_NAME.get(district, L(district)))
        income = gen.inr(extra.get("income") or 0, 0)
        cat = ctx.t(CAT_NAME.get(extra.get("category"), L("-")))
        if ctx.kn:
            base = f"{dist} ಜಿಲ್ಲೆ, {taluk} ತಾಲ್ಲೂಕಿನ ನಿವಾಸಿಯಾದ {hon[1]} {name}, {father} ಅವರ {rel[1]},"
            body = {"income": f"{base} ಇವರ ಕುಟುಂಬದ ಎಲ್ಲಾ ಮೂಲಗಳಿಂದ ವಾರ್ಷಿಕ ಆದಾಯ {income} ಎಂದು ಪ್ರಮಾಣೀಕರಿಸಲಾಗಿದೆ.",
                    "caste": f"{base} ಇವರು {extra.get('caste', '')} ಜಾತಿಗೆ ಸೇರಿದ್ದು, ಇದು ಕರ್ನಾಟಕ ಸರ್ಕಾರದ ಆದೇಶದಂತೆ {cat} ಅಡಿ ಮಾನ್ಯವಾಗಿದೆ ಎಂದು ಪ್ರಮಾಣೀಕರಿಸಲಾಗಿದೆ.",
                    "caste_income": f"{base} ಇವರು {extra.get('caste', '')} ಜಾತಿಗೆ ({cat}) ಸೇರಿದ್ದು, ಕುಟುಂಬದ ವಾರ್ಷಿಕ ಆದಾಯ {income} ಎಂದು ಪ್ರಮಾಣೀಕರಿಸಲಾಗಿದೆ.",
                    "residence": f"{base} ಇವರು ಕಳೆದ 5 ವರ್ಷಗಳಿಂದ ಮೇಲ್ಕಂಡ ವಿಳಾಸದಲ್ಲಿ ವಾಸವಾಗಿದ್ದಾರೆ ಎಂದು ಪ್ರಮಾಣೀಕರಿಸಲಾಗಿದೆ."}[cert]
        else:
            base = f"This is to certify that {hon[0]} {name}, {rel[0]} {father}, resident of {taluk} Taluk, {dist} District,"
            body = {"income": f"{base} has an annual family income of {income} from all sources.",
                    "caste": f"{base} belongs to the {extra.get('caste', '')} caste, which is recognised under {cat} as per the orders of the Government of Karnataka.",
                    "caste_income": f"{base} belongs to the {extra.get('caste', '')} caste ({cat}) and the annual family income from all sources is {income}.",
                    "residence": f"{base} has been residing at the above address for the last 5 years."}[cert]
        return docs.create(ctx.session_id, "nk_cert", f"{cert.title().replace('_', '_and_')}_Certificate_{app_no}.pdf", {
            "lang": ctx.lang, "place": taluk, "dept": ctx.t(L("Revenue Department", "ಕಂದಾಯ ಇಲಾಖೆ")),
            "dept_sub": ctx.t(L(f"Office of the Tahsildar, {taluk} Taluk", f"ತಹಶೀಲ್ದಾರ್ ಕಚೇರಿ, {taluk} ತಾಲ್ಲೂಕು")),
            "title": ctx.t(CERTS[cert]).upper() if not ctx.kn else ctx.t(CERTS[cert]),
            "ref_label": ctx.t(L("Certificate No", "ಪ್ರಮಾಣಪತ್ರ ಸಂಖ್ಯೆ")), "ref": app_no,
            "sections": [{"text": body}, {"rows": [
                [ctx.t(L("Validity", "ಮಾನ್ಯತೆ")), ctx.t(L("5 years from the date of issue", "ವಿತರಣಾ ದಿನಾಂಕದಿಂದ 5 ವರ್ಷ"))],
                [ctx.t(L("Issued under", "ವಿತರಣೆ")), ctx.t(L("Sakala Services Act, 2011", "ಸಕಾಲ ಸೇವೆಗಳ ಕಾಯ್ದೆ, 2011"))]]}],
            "signatory": {"name": ctx.t(L("Deputy Tahsildar", "ಉಪ ತಹಶೀಲ್ದಾರ್")), "designation": f"{taluk}, {dist}"}})

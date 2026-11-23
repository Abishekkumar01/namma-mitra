"""Department of Industrial Training and Employment - Yuvanidhi scheme.

Seva One services covered: "Application for Yuvanidhi scheme",
"Yuvanidhi - Application for Monthly Unemployment Self Declaration", "Yuvanidhi Application Status Check".
Apply -> acknowledgement PDF -> live status; status/declaration by any well-formed YN number.
"""
import datetime as dt

from .. import db, docs, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service, masked_aadhaar, stage_from_elapsed, timeline

DEPT = L("Department of Industrial Training and Employment", "ಕೈಗಾರಿಕಾ ತರಬೇತಿ ಮತ್ತು ಉದ್ಯೋಗ ಇಲಾಖೆ")
QUALS = {"degree": (L("Degree (Graduate)", "ಪದವಿ (ಪದವೀಧರ)"), 3000), "diploma": (L("Diploma", "ಡಿಪ್ಲೊಮಾ"), 1500)}
STAGES = [L("Application submitted", "ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ"),
          L("Aadhaar and marks card verified", "ಆಧಾರ್ ಮತ್ತು ಅಂಕಪಟ್ಟಿ ಪರಿಶೀಲನೆ"),
          L("Employment status checked (EPFO / ESI)", "ಉದ್ಯೋಗ ಸ್ಥಿತಿ ಪರಿಶೀಲನೆ (EPFO / ESI)"),
          L("Approved - allowance sanctioned", "ಅನುಮೋದಿತ - ಭತ್ಯೆ ಮಂಜೂರು")]
YN_RE = r"^YN\d{8,10}$"
NAME_RE = r"^[A-Za-zಀ-೿ .']{3,60}$"


class Yuvanidhi(Service):
    key = "yuvanidhi"
    order = 4
    icon = "yuvanidhi"
    title = L("Yuvanidhi Scheme", "ಯುವನಿಧಿ ಯೋಜನೆ")
    subtitle = L("Apply, check status, monthly self-declaration", "ಅರ್ಜಿ, ಸ್ಥಿತಿ, ಮಾಸಿಕ ಸ್ವಯಂ ಘೋಷಣೆ")
    dept = DEPT
    sevaone = [L("Application for Yuvanidhi scheme"), L("Yuvanidhi Application Status Check"),
               L("Yuvanidhi - Application for Monthly Unemployment Self Declaration")]
    keywords = ["yuva nidhi", "yuvanidhi", "unemployment", "allowance", "self declaration", "ಯುವನಿಧಿ", "ನಿರುದ್ಯೋಗ", "ಭತ್ಯೆ"]

    def fields(self, ctx):
        apply = {"action": "apply"}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("apply", L("Application for Yuvanidhi Scheme", "ಯುವನಿಧಿ ಯೋಜನೆಗೆ ಅರ್ಜಿ")),
                fk.opt("status", L("Yuvanidhi Application Status Check", "ಯುವನಿಧಿ ಅರ್ಜಿ ಸ್ಥಿತಿ")),
                fk.opt("declare", L("Monthly Unemployment Self Declaration", "ಮಾಸಿಕ ನಿರುದ್ಯೋಗ ಸ್ವಯಂ ಘೋಷಣೆ"))]),
            fk.text("name", L("Applicant Name (as per Aadhaar)", "ಅರ್ಜಿದಾರರ ಹೆಸರು (ಆಧಾರ್ ಪ್ರಕಾರ)"), show_if=apply,
                    pattern=NAME_RE, placeholder=L("e.g. Kiran Kumar", "ಉದಾ: ಕಿರಣ್ ಕುಮಾರ್"),
                    error=L("Enter a valid name (letters only, min 3)", "ಮಾನ್ಯ ಹೆಸರು ನಮೂದಿಸಿ (ಅಕ್ಷರಗಳು ಮಾತ್ರ)")),
            fk.text("aadhaar", L("Aadhaar Number", "ಆಧಾರ್ ಸಂಖ್ಯೆ"), show_if=apply, placeholder="2345 6789 0123",
                    transform="digits", pattern=r"^\d{12}$", input_mode="numeric",
                    error=L("Aadhaar number must be exactly 12 digits", "ಆಧಾರ್ ಸಂಖ್ಯೆ ನಿಖರವಾಗಿ 12 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.date("dob", L("Date of Birth", "ಜನ್ಮ ದಿನಾಂಕ"), min_days=-365 * 35, max_days=-365 * 18, show_if=apply,
                    helper=L("Applicant must be 18 to 35 years old", "ಅರ್ಜಿದಾರರ ವಯಸ್ಸು 18 ರಿಂದ 35 ವರ್ಷ ಇರಬೇಕು"),
                    error=L("Applicant must be 18 to 35 years old (born between {a} and {b}).",
                            "ಅರ್ಜಿದಾರರ ವಯಸ್ಸು 18 ರಿಂದ 35 ವರ್ಷ ಇರಬೇಕು ({a} ರಿಂದ {b} ನಡುವೆ ಜನಿಸಿರಬೇಕು).")),
            fk.radio("qual", L("Qualification", "ವಿದ್ಯಾರ್ಹತೆ"), [fk.opt(k, v[0], L(f"₹{v[1]:,} per month", f"ತಿಂಗಳಿಗೆ ₹{v[1]:,}")) for k, v in QUALS.items()], show_if=apply),
            fk.number("year", L("Year of Passing", "ಉತ್ತೀರ್ಣ ವರ್ಷ"), min=2022, max=2026, placeholder="2025", show_if=apply,
                      helper=L("Year you passed your degree or diploma (2022 to 2026)", "ಪದವಿ ಅಥವಾ ಡಿಪ್ಲೊಮಾ ಉತ್ತೀರ್ಣರಾದ ವರ್ಷ (2022 ರಿಂದ 2026)"),
                      error=L("Year of passing must be between {min} and {max}. Yuvanidhi covers graduates and diploma holders who passed in {min} or later, and a future year is not possible.",
                              "ಉತ್ತೀರ್ಣ ವರ್ಷ {min} ರಿಂದ {max} ನಡುವೆ ಇರಬೇಕು. ಯುವನಿಧಿ {min} ಅಥವಾ ನಂತರ ಉತ್ತೀರ್ಣರಾದ ಪದವೀಧರರು ಮತ್ತು ಡಿಪ್ಲೊಮಾದಾರರಿಗೆ ಮಾತ್ರ; ಭವಿಷ್ಯದ ವರ್ಷ ನಮೂದಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ.")),
            fk.dropdown("district", L("District", "ಜಿಲ್ಲೆ"), K.DISTRICT_OPTIONS, show_if=apply),
            fk.text("yn_app", L("Enter Yuvanidhi Application Number", "ಯುವನಿಧಿ ಅರ್ಜಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"),
                    show_if={"action": ["status", "declare"]}, placeholder="YN2400123456", transform="upper_nospace",
                    pattern=YN_RE, error=L("Application number looks like YN2400123456", "ಅರ್ಜಿ ಸಂಖ್ಯೆ YN2400123456 ರೀತಿ ಇರುತ್ತದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        if any(w in t for w in ("declar", "ಘೋಷಣೆ")):
            return {"action": "declare"}
        if any(w in t for w in ("apply", "ಅರ್ಜಿ ಸಲ್ಲಿಸ")):
            return {"action": "apply"}
        return {"action": "status"}

    def submit(self, ctx, screen, v, data):
        if v["action"] == "apply":
            return self._apply(ctx, v)
        if gen.is_missing(v["yn_app"][2:]):
            return Errors({"yn_app": L("No Yuvanidhi application found with this number.", "ಈ ಸಂಖ್ಯೆಯ ಯುವನಿಧಿ ಅರ್ಜಿ ಕಂಡುಬಂದಿಲ್ಲ.")})
        return self._status(ctx, v["yn_app"]) if v["action"] == "status" else self._declare_prompt(ctx, v["yn_app"])

    # ---------------------------------------------------------------------
    def _record(self, ctx, app):
        rec = db.rec_get("yn_app", app)
        if rec:
            return dict(rec, name=rec["name"], stage=stage_from_elapsed(rec["_created_at"], len(STAGES)), live=True)
        r = gen.rng("yn", app)
        return {"name": ctx.t(gen.person(r)["name"]), "qual": "degree" if r.random() < 0.7 else "diploma",
                "district": r.choice(K.DISTRICTS)[0], "stage": len(STAGES) - 1, "live": False, "r": r}

    def _apply(self, ctx, v):
        app = "YN" + dt.date.today().strftime("%y") + gen.ref_id("", 8)
        rec = {k: v[k] for k in ("name", "aadhaar", "dob", "qual", "year", "district")}
        db.rec_put("yn_app", app, rec, ctx.session_id)
        amt = QUALS[v["qual"]][1]
        dist = ctx.t(K.DISTRICT_NAME[v["district"]])
        fname = f"Yuvanidhi_Acknowledgement_{app}.pdf"
        doc_id = docs.create(ctx.session_id, "yn_ack", fname, {
            "lang": ctx.lang, "place": dist, "verify_url": "sevaone.karnataka.gov.in",
            "dept": ctx.t(DEPT), "dept_sub": ctx.t(L("Yuvanidhi Scheme", "ಯುವನಿಧಿ ಯೋಜನೆ")),
            "title": ctx.t(L("APPLICATION ACKNOWLEDGEMENT", "ಅರ್ಜಿ ಸ್ವೀಕೃತಿ")),
            "ref_label": ctx.t(L("Application No", "ಅರ್ಜಿ ಸಂಖ್ಯೆ")), "ref": app,
            "sections": [{"rows": [
                [ctx.t(L("Applicant", "ಅರ್ಜಿದಾರರು")), v["name"]], [ctx.t(L("Aadhaar", "ಆಧಾರ್")), masked_aadhaar(v["aadhaar"])],
                [ctx.t(L("Date of Birth", "ಜನ್ಮ ದಿನಾಂಕ")), gen.dmy(v["dob"])],
                [ctx.t(L("Qualification", "ವಿದ್ಯಾರ್ಹತೆ")), f"{ctx.t(QUALS[v['qual']][0])} ({v['year']})"],
                [ctx.t(L("District", "ಜಿಲ್ಲೆ")), dist],
                [ctx.t(L("Eligible allowance", "ಅರ್ಹ ಭತ್ಯೆ")), ctx.t(L(f"₹{amt:,} per month for up to 24 months", f"ಗರಿಷ್ಠ 24 ತಿಂಗಳವರೆಗೆ ತಿಂಗಳಿಗೆ ₹{amt:,}"))]]}],
            "notes": [ctx.t(L("Allowance is paid only while the applicant remains unemployed and submits the monthly self-declaration.",
                              "ಅರ್ಜಿದಾರರು ನಿರುದ್ಯೋಗಿಯಾಗಿದ್ದು ಮಾಸಿಕ ಸ್ವಯಂ ಘೋಷಣೆ ಸಲ್ಲಿಸುವವರೆಗೆ ಮಾತ್ರ ಭತ್ಯೆ ಪಾವತಿಸಲಾಗುತ್ತದೆ."))],
            "signatory": {"name": ctx.t(L("District Employment Officer", "ಜಿಲ್ಲಾ ಉದ್ಯೋಗ ಅಧಿಕಾರಿ")), "designation": dist}})
        msg = ctx.t(L(f"*Yuvanidhi - Application Submitted*\n\nApplication No: *{app}*\nApplicant: {v['name']}\nQualification: {ctx.t(QUALS[v['qual']][0])}\n"
                      f"Eligible allowance: *₹{amt:,} per month*\n\nYour application will be verified against Aadhaar, the marks card and EPFO/ESI employment records.",
                      f"*ಯುವನಿಧಿ - ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: *{app}*\nಅರ್ಜಿದಾರರು: {v['name']}\nವಿದ್ಯಾರ್ಹತೆ: {ctx.t(QUALS[v['qual']][0])}\n"
                      f"ಅರ್ಹ ಭತ್ಯೆ: *ತಿಂಗಳಿಗೆ ₹{amt:,}*\n\nನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ಆಧಾರ್, ಅಂಕಪಟ್ಟಿ ಮತ್ತು EPFO/ESI ಉದ್ಯೋಗ ದಾಖಲೆಗಳೊಂದಿಗೆ ಪರಿಶೀಲಿಸಲಾಗುವುದು."))
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(
            ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"status:{app}"))))

    def _status(self, ctx, app):
        rec = self._record(ctx, app)
        amt = QUALS[rec["qual"]][1]
        head = ctx.t(L(f"*Yuvanidhi - Application Status*\n\nApplication No: {app}\nApplicant: {rec['name']}\nQualification: {ctx.t(QUALS[rec['qual']][0])} - ₹{amt:,} per month\n\n",
                       f"*ಯುವನಿಧಿ - ಅರ್ಜಿ ಸ್ಥಿತಿ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: {app}\nಅರ್ಜಿದಾರರು: {rec['name']}\nವಿದ್ಯಾರ್ಹತೆ: {ctx.t(QUALS[rec['qual']][0])} - ತಿಂಗಳಿಗೆ ₹{amt:,}\n\n"))
        msg = head + timeline(ctx, STAGES, rec["stage"])
        btns = []
        if rec["stage"] < len(STAGES) - 1:
            msg += ctx.t(L("\n\n_Status updates automatically. Check again shortly._", "\n\n_ಸ್ಥಿತಿ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನವೀಕರಣಗೊಳ್ಳುತ್ತದೆ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪರಿಶೀಲಿಸಿ._"))
            btns.append(self.btn(ctx.t(L("Refresh Status", "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ")), f"status:{app}"))
        else:
            r = rec.get("r") or gen.rng("ynpay", app)
            lines = []
            for i, m in enumerate(gen.months_back(4)):
                if i == 0 and gen.today().day < 20:
                    lines.append(f"{gen.month_year(m, ctx.lang)} - {ctx.t(L('Processing', 'ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ'))}")
                else:
                    lines.append(f"{gen.month_year(m, ctx.lang)} - *₹{amt:,}* ({ctx.t(L('credited', 'ಜಮೆ'))} {min(r.randint(5, 25), 28):02d}-{m.month:02d})")
            msg += "\n\n" + ctx.t(L("*Recent payments:*\n", "*ಇತ್ತೀಚಿನ ಪಾವತಿಗಳು:*\n")) + "\n".join(lines)
            month = gen.month_year(gen.today(), ctx.lang)
            if db.rec_get("yn_decl", f"{app}:{gen.today():%Y%m}"):
                msg += ctx.t(L(f"\n\nSelf-declaration for {month}: *Submitted*", f"\n\n{month} ಸ್ವಯಂ ಘೋಷಣೆ: *ಸಲ್ಲಿಸಲಾಗಿದೆ*"))
            else:
                msg += ctx.t(L(f"\n\nMonthly self-declaration for *{month}* is pending. Submit it before the 25th to receive this month's allowance.",
                               f"\n\n*{month}* ರ ಮಾಸಿಕ ಸ್ವಯಂ ಘೋಷಣೆ ಬಾಕಿ ಇದೆ. ಈ ತಿಂಗಳ ಭತ್ಯೆ ಪಡೆಯಲು 25ನೇ ತಾರೀಖಿನೊಳಗೆ ಸಲ್ಲಿಸಿ."))
                btns.append(self.btn(ctx.t(L("Submit Self-Declaration", "ಸ್ವಯಂ ಘೋಷಣೆ ಸಲ್ಲಿಸಿ")), f"declare:{app}"))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx, *btns)))

    def _declare_prompt(self, ctx, app):
        return self._declare(ctx, app)

    def _declare(self, ctx, app):
        rec = self._record(ctx, app)
        month = gen.month_year(gen.today(), ctx.lang)
        if rec["stage"] < len(STAGES) - 1:
            return Reply(ui.text(ctx.t(L(f"Application {app} is still under verification. The monthly self-declaration opens once the application is approved.",
                                         f"ಅರ್ಜಿ {app} ಇನ್ನೂ ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ. ಅರ್ಜಿ ಅನುಮೋದನೆಯಾದ ನಂತರ ಮಾಸಿಕ ಸ್ವಯಂ ಘೋಷಣೆ ತೆರೆಯುತ್ತದೆ.")),
                                 buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"status:{app}"))))
        if db.rec_get("yn_decl", f"{app}:{gen.today():%Y%m}"):
            return Reply(ui.text(ctx.t(L(f"The self-declaration for {month} has already been submitted for application {app}.",
                                         f"ಅರ್ಜಿ {app} ಗೆ {month} ರ ಸ್ವಯಂ ಘೋಷಣೆಯನ್ನು ಈಗಾಗಲೇ ಸಲ್ಲಿಸಲಾಗಿದೆ.")), buttons=self.menu_buttons(ctx)))
        db.rec_put("yn_decl", f"{app}:{gen.today():%Y%m}", {"at": gen.dmy(gen.today())}, ctx.session_id)
        amt = QUALS[rec["qual"]][1]
        msg = ctx.t(L(f"*Self-declaration submitted*\n\nApplication No: {app}\nMonth: {month}\nApplicant: {rec['name']}\n\n"
                      f"Declaration: I am not employed and not pursuing higher studies during {month}.\n\nThe allowance of ₹{amt:,} for this month will be credited through DBT.",
                      f"*ಸ್ವಯಂ ಘೋಷಣೆ ಸಲ್ಲಿಸಲಾಗಿದೆ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: {app}\nತಿಂಗಳು: {month}\nಅರ್ಜಿದಾರರು: {rec['name']}\n\n"
                      f"ಘೋಷಣೆ: {month} ರಲ್ಲಿ ನಾನು ಉದ್ಯೋಗದಲ್ಲಿಲ್ಲ ಮತ್ತು ಉನ್ನತ ವ್ಯಾಸಂಗ ಮಾಡುತ್ತಿಲ್ಲ.\n\nಈ ತಿಂಗಳ ₹{amt:,} ಭತ್ಯೆಯನ್ನು ಡಿಬಿಟಿ ಮೂಲಕ ಜಮೆ ಮಾಡಲಾಗುವುದು."))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx)))

    def on_button(self, ctx, arg):
        kind, _, app = arg.partition(":")
        if kind == "status":
            return self._status(ctx, app)
        if kind == "declare":
            return self._declare(ctx, app)
        return None

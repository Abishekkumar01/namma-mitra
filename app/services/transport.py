"""Transport Department - Vahan and Sarathi services.

Seva One services covered: "Issue of RC Extract of Vehicles", "Driving License Extract",
"Renewal of Driving License".
RC extract and DL extract for any well-formed number; DL renewal with fee, acknowledgement and renewed DL PDF.
"""
import datetime as dt

from .. import db, docs, payments, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service

DEPT = L("Transport Department", "ಸಾರಿಗೆ ಇಲಾಖೆ")
VEH_RE = r"^KA\d{2}[A-Z]{0,3}\d{1,4}$"
DL_RE = r"^KA\d{13}$"
RENEW_FEE = 400   # ₹200 renewal + ₹200 smart card (indicative)


def vehicle(reg):
    r = gen.rng("vahan", reg)
    model, fuel, vclass, two = r.choice(K.VEHICLES)
    reg_date = dt.date(r.randint(2012, 2025), r.randint(1, 12), r.randint(1, 28))
    rto = K.RTO.get(reg[2:4], (f"RTO KA-{reg[2:4]}", f"ಆರ್‌ಟಿಒ ಕೆಎ-{reg[2:4]}"))
    today = gen.today()
    return {"owner": gen.person(r)["name"], "model": model, "fuel": fuel, "vclass": vclass, "two": two,
            "reg_date": reg_date, "rto": L(*rto), "ins": today + dt.timedelta(days=r.randint(-60, 330)),
            "puc": today + dt.timedelta(days=r.randint(-30, 180)), "fitness": reg_date.replace(year=reg_date.year + 15),
            "insurer": r.choice(["New India Assurance", "United India Insurance", "ICICI Lombard", "Bajaj Allianz"]),
            "chassis": "MA3" + gen.digits(r, 14).upper(), "engine": "K12M" + gen.digits(r, 7),
            "colour": r.choice([L("White", "ಬಿಳಿ"), L("Silver", "ಬೆಳ್ಳಿ"), L("Grey", "ಬೂದು"), L("Red", "ಕೆಂಪು"), L("Black", "ಕಪ್ಪು"), L("Blue", "ನೀಲಿ")])}


def licence(ctx, dl_no, dob):
    r = gen.rng("dl", dl_no)
    born = dt.date.fromisoformat(dob)
    year = int(dl_no[4:8])
    issue_year = year if 1980 <= year <= gen.today().year else r.randint(2005, 2024)
    issued = dt.date(issue_year, r.randint(1, 12), r.randint(1, 28))
    valid = issued.replace(year=issued.year + 20)
    if born.year + 50 < valid.year and born.replace(year=born.year + 50) > gen.today():
        valid = born.replace(year=born.year + 50)
    rto = K.RTO.get(dl_no[2:4], (f"RTO KA-{dl_no[2:4]}", f"ಆರ್‌ಟಿಒ ಕೆಎ-{dl_no[2:4]}"))
    renewed = db.rec_get("dl_renewed", dl_no)
    if renewed:
        valid = dt.date.fromisoformat(renewed["valid"])
    return {"name": ctx.t(gen.person(r)["name"]), "born": born, "issued": issued, "valid": valid, "rto": L(*rto),
            "classes": r.choice(["MCWG, LMV", "LMV", "MCWG", "MCWG, LMV, LMV-TR"]), "blood": r.choice(["A+", "B+", "O+", "AB+", "O-"]),
            "renewed": renewed}


class Transport(Service):
    key = "transport"
    order = 9
    icon = "vehicle"
    title = L("Transport Department Services", "ಸಾರಿಗೆ ಇಲಾಖೆ ಸೇವೆಗಳು")
    subtitle = L("RC extract, driving licence extract and renewal", "ಆರ್‌ಸಿ ವಿವರ, ಚಾಲನಾ ಪರವಾನಗಿ ವಿವರ ಮತ್ತು ನವೀಕರಣ")
    dept = DEPT
    sevaone = [L("Issue of RC Extract of Vehicles"), L("Driving License Extract"), L("Renewal of Driving License")]
    keywords = ["vehicle", "rc", "rc extract", "registration certificate", "driving licence", "driving license", "dl", "renew",
                "renewal", "rto", "insurance", "ವಾಹನ", "ಚಾಲನಾ", "ಪರವಾನಗಿ", "ನವೀಕರಣ", "ಆರ್‌ಸಿ"]

    def fields(self, ctx):
        dl = {"action": ["dl", "renew"]}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("rc", L("Issue of RC Extract of Vehicle", "ವಾಹನ ಆರ್‌ಸಿ ವಿವರ (RC Extract)")),
                fk.opt("dl", L("Driving Licence Extract", "ಚಾಲನಾ ಪರವಾನಗಿ ವಿವರ")),
                fk.opt("renew", L("Renewal of Driving Licence", "ಚಾಲನಾ ಪರವಾನಗಿ ನವೀಕರಣ"))]),
            fk.text("vehicle", L("Enter Vehicle Number", "ವಾಹನ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": "rc"},
                    placeholder="KA01AB1234", transform="upper_nospace", pattern=VEH_RE,
                    error=L("Enter a Karnataka vehicle number like KA01AB1234", "KA01AB1234 ರೀತಿಯ ಕರ್ನಾಟಕ ವಾಹನ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ")),
            fk.text("dl_no", L("Enter Driving Licence Number", "ಚಾಲನಾ ಪರವಾನಗಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if=dl,
                    placeholder="KA0120190001234", transform="upper_nospace", pattern=DL_RE,
                    error=L("DL number looks like KA0120190001234", "ಡಿಎಲ್ ಸಂಖ್ಯೆ KA0120190001234 ರೀತಿ ಇರುತ್ತದೆ")),
            fk.date("dob", L("Date of Birth", "ಜನ್ಮ ದಿನಾಂಕ"), min_days=-365 * 90, max_days=-365 * 16, show_if=dl),
            fk.text("mobile", L("Mobile Number (for the renewed licence)", "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ (ನವೀಕೃತ ಪರವಾನಗಿಗಾಗಿ)"), show_if={"action": "renew"},
                    placeholder="9876543210", transform="digits", pattern=r"^[6-9]\d{9}$", input_mode="numeric",
                    error=L("Enter a valid 10-digit mobile number", "ಮಾನ್ಯ 10 ಅಂಕಿಯ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ")),
        ]

    def prefill(self, text):
        t = text.lower()
        if any(w in t for w in ("renew", "ನವೀಕರಣ")):
            return {"action": "renew"}
        if any(w in t for w in ("licence", "license", " dl", "ಪರವಾನಗಿ", "ಚಾಲನಾ")):
            return {"action": "dl"}
        return {"action": "rc"}

    def submit(self, ctx, screen, v, data):
        if v["action"] == "rc":
            if gen.is_missing(v["vehicle"][4:]):
                return Errors({"vehicle": L("No vehicle found with this registration number.", "ಈ ನೋಂದಣಿ ಸಂಖ್ಯೆಯ ವಾಹನ ಕಂಡುಬಂದಿಲ್ಲ.")})
            return self._rc(ctx, v["vehicle"])
        if gen.is_missing(v["dl_no"][4:]):
            return Errors({"dl_no": L("No licence found for this number and date of birth.", "ಈ ಸಂಖ್ಯೆ ಮತ್ತು ಜನ್ಮ ದಿನಾಂಕಕ್ಕೆ ಪರವಾನಗಿ ಕಂಡುಬಂದಿಲ್ಲ.")})
        return self._dl(ctx, v["dl_no"], v["dob"]) if v["action"] == "dl" else self._renew(ctx, v["dl_no"], v["dob"], v["mobile"])

    def _validity(self, ctx, d):
        days = (d - gen.today()).days
        if days < 0:
            return f"{gen.dmy(d)} ({ctx.t(L('EXPIRED', 'ಅವಧಿ ಮುಗಿದಿದೆ'))})"
        if days < 30:
            return f"{gen.dmy(d)} ({ctx.t(L(f'expires in {days} days', f'{days} ದಿನಗಳಲ್ಲಿ ಮುಕ್ತಾಯ'))})"
        return gen.dmy(d)

    # ---------------------------------------------------------------------
    def _rc(self, ctx, reg):
        x = vehicle(reg)
        fuel = x["fuel"] if not ctx.kn else K.FUEL_KN[x["fuel"]]
        masked = gen.mask_name(ctx.t(x["owner"]))
        msg = ctx.t(L(f"*RC Extract (Vahan)*\n\nRegistration No: *{reg}*\nOwner: {masked}\nVehicle: {x['model']} ({ctx.t(x['colour'])})\nFuel: {fuel}\nClass: {x['vclass']}\n"
                      f"Registered: {gen.dmy(x['reg_date'])}\nRTO: {ctx.t(x['rto'])}\n\nInsurance: {self._validity(ctx, x['ins'])}\nInsurer: {x['insurer']}\n"
                      f"PUC: {self._validity(ctx, x['puc'])}\nRegistration valid till: {gen.dmy(x['fitness'])}\nRoad Tax: Lifetime (paid)",
                      f"*ಆರ್‌ಸಿ ವಿವರ (ವಾಹನ್)*\n\nನೋಂದಣಿ ಸಂಖ್ಯೆ: *{reg}*\nಮಾಲೀಕರು: {masked}\nವಾಹನ: {x['model']} ({ctx.t(x['colour'])})\nಇಂಧನ: {fuel}\nವರ್ಗ: {x['vclass']}\n"
                      f"ನೋಂದಣಿ: {gen.dmy(x['reg_date'])}\nಆರ್‌ಟಿಒ: {ctx.t(x['rto'])}\n\nವಿಮೆ: {self._validity(ctx, x['ins'])}\nವಿಮಾ ಸಂಸ್ಥೆ: {x['insurer']}\n"
                      f"ಪಿಯುಸಿ: {self._validity(ctx, x['puc'])}\nನೋಂದಣಿ ಮಾನ್ಯತೆ: {gen.dmy(x['fitness'])}\nರಸ್ತೆ ತೆರಿಗೆ: ಜೀವಿತಾವಧಿ (ಪಾವತಿಸಲಾಗಿದೆ)"))
        fname = f"RC_Extract_{reg}.pdf"
        doc_id = docs.create(ctx.session_id, "rc_extract", fname, {
            "lang": ctx.lang, "place": ctx.t(x["rto"]).split(" (")[0], "verify_url": "parivahan.gov.in",
            "dept": ctx.t(DEPT), "dept_sub": ctx.t(L("Vahan - Registration of Motor Vehicles", "ವಾಹನ್ - ಮೋಟಾರು ವಾಹನಗಳ ನೋಂದಣಿ")),
            "title": ctx.t(L("RC EXTRACT", "ಆರ್‌ಸಿ ವಿವರ")), "ref_label": ctx.t(L("Registration No", "ನೋಂದಣಿ ಸಂಖ್ಯೆ")), "ref": reg,
            "sections": [{"rows": [[ctx.t(L("Owner", "ಮಾಲೀಕರು")), ctx.t(x["owner"])], [ctx.t(L("Vehicle", "ವಾಹನ")), f"{x['model']} ({ctx.t(x['colour'])})"],
                                   [ctx.t(L("Chassis No", "ಚಾಸಿಸ್ ಸಂಖ್ಯೆ")), x["chassis"]], [ctx.t(L("Engine No", "ಎಂಜಿನ್ ಸಂಖ್ಯೆ")), x["engine"]],
                                   [ctx.t(L("Fuel / Class", "ಇಂಧನ / ವರ್ಗ")), f"{fuel} / {x['vclass']}"], [ctx.t(L("Registration date", "ನೋಂದಣಿ ದಿನಾಂಕ")), gen.dmy(x["reg_date"])],
                                   [ctx.t(L("Registration valid till", "ನೋಂದಣಿ ಮಾನ್ಯತೆ")), gen.dmy(x["fitness"])], [ctx.t(L("RTO", "ಆರ್‌ಟಿಒ")), ctx.t(x["rto"])],
                                   [ctx.t(L("Insurance valid till", "ವಿಮೆ ಮಾನ್ಯತೆ")), f"{gen.dmy(x['ins'])} ({x['insurer']})"], [ctx.t(L("PUC valid till", "ಪಿಯುಸಿ ಮಾನ್ಯತೆ")), gen.dmy(x["puc"])]]}],
            "notes": [ctx.t(L("Extract of the Certificate of Registration as recorded in the Vahan database.", "ವಾಹನ್ ದತ್ತಸಂಚಯದಲ್ಲಿ ದಾಖಲಾದ ನೋಂದಣಿ ಪ್ರಮಾಣಪತ್ರದ ವಿವರ."))],
            "signatory": {"name": ctx.t(L("Regional Transport Officer", "ಪ್ರಾದೇಶಿಕ ಸಾರಿಗೆ ಅಧಿಕಾರಿ")), "designation": ctx.t(x["rto"])}})
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx)))

    def _dl_doc(self, ctx, dl_no, d, title, extra_rows=()):
        fname = f"{title.replace(' ', '_')}_{dl_no}.pdf"
        doc_id = docs.create(ctx.session_id, "dl_extract", fname, {
            "lang": ctx.lang, "place": ctx.t(d["rto"]).split(" (")[0], "verify_url": "sarathi.parivahan.gov.in",
            "dept": ctx.t(DEPT), "dept_sub": ctx.t(L("Sarathi - Driving Licence", "ಸಾರಥಿ - ಚಾಲನಾ ಪರವಾನಗಿ")),
            "title": ctx.t(L("DRIVING LICENCE EXTRACT", "ಚಾಲನಾ ಪರವಾನಗಿ ವಿವರ")) if title == "DL Extract" else ctx.t(L("RENEWED DRIVING LICENCE", "ನವೀಕೃತ ಚಾಲನಾ ಪರವಾನಗಿ")),
            "ref_label": ctx.t(L("DL No", "ಡಿಎಲ್ ಸಂಖ್ಯೆ")), "ref": dl_no,
            "highlight": {"label": ctx.t(L("Valid till (Non-Transport)", "ಮಾನ್ಯತೆ (ಸಾರಿಗೇತರ)")), "value": gen.dmy(d["valid"])},
            "sections": [{"rows": [[ctx.t(L("Name", "ಹೆಸರು")), d["name"]], [ctx.t(L("Date of Birth", "ಜನ್ಮ ದಿನಾಂಕ")), gen.dmy(d["born"])],
                                   [ctx.t(L("Blood Group", "ರಕ್ತದ ಗುಂಪು")), d["blood"]], [ctx.t(L("Class of Vehicles", "ವಾಹನ ವರ್ಗ")), d["classes"]],
                                   [ctx.t(L("Date of Issue", "ವಿತರಣಾ ದಿನಾಂಕ")), gen.dmy(d["issued"])], [ctx.t(L("Issuing RTO", "ವಿತರಿಸಿದ ಆರ್‌ಟಿಒ")), ctx.t(d["rto"])]] + list(extra_rows)}],
            "signatory": {"name": ctx.t(L("Licensing Authority", "ಪರವಾನಗಿ ಪ್ರಾಧಿಕಾರ")), "designation": ctx.t(d["rto"])}})
        return doc_id, fname

    def _dl(self, ctx, dl_no, dob):
        d = licence(ctx, dl_no, dob)
        msg = ctx.t(L(f"*Driving Licence Extract (Sarathi)*\n\nDL No: {dl_no}\nName: {d['name']}\nDOB: {gen.dmy(d['born'])}\nStatus: *ACTIVE*\n\n"
                      f"Class of vehicles: *{d['classes']}*\nIssued: {gen.dmy(d['issued'])}\nValid till (Non-Transport): {self._validity(ctx, d['valid'])}\nRTO: {ctx.t(d['rto'])}",
                      f"*ಚಾಲನಾ ಪರವಾನಗಿ ವಿವರ (ಸಾರಥಿ)*\n\nಡಿಎಲ್ ಸಂಖ್ಯೆ: {dl_no}\nಹೆಸರು: {d['name']}\nಜನ್ಮ ದಿನಾಂಕ: {gen.dmy(d['born'])}\nಸ್ಥಿತಿ: *ಸಕ್ರಿಯ*\n\n"
                      f"ವಾಹನ ವರ್ಗ: *{d['classes']}*\nವಿತರಣೆ: {gen.dmy(d['issued'])}\nಮಾನ್ಯತೆ (ಸಾರಿಗೇತರ): {self._validity(ctx, d['valid'])}\nಆರ್‌ಟಿಒ: {ctx.t(d['rto'])}"))
        doc_id, fname = self._dl_doc(ctx, dl_no, d, "DL Extract")
        btn = [] if d["renewed"] else [self.btn(ctx.t(L("Renew this Licence", "ಈ ಪರವಾನಗಿ ನವೀಕರಿಸಿ")), f"renew:{dl_no}:{dob}")]
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx, *btn)))

    def _renew(self, ctx, dl_no, dob, mobile="-"):
        d = licence(ctx, dl_no, dob)
        if d["renewed"]:
            return Reply(ui.text(ctx.t(L(f"Licence *{dl_no}* was already renewed on {d['renewed']['on']} and is valid till *{gen.dmy(d['valid'])}*.",
                                         f"ಪರವಾನಗಿ *{dl_no}* ಅನ್ನು {d['renewed']['on']} ರಂದು ಈಗಾಗಲೇ ನವೀಕರಿಸಲಾಗಿದೆ ಮತ್ತು *{gen.dmy(d['valid'])}* ವರೆಗೆ ಮಾನ್ಯವಾಗಿದೆ.")),
                                 buttons=self.menu_buttons(ctx)))
        app = "DLR" + dt.date.today().strftime("%y%m%d") + gen.ref_id("", 4)
        db.rec_put("dl_renew_app", app, {"dl_no": dl_no, "dob": dob, "mobile": mobile}, ctx.session_id)
        pid = payments.create(ctx.session_id, self.key, ctx.t(L("Driving Licence renewal fee", "ಚಾಲನಾ ಪರವಾನಗಿ ನವೀಕರಣ ಶುಲ್ಕ")), RENEW_FEE, app)
        msg = ctx.t(L(f"*Renewal of Driving Licence*\n\nApplication No: *{app}*\nDL No: {dl_no}\nName: {d['name']}\nCurrent validity: {self._validity(ctx, d['valid'])}\n\n"
                      f"Fee: *₹{RENEW_FEE}.00* (renewal ₹200 + smart card ₹200)\nPay the fee to renew the licence for 5 years.",
                      f"*ಚಾಲನಾ ಪರವಾನಗಿ ನವೀಕರಣ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: *{app}*\nಡಿಎಲ್ ಸಂಖ್ಯೆ: {dl_no}\nಹೆಸರು: {d['name']}\nಪ್ರಸ್ತುತ ಮಾನ್ಯತೆ: {self._validity(ctx, d['valid'])}\n\n"
                      f"ಶುಲ್ಕ: *₹{RENEW_FEE}.00* (ನವೀಕರಣ ₹200 + ಸ್ಮಾರ್ಟ್ ಕಾರ್ಡ್ ₹200)\n5 ವರ್ಷಗಳಿಗೆ ಪರವಾನಗಿ ನವೀಕರಿಸಲು ಶುಲ್ಕ ಪಾವತಿಸಿ."))
        return Reply(ui.text(msg, cta=ui.cta_pay(ctx.s("pay", amt=f"₹{RENEW_FEE}.00"), pid), buttons=self.menu_buttons(ctx)))

    def on_payment(self, ctx, p):
        rec = db.rec_get("dl_renew_app", p["ref"])
        if not rec:
            return [ui.text(ctx.s("payment_missing"))]
        d = licence(ctx, rec["dl_no"], rec["dob"])
        base = max(d["valid"], gen.today())
        new_valid = base.replace(year=base.year + 5)
        db.rec_put("dl_renewed", rec["dl_no"], {"valid": new_valid.isoformat(), "on": gen.dmy(gen.today()), "app": p["ref"], "txn": p["txn_id"]}, ctx.session_id)
        d = licence(ctx, rec["dl_no"], rec["dob"])
        doc_id, fname = self._dl_doc(ctx, rec["dl_no"], d, "Renewed DL", [
            [ctx.t(L("Renewed on", "ನವೀಕರಿಸಿದ ದಿನಾಂಕ")), gen.dmy(gen.today())], [ctx.t(L("Renewal application", "ನವೀಕರಣ ಅರ್ಜಿ")), p["ref"]],
            [ctx.t(L("Fee paid", "ಪಾವತಿಸಿದ ಶುಲ್ಕ")), f"{gen.inr(p['amount'])} ({p['method']})"], [ctx.t(L("Transaction ID", "ವಹಿವಾಟು ಸಂಖ್ಯೆ")), p["txn_id"]]])
        msg = ctx.t(L(f"*Driving Licence Renewed*\n\nDL No: *{rec['dl_no']}*\nName: {d['name']}\nNew validity: *{gen.dmy(new_valid)}*\nTxn ID: {p['txn_id']}\n\n"
                      f"The smart card will be posted to the registered address within 15 days. The renewed e-licence is attached below.",
                      f"*ಚಾಲನಾ ಪರವಾನಗಿ ನವೀಕರಿಸಲಾಗಿದೆ*\n\nಡಿಎಲ್ ಸಂಖ್ಯೆ: *{rec['dl_no']}*\nಹೆಸರು: {d['name']}\nಹೊಸ ಮಾನ್ಯತೆ: *{gen.dmy(new_valid)}*\nವಹಿವಾಟು ಸಂಖ್ಯೆ: {p['txn_id']}\n\n"
                      f"ಸ್ಮಾರ್ಟ್ ಕಾರ್ಡ್ ಅನ್ನು 15 ದಿನಗಳೊಳಗೆ ನೋಂದಾಯಿತ ವಿಳಾಸಕ್ಕೆ ಅಂಚೆ ಮೂಲಕ ಕಳುಹಿಸಲಾಗುವುದು. ನವೀಕೃತ ಇ-ಪರವಾನಗಿ ಕೆಳಗೆ ಲಗತ್ತಿಸಲಾಗಿದೆ."))
        return [ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx))]

    def on_button(self, ctx, arg):
        if arg.startswith("renew:"):
            _, dl_no, dob = arg.split(":", 2)
            return self._renew(ctx, dl_no, dob)
        return None

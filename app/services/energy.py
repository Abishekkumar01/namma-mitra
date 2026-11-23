"""Energy Department - ESCOMs (BESCOM, MESCOM, HESCOM, GESCOM, CESC).

View bill (any 10-digit Account ID) -> Gruha Jyothi zero-bill logic -> pay -> receipt PDF.
Register complaint -> docket number -> track (stages advance with time).
"""
import datetime as dt
import time

from .. import db, docs, payments, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service, stage_from_elapsed, timeline

CTYPES = {
    "outage": L("Power Outage / No Supply", "ವಿದ್ಯುತ್ ಸ್ಥಗಿತ / ಪೂರೈಕೆ ಇಲ್ಲ"),
    "voltage": L("Low / High Voltage", "ಕಡಿಮೆ / ಹೆಚ್ಚು ವೋಲ್ಟೇಜ್"),
    "meter": L("Meter Faulty / Burnt", "ಮೀಟರ್ ದೋಷ / ಸುಟ್ಟಿದೆ"),
    "transformer": L("Transformer Problem", "ಟ್ರಾನ್ಸ್‌ಫಾರ್ಮರ್ ಸಮಸ್ಯೆ"),
    "line": L("Fallen Wire / Pole Danger", "ತುಂಡಾದ ತಂತಿ / ಕಂಬ ಅಪಾಯ"),
    "billing": L("Billing Dispute", "ಬಿಲ್ ವಿವಾದ"),
}
C_STAGES = [L("Complaint registered", "ದೂರು ದಾಖಲಾಗಿದೆ"),
            L("Assigned to Section Officer", "ಶಾಖಾಧಿಕಾರಿಗೆ ನಿಯೋಜಿಸಲಾಗಿದೆ"),
            L("Lineman dispatched to site", "ಲೈನ್‌ಮ್ಯಾನ್ ಸ್ಥಳಕ್ಕೆ ತೆರಳಿದ್ದಾರೆ"),
            L("Resolved - supply restored", "ಪರಿಹರಿಸಲಾಗಿದೆ - ಪೂರೈಕೆ ಮರುಸ್ಥಾಪನೆ")]
ACC = r"^\d{10}$"
# LT-2(a) domestic tariff, FY 2025-26 (KERC order, March 2025): energy charge Rs 5.80/unit,
# fixed charge Rs 145/kW/month, P&G pension surcharge 36 paise/unit, electricity tax 9% on energy charges.
ENERGY_RATE = 5.80
FIXED_PER_KW = 145
PENSION_SURCHARGE = 0.36
TAX_RATE = 0.09
GJ_CAP = 200


def bill_breakup(units, load, gj, entitled):
    """Itemised domestic bill. Gruha Jyothi: free up to the entitlement; above it only the extra
    units are billed; above 200 units the subsidy does not apply for that month."""
    fixed = round(FIXED_PER_KW * load, 2)
    energy = round(units * ENERGY_RATE, 2)
    surcharge = round(units * PENSION_SURCHARGE, 2)
    tax = round(energy * TAX_RATE, 2)
    gross = round(fixed + energy + surcharge + tax, 2)
    if not gj or units > GJ_CAP:
        net = gross
    elif units <= entitled:
        net = 0.0
    else:
        extra = units - entitled
        net = round(extra * ENERGY_RATE * (1 + TAX_RATE) + extra * PENSION_SURCHARGE, 2)
    return {"fixed": fixed, "energy": energy, "surcharge": surcharge, "tax": tax, "gross": gross,
            "subsidy": round(gross - net, 2), "net": net, "over_cap": gj and units > GJ_CAP}


ESCOM_HQ = {"bescom": L("Bengaluru", "ಬೆಂಗಳೂರು"), "mescom": L("Mangaluru", "ಮಂಗಳೂರು"), "hescom": L("Hubballi", "ಹುಬ್ಬಳ್ಳಿ"),
            "gescom": L("Kalaburagi", "ಕಲಬುರಗಿ"), "cesc": L("Mysuru", "ಮೈಸೂರು")}
ESCOM_WEB = {"bescom": "bescom.karnataka.gov.in", "mescom": "mescom.karnataka.gov.in", "hescom": "hescom.karnataka.gov.in",
             "gescom": "gescom.karnataka.gov.in", "cesc": "cescmysore.karnataka.gov.in"}


def consumer(escom, account):
    """Deterministic consumer + current bill for an account."""
    r = gen.rng("escom", escom, account)
    p = gen.person(r)
    area_en, area_kn, city_en, city_kn = r.choice(K.LOCALITIES[escom])
    n, cross = r.randint(1, 480), r.randint(1, 18)
    load = r.choice([1, 2, 2, 3, 4, 5])
    avg = r.randint(55, 190)                       # 12-month average units (Gruha Jyothi base)
    gj = r.random() < 0.85                         # registered under Gruha Jyothi
    entitled = min(200, round(avg * 1.10)) if gj else 0
    units = max(20, int(avg * r.uniform(0.75, 1.45)))
    # Memorable demo accounts pinned to the interesting paths (see data/TEST_DATA.md)
    if account == "1234567890":          # Gruha Jyothi zero bill
        gj, entitled = True, min(200, round(avg * 1.10))
        units = max(20, entitled - r.randint(8, 30))
    elif account == "9876543210":        # Gruha Jyothi but exceeded -> payable bill
        gj, entitled = True, min(200, round(avg * 1.10))
        units = entitled + r.randint(35, 80)
    elif account == "1111111111":        # not registered -> full bill
        gj, entitled = False, 0
    bill_date = gen.today() - dt.timedelta(days=r.randint(2, 9))
    due = bill_date + dt.timedelta(days=15)
    b = bill_breakup(units, load, gj, entitled)
    net, gj_benefit = b["net"], b["subsidy"]
    return {"name": p["name"], "address": L(f"#{n}, {cross}th Cross, {area_en}, {city_en}",
                                            f"#{n}, {cross}ನೇ ಅಡ್ಡರಸ್ತೆ, {area_kn}, {city_kn}"),
            "load": load, "avg": avg, "gj": gj, "entitled": entitled, "units": units,
            "bill_date": bill_date.isoformat(), "due": due.isoformat(), "net": net,
            "gj_benefit": gj_benefit, "breakup": b, "rr": f"{city_en[:3].upper()}{r.randint(10, 99)}-{r.randint(1000, 9999)}",
            "subdiv": L(f"{area_en} Sub-Division", f"{area_kn} ಉಪವಿಭಾಗ")}


class Energy(Service):
    key = "energy"
    order = 2
    icon = "energy"
    title = L("Electricity Services (ESCOMs)", "ವಿದ್ಯುತ್ ಸೇವೆಗಳು (ಎಸ್ಕಾಂ)")
    dept = L("Energy Department - BESCOM, MESCOM, HESCOM, GESCOM, CESC", "ಇಂಧನ ಇಲಾಖೆ - ಬೆಸ್ಕಾಂ, ಮೆಸ್ಕಾಂ, ಹೆಸ್ಕಾಂ, ಜೆಸ್ಕಾಂ, ಸೆಸ್ಕ್")
    sevaone = [L("Online Bill Payment - RAPDRP Towns"), L("PGRS (Compliant Registration)"), L("Meter Complaints"), L("Line breakdown- City/Town areas")]
    subtitle = L("Online bill payment, PGRS complaint registration", "ವಿದ್ಯುತ್ ಬಿಲ್ ಪಾವತಿ, ದೂರುಗಳು ಮತ್ತು ಇನ್ನಷ್ಟು")
    keywords = ["electricity", "current bill", "power", "bescom", "mescom", "hescom", "gescom", "cesc",
                "light bill", "power cut", "eb bill", "vidyut", "electric", "ವಿದ್ಯುತ್", "ಕರೆಂಟ್", "ಬೆಸ್ಕಾಂ", "ಬಿಲ್", "bill"]

    def fields(self, ctx):
        acc_show = {"action": ["bill", "complaint"]}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("bill", L("View & Pay Electricity Bill", "ವಿದ್ಯುತ್ ಬಿಲ್ ವೀಕ್ಷಿಸಿ ಮತ್ತು ಪಾವತಿಸಿ")),
                fk.opt("complaint", L("Register Power Complaint", "ವಿದ್ಯುತ್ ದೂರು ದಾಖಲಿಸಿ")),
                fk.opt("track", L("Track Complaint Status", "ದೂರಿನ ಸ್ಥಿತಿ ತಿಳಿಯಿರಿ")),
            ]),
            fk.radio("escom", L("Select your ESCOM", "ನಿಮ್ಮ ಎಸ್ಕಾಂ ಆಯ್ಕೆಮಾಡಿ"), K.ESCOM_OPTIONS, show_if=acc_show),
            fk.text("account", L("Enter your Account ID", "ನಿಮ್ಮ ಖಾತೆ ಸಂಖ್ಯೆ (Account ID) ನಮೂದಿಸಿ"), show_if=acc_show,
                    placeholder="1234567890", transform="digits", pattern=ACC, input_mode="numeric",
                    helper=L("10-digit number printed on top of your bill", "ನಿಮ್ಮ ಬಿಲ್‌ನ ಮೇಲ್ಭಾಗದಲ್ಲಿರುವ 10 ಅಂಕಿಯ ಸಂಖ್ಯೆ"),
                    error=L("Account ID must be 10 digits", "ಖಾತೆ ಸಂಖ್ಯೆ 10 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.radio("ctype", L("Complaint Type", "ದೂರಿನ ಪ್ರಕಾರ"), [fk.opt(k, v) for k, v in CTYPES.items()],
                     show_if={"action": "complaint"}),
            fk.textarea("details", L("Describe the problem", "ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ"), required=False,
                        show_if={"action": "complaint"},
                        placeholder=L("e.g. No power since 6 AM in our street", "ಉದಾ: ಬೆಳಿಗ್ಗೆ 6 ರಿಂದ ನಮ್ಮ ರಸ್ತೆಯಲ್ಲಿ ವಿದ್ಯುತ್ ಇಲ್ಲ")),
            fk.text("docket", L("Enter Complaint Number", "ದೂರಿನ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": "track"},
                    placeholder="BES2611224821", transform="upper_nospace", pattern=r"^[A-Z]{3}\d{10}$",
                    error=L("Complaint number looks like BES2611224821", "ದೂರಿನ ಸಂಖ್ಯೆ BES2611224821 ರೀತಿ ಇರುತ್ತದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        if any(w in t for w in ("track", "status", "ಸ್ಥಿತಿ")) and any(w in t for w in ("complaint", "ದೂರು")):
            return {"action": "track"}
        if any(w in t for w in ("complaint", "power cut", "no power", "outage", "voltage", "ದೂರು", "ಸ್ಥಗಿತ")):
            return {"action": "complaint"}
        out = {"action": "bill"} if any(w in t for w in ("bill", "pay", "ಬಿಲ್", "ಪಾವತಿ")) else {}
        for k in K.ESCOM_PREFIX:
            if k in t or (k == "cesc" and "chamundeshwari" in t):
                out["escom"] = k
        return out

    def submit(self, ctx, screen, v, data):
        if v["action"] == "bill":
            return self.bill(ctx, v["escom"], v["account"])
        if v["action"] == "complaint":
            return self.complaint(ctx, v)
        return self.track(ctx, v["docket"])

    # ---------------------------------------------------------------------
    def _not_found(self, ctx, escom):
        name = ctx.t(K.ESCOM_NAME[escom])
        return Errors({"account": L(f"No consumer found with this Account ID in {name}. Please check and re-enter.",
                                    f"{name} ನಲ್ಲಿ ಈ ಖಾತೆ ಸಂಖ್ಯೆಯ ಗ್ರಾಹಕರು ಕಂಡುಬಂದಿಲ್ಲ. ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ನಮೂದಿಸಿ.")})

    def bill(self, ctx, escom, account):
        if gen.is_missing(account):
            return self._not_found(ctx, escom)
        c = consumer(escom, account)
        bd = dt.date.fromisoformat(c["bill_date"])
        paid = db.rec_get("escom_paid", f"{escom}:{account}:{bd:%Y%m}")
        en = ctx.t(K.ESCOM_NAME[escom])
        gj_line = (ctx.t(L(f"Gruha Jyothi: *{c['entitled']} units free* (avg {c['avg']} units + 10%)",
                           f"ಗೃಹ ಜ್ಯೋತಿ: *{c['entitled']} ಯೂನಿಟ್ ಉಚಿತ* (ಸರಾಸರಿ {c['avg']} + 10%)"))
                   if c["gj"] else ctx.t(L("Not registered under Gruha Jyothi", "ಗೃಹ ಜ್ಯೋತಿಯಲ್ಲಿ ನೋಂದಾಯಿಸಿಲ್ಲ")))
        head = ctx.t(L(
            f"*{en} - Electricity Bill*\n\nConsumer: *{ctx.t(c['name'])}*\nAccount ID: {account}\n"
            f"Address: {ctx.t(c['address'])}\nTariff: LT-2(a) Domestic | {c['load']} kW\n\n"
            f"Bill Month: {gen.month_year(bd, 'en')}\nUnits Consumed: *{c['units']}*\n{gj_line}\n",
            f"*{en} - ವಿದ್ಯುತ್ ಬಿಲ್*\n\nಗ್ರಾಹಕರು: *{ctx.t(c['name'])}*\nಖಾತೆ ಸಂಖ್ಯೆ: {account}\n"
            f"ವಿಳಾಸ: {ctx.t(c['address'])}\nದರ: ಎಲ್‌ಟಿ-2(ಎ) ಗೃಹ ಬಳಕೆ | {c['load']} ಕಿ.ವ್ಯಾ\n\n"
            f"ಬಿಲ್ ತಿಂಗಳು: {gen.month_year(bd, 'kn')}\nಬಳಸಿದ ಯೂನಿಟ್: *{c['units']}*\n{gj_line}\n"))
        b = c["breakup"]
        head += ctx.t(L(
            f"\n*Charges:*\nFixed charges ({c['load']} kW × ₹{FIXED_PER_KW}): {gen.inr(b['fixed'])}\n"
            f"Energy charges ({c['units']} × ₹{ENERGY_RATE:.2f}): {gen.inr(b['energy'])}\n"
            f"Pension surcharge ({c['units']} × ₹{PENSION_SURCHARGE:.2f}): {gen.inr(b['surcharge'])}\n"
            f"Electricity tax (9%): {gen.inr(b['tax'])}\n",
            f"\n*ಶುಲ್ಕಗಳು:*\nನಿಗದಿತ ಶುಲ್ಕ ({c['load']} ಕಿ.ವ್ಯಾ × ₹{FIXED_PER_KW}): {gen.inr(b['fixed'])}\n"
            f"ಇಂಧನ ಶುಲ್ಕ ({c['units']} × ₹{ENERGY_RATE:.2f}): {gen.inr(b['energy'])}\n"
            f"ಪಿಂಚಣಿ ಹೆಚ್ಚುವರಿ ಶುಲ್ಕ ({c['units']} × ₹{PENSION_SURCHARGE:.2f}): {gen.inr(b['surcharge'])}\n"
            f"ವಿದ್ಯುತ್ ತೆರಿಗೆ (9%): {gen.inr(b['tax'])}\n"))
        if c["gj_benefit"]:
            head += ctx.t(L(f"Gruha Jyothi subsidy: -{gen.inr(c['gj_benefit'])}\n",
                            f"ಗೃಹ ಜ್ಯೋತಿ ಸಹಾಯಧನ: -{gen.inr(c['gj_benefit'])}\n"))
        elif b["over_cap"]:
            head += ctx.t(L(f"Gruha Jyothi: not applicable this month (consumption above {GJ_CAP} units)\n",
                            f"ಗೃಹ ಜ್ಯೋತಿ: ಈ ತಿಂಗಳು ಅನ್ವಯಿಸುವುದಿಲ್ಲ ({GJ_CAP} ಯೂನಿಟ್‌ಗಿಂತ ಹೆಚ್ಚು ಬಳಕೆ)\n"))
        bill_doc = self._bill_doc(ctx, escom, account, c)
        if paid:
            msg = head + ctx.t(L(f"\n*No dues.* Paid {gen.inr(paid['amount'])} on {paid['date']}\nTxn: {paid['txn']}",
                                 f"\n*ಬಾಕಿ ಇಲ್ಲ.* {paid['date']} ರಂದು {gen.inr(paid['amount'])} ಪಾವತಿಸಲಾಗಿದೆ\nವಹಿವಾಟು: {paid['txn']}"))
            return Reply(ui.text(msg), ui.document(bill_doc, f"{K.ESCOM_NAME[escom]['en'].split()[0]}_Bill_{account}.pdf", buttons=self.menu_buttons(ctx)))
        if c["net"] == 0:
            msg = head + ctx.t(L("\n*Net Amount Payable: ₹0.00*\nZero bill this month under Gruha Jyothi!",
                                 "\n*ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ: ₹0.00*\nಗೃಹ ಜ್ಯೋತಿ ಅಡಿ ಈ ತಿಂಗಳು ಶೂನ್ಯ ಬಿಲ್!"))
            return Reply(ui.text(msg), ui.document(bill_doc, f"{K.ESCOM_NAME[escom]['en'].split()[0]}_Bill_{account}.pdf", buttons=self.menu_buttons(ctx)))
        msg = head + ctx.t(L(f"\n*Net Amount Payable: {gen.inr(c['net'])}*\nDue Date: *{gen.dmy(c['due'])}*",
                             f"\n*ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ: {gen.inr(c['net'])}*\nಕೊನೆಯ ದಿನಾಂಕ: *{gen.dmy(c['due'])}*"))
        pid = payments.create(ctx.session_id, self.key, f"{en} bill {account}", c["net"], f"{escom}:{account}:{bd:%Y%m}")
        return Reply(ui.text(msg, cta=ui.cta_pay(ctx.s("pay", amt=gen.inr(c["net"])), pid)),
                     ui.document(bill_doc, f"{K.ESCOM_NAME[escom]['en'].split()[0]}_Bill_{account}.pdf", buttons=self.menu_buttons(ctx)))

    def _bill_doc(self, ctx, escom, account, c):
        bd = dt.date.fromisoformat(c["bill_date"])
        return docs.create(ctx.session_id, "escom_bill", f"{K.ESCOM_NAME[escom]['en'].split()[0]}_Bill_{account}.pdf", {
            "lang": ctx.lang, "place": ctx.t(ESCOM_HQ[escom]), "verify_url": ESCOM_WEB[escom], "dept": ctx.t(K.ESCOM_FULL[escom]),
            "dept_sub": ctx.t(L("Energy Department", "ಇಂಧನ ಇಲಾಖೆ")),
            "title": ctx.t(L("Electricity Bill", "ವಿದ್ಯುತ್ ಬಿಲ್")), "subtitle": gen.month_year(bd, ctx.lang),
            "ref_label": ctx.t(L("Account ID", "ಖಾತೆ ಸಂಖ್ಯೆ")), "ref": account,
            "highlight": {"label": ctx.t(L("Net Amount Payable", "ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ")), "value": gen.inr(c["net"])},
            "sections": [
                {"heading": ctx.t(L("Consumer", "ಗ್ರಾಹಕರು")), "rows": [
                    [ctx.t(L("Name", "ಹೆಸರು")), ctx.t(c["name"])], [ctx.t(L("Address", "ವಿಳಾಸ")), ctx.t(c["address"])],
                    [ctx.t(L("RR Number", "ಆರ್‌ಆರ್ ಸಂಖ್ಯೆ")), c["rr"]], [ctx.t(L("Tariff", "ದರ")), f"LT-2(a) | {c['load']} kW"],
                    [ctx.t(L("Sub-Division", "ಉಪವಿಭಾಗ")), ctx.t(c["subdiv"])]]},
                {"heading": ctx.t(L("Bill Details", "ಬಿಲ್ ವಿವರ")), "rows": [
                    [ctx.t(L("Bill Date", "ಬಿಲ್ ದಿನಾಂಕ")), gen.dmy(c["bill_date"])], [ctx.t(L("Due Date", "ಕೊನೆಯ ದಿನಾಂಕ")), gen.dmy(c["due"])],
                    [ctx.t(L("Units Consumed", "ಬಳಸಿದ ಯೂನಿಟ್")), c["units"]],
                    [ctx.t(L("Gruha Jyothi Entitlement", "ಗೃಹ ಜ್ಯೋತಿ ಅರ್ಹತೆ")), f"{c['entitled']} " + ctx.t(L("units", "ಯೂನಿಟ್")) if c["gj"] else "-"],
                    [ctx.t(L(f"Fixed Charges ({c['load']} kW × ₹{FIXED_PER_KW})", f"ನಿಗದಿತ ಶುಲ್ಕ ({c['load']} ಕಿ.ವ್ಯಾ × ₹{FIXED_PER_KW})")), gen.inr(c["breakup"]["fixed"])],
                    [ctx.t(L(f"Energy Charges ({c['units']} × ₹{ENERGY_RATE:.2f})", f"ಇಂಧನ ಶುಲ್ಕ ({c['units']} × ₹{ENERGY_RATE:.2f})")), gen.inr(c["breakup"]["energy"])],
                    [ctx.t(L(f"P&G Pension Surcharge ({c['units']} × ₹{PENSION_SURCHARGE:.2f})", f"ಪಿಂಚಣಿ ಹೆಚ್ಚುವರಿ ಶುಲ್ಕ ({c['units']} × ₹{PENSION_SURCHARGE:.2f})")), gen.inr(c["breakup"]["surcharge"])],
                    [ctx.t(L("Electricity Tax (9% of energy charges)", "ವಿದ್ಯುತ್ ತೆರಿಗೆ (ಇಂಧನ ಶುಲ್ಕದ 9%)")), gen.inr(c["breakup"]["tax"])],
                    [ctx.t(L("Gross Amount", "ಒಟ್ಟು ಮೊತ್ತ")), gen.inr(c["breakup"]["gross"])],
                    [ctx.t(L("Gruha Jyothi Subsidy", "ಗೃಹ ಜ್ಯೋತಿ ಸಹಾಯಧನ")), ("-" + gen.inr(c["gj_benefit"])) if c["gj_benefit"] else "-"],
                    [ctx.t(L("Net Payable", "ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ")), gen.inr(c["net"])]]}],
            "notes": [ctx.t(L("Tariff LT-2(a) as per the KERC tariff order for FY 2025-26. Helpline: 1912 (24x7).",
                              "ಕೆಇಆರ್‌ಸಿ 2025-26 ದರ ಆದೇಶದ ಪ್ರಕಾರ ಎಲ್‌ಟಿ-2(ಎ) ದರ. ಸಹಾಯವಾಣಿ: 1912 (24x7)."))],
            "signatory": {"name": ctx.t(K.ESCOM_NAME[escom]), "designation": ctx.t(c["subdiv"])}})

    def on_payment(self, ctx, p):
        escom, account, ym = p["ref"].split(":")
        date = time.strftime("%d-%m-%Y")
        db.rec_put("escom_paid", p["ref"], {"amount": p["amount"], "date": date, "txn": p["txn_id"]}, ctx.session_id)
        c = consumer(escom, account)
        en = ctx.t(K.ESCOM_NAME[escom])
        doc_id = docs.create(ctx.session_id, "escom_receipt", f"{K.ESCOM_NAME[escom]['en'].split()[0]}_Receipt_{account}.pdf", {
            "lang": ctx.lang, "place": ctx.t(ESCOM_HQ[escom]), "verify_url": ESCOM_WEB[escom], "dept": ctx.t(K.ESCOM_FULL[escom]), "dept_sub": ctx.t(L("Energy Department", "ಇಂಧನ ಇಲಾಖೆ")),
            "title": ctx.t(L("Payment Receipt", "ಪಾವತಿ ರಸೀದಿ")), "ref_label": ctx.t(L("Receipt No", "ರಸೀದಿ ಸಂಖ್ಯೆ")),
            "ref": p["id"], "highlight": {"label": ctx.t(L("Amount Paid", "ಪಾವತಿಸಿದ ಮೊತ್ತ")), "value": gen.inr(p["amount"])},
            "sections": [{"rows": [[ctx.t(L("Consumer", "ಗ್ರಾಹಕರು")), ctx.t(c["name"])],
                                   [ctx.t(L("Account ID", "ಖಾತೆ ಸಂಖ್ಯೆ")), account],
                                   [ctx.t(L("Transaction ID", "ವಹಿವಾಟು ಸಂಖ್ಯೆ")), p["txn_id"]],
                                   [ctx.t(L("Payment Mode", "ಪಾವತಿ ವಿಧಾನ")), p["method"]],
                                   [ctx.t(L("Date", "ದಿನಾಂಕ")), date]]}],
            "signatory": {"name": en, "designation": ctx.t(L("Online Payment", "ಆನ್‌ಲೈನ್ ಪಾವತಿ"))}})
        msg = ctx.t(L(f"*Payment Successful*\n\n{en} bill for Account ID *{account}* paid.\nAmount: *{gen.inr(p['amount'])}*\n"
                      f"Txn ID: {p['txn_id']}\n\nThank you for paying on time!",
                      f"*ಪಾವತಿ ಯಶಸ್ವಿಯಾಗಿದೆ*\n\nಖಾತೆ ಸಂಖ್ಯೆ *{account}* ರ {en} ಬಿಲ್ ಪಾವತಿಸಲಾಗಿದೆ.\nಮೊತ್ತ: *{gen.inr(p['amount'])}*\n"
                      f"ವಹಿವಾಟು ಸಂಖ್ಯೆ: {p['txn_id']}\n\nಸಮಯಕ್ಕೆ ಸರಿಯಾಗಿ ಪಾವತಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು!"))
        return [ui.text(msg), ui.document(doc_id, f"{K.ESCOM_NAME[escom]['en'].split()[0]}_Receipt_{account}.pdf", buttons=self.menu_buttons(ctx))]

    # ---------------------------------------------------------------------
    def complaint(self, ctx, v):
        if gen.is_missing(v["account"]):
            return self._not_found(ctx, v["escom"])
        c = consumer(v["escom"], v["account"])
        docket = f"{K.ESCOM_PREFIX[v['escom']]}{dt.date.today():%y%m%d}{gen.ref_id('', 4)}"
        db.rec_put("escom_complaint", docket, dict(v, subdiv=c["subdiv"]), ctx.session_id)
        msg = ctx.t(L(
            f"*Complaint Registered*\n\nComplaint No: *{docket}*\nType: {ctx.t(CTYPES[v['ctype']])}\n"
            f"Consumer: {ctx.t(c['name'])} ({v['account']})\nAddress: {ctx.t(c['address'])}\n\n"
            f"Assigned to *{ctx.t(c['subdiv'])}*. A lineman will attend within *4 hours*.\nHelpline: 1912",
            f"*ದೂರು ದಾಖಲಾಗಿದೆ*\n\nದೂರಿನ ಸಂಖ್ಯೆ: *{docket}*\nಪ್ರಕಾರ: {ctx.t(CTYPES[v['ctype']])}\n"
            f"ಗ್ರಾಹಕರು: {ctx.t(c['name'])} ({v['account']})\nವಿಳಾಸ: {ctx.t(c['address'])}\n\n"
            f"*{ctx.t(c['subdiv'])}* ಗೆ ನಿಯೋಜಿಸಲಾಗಿದೆ. *4 ಗಂಟೆಗಳೊಳಗೆ* ಲೈನ್‌ಮ್ಯಾನ್ ಭೇಟಿ ನೀಡುತ್ತಾರೆ.\nಸಹಾಯವಾಣಿ: 1912"))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Complaint", "ದೂರು ಸ್ಥಿತಿ")), f"track:{docket}"))))

    def track(self, ctx, docket):
        if gen.is_missing(docket):
            return Errors({"docket": L("No complaint found with this number.", "ಈ ಸಂಖ್ಯೆಯ ದೂರು ಕಂಡುಬಂದಿಲ್ಲ.")})
        rec = db.rec_get("escom_complaint", docket)
        if rec:
            stage = stage_from_elapsed(rec["_created_at"], len(C_STAGES))
            ctype, subdiv = rec["ctype"], ctx.t(rec["subdiv"])
        else:
            r = gen.rng("escomc", docket)
            stage, ctype = r.randint(1, 3), r.choice(list(CTYPES))
            subdiv = ctx.t(L("Jayanagar Sub-Division", "ಜಯನಗರ ಉಪವಿಭಾಗ"))
        msg = ctx.t(L(f"*Complaint Status*\n\nComplaint No: {docket}\nType: {ctx.t(CTYPES[ctype])}\nOffice: {subdiv}\n\n",
                      f"*ದೂರಿನ ಸ್ಥಿತಿ*\n\nದೂರಿನ ಸಂಖ್ಯೆ: {docket}\nಪ್ರಕಾರ: {ctx.t(CTYPES[ctype])}\nಕಚೇರಿ: {subdiv}\n\n"))
        msg += timeline(ctx, C_STAGES, stage)
        btns = self.menu_buttons(ctx) if stage == len(C_STAGES) - 1 else self.menu_buttons(
            ctx, self.btn(ctx.t(L("Refresh Status", "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ")), f"track:{docket}"))
        return Reply(ui.text(msg, buttons=btns))

    def on_button(self, ctx, arg):
        if arg.startswith("track:"):
            return self.track(ctx, arg.split(":", 1)[1])
        return None

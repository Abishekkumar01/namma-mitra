"""KSRTC - bus ticket booking (3 screens) & cancellation.

Screen main : from / to / date / passengers / class
Screen bus  : available services (generated per route+date, distance-based fares & timings)
Screen pax  : primary passenger + boarding point -> payment (or Shakti zero-ticket) -> e-ticket PDF
Cancel      : any PNR -> refund calculation -> confirm button -> cancelled
"""
import datetime as dt
import math
import re
import time

from .. import db, docs, payments, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Screen, Service

RES_FEE = 10


def distance_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (K.CITIES[a][2], K.CITIES[a][3], K.CITIES[b][2], K.CITIES[b][3]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return max(40, int(6371 * 2 * math.asin(math.sqrt(h)) * 1.28))


def services_for(frm, to, date, btype):
    km = distance_km(frm, to)
    r = gen.rng("ksrtc", frm, to, date)
    types = [t for t in K.BUS_TYPES if not (t == "ev" and km > 260) and not (t == "ambaari" and km < 250)]
    hours = km / 52
    out = []
    for i in range(r.randint(6, 9)):
        t = r.choice(types)
        dep_min = r.randint(5 * 60, 23 * 60 + 30)
        dep_min -= dep_min % 15
        out.append((t, dep_min))
    if btype != "any" and btype in types and not any(t == btype for t, _ in out):
        out.append((btype, r.randint(18, 23) * 60))
    res = []
    for i, (t, dep_min) in enumerate(sorted(out, key=lambda x: x[1])):
        if btype != "any" and t != btype:
            continue
        rate = K.BUS_TYPES[t][2]
        dur = int(hours * 60 * (0.92 if t in ("airavat", "club") else 1.0))
        arr = dep_min + dur
        res.append({"id": f"S{i + 1}", "type": t, "dep": dep_min, "arr": arr,
                    "fare": int(round(km * rate / 5) * 5) + RES_FEE, "seats": r.randint(3, 38),
                    "code": f"{K.CITIES[frm][0][:3].upper()}{K.CITIES[to][0][:3].upper()}{r.randint(100, 999)}"})
    return km, res


def hhmm(minutes):
    m = minutes % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}" + (" (+1)" if minutes >= 24 * 60 else "")


class Ksrtc(Service):
    key = "ksrtc"
    order = 8
    icon = "bus"
    title = L("KSRTC Bus Reservation", "ಕೆಎಸ್‌ಆರ್‌ಟಿಸಿ ಬಸ್ ಮುಂಗಡ ಕಾಯ್ದಿರಿಸುವಿಕೆ")
    dept = L("Karnataka State Road Transport Corporation", "ಕರ್ನಾಟಕ ರಾಜ್ಯ ರಸ್ತೆ ಸಾರಿಗೆ ನಿಗಮ")
    sevaone = [L("Online Reservation for bus booking KSRTC")]
    subtitle = L("Online reservation for bus booking and cancellation", "ಬಸ್ ಟಿಕೆಟ್ ಬುಕಿಂಗ್ ಮತ್ತು ರದ್ದತಿ")
    keywords = ["bus", "ticket", "ksrtc", "travel", "booking", "airavat", "sarige", "journey",
                "ಬಸ್", "ಟಿಕೆಟ್", "ಪ್ರಯಾಣ", "ಕೆಎಸ್‌ಆರ್‌ಟಿಸಿ"]

    def fields(self, ctx):
        book = {"action": "book"}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("book", L("Book Bus Ticket", "ಬಸ್ ಟಿಕೆಟ್ ಬುಕ್ ಮಾಡಿ")),
                fk.opt("cancel", L("Cancel Ticket", "ಟಿಕೆಟ್ ರದ್ದುಪಡಿಸಿ"))]),
            fk.dropdown("from", L("From", "ಎಲ್ಲಿಂದ"), K.CITY_OPTIONS, show_if=book),
            fk.dropdown("to", L("To", "ಎಲ್ಲಿಗೆ"), K.CITY_OPTIONS, show_if=book),
            fk.date("date", L("Journey Date", "ಪ್ರಯಾಣ ದಿನಾಂಕ"), min_days=0, max_days=30, show_if=book,
                    helper=L("Reservation opens 30 days in advance", "30 ದಿನ ಮುಂಚಿತವಾಗಿ ಮುಂಗಡ ಕಾಯ್ದಿರಿಸಬಹುದು"),
                    error=L("Journey date must be between today ({a}) and {b}. Reservations open 30 days in advance.",
                            "ಪ್ರಯಾಣ ದಿನಾಂಕ ಇಂದಿನಿಂದ ({a}) {b} ರೊಳಗೆ ಇರಬೇಕು. 30 ದಿನ ಮುಂಚಿತವಾಗಿ ಮಾತ್ರ ಕಾಯ್ದಿರಿಸಬಹುದು.")),
            fk.number("pax", L("Number of Passengers", "ಪ್ರಯಾಣಿಕರ ಸಂಖ್ಯೆ"), min=1, max=6, placeholder="1", show_if=book,
                      error=L("You can book {min} to {max} seats in one ticket.", "ಒಂದು ಟಿಕೆಟ್‌ನಲ್ಲಿ {min} ರಿಂದ {max} ಆಸನಗಳನ್ನು ಕಾಯ್ದಿರಿಸಬಹುದು.")),
            fk.radio("btype", L("Bus Class", "ಬಸ್ ವರ್ಗ"),
                     [fk.opt("any", L("Any class", "ಯಾವುದೇ ವರ್ಗ"))] +
                     [fk.opt(k, L(v[0], v[1])) for k, v in K.BUS_TYPES.items()], show_if=book),
            fk.text("pnr", L("Enter PNR Number", "ಪಿಎನ್‌ಆರ್ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": "cancel"},
                    placeholder="KS2611220123", transform="upper_nospace", pattern=r"^[A-Z0-9]{6,14}$",
                    error=L("Enter a valid PNR (6-14 letters/digits)", "ಮಾನ್ಯ ಪಿಎನ್‌ಆರ್ ನಮೂದಿಸಿ (6-14 ಅಕ್ಷರ/ಅಂಕಿ)")),
        ]

    def prefill(self, text):
        t = text.lower()
        if "cancel" in t or "ರದ್ದು" in t:
            return {"action": "cancel"}
        out = {"action": "book"} if any(w in t for w in ("book", "ticket", "bus", "ಟಿಕೆಟ್", "ಬಸ್")) else {}
        for k, v in K.CITIES.items():
            en = v[0].lower().split()[0]
            stem = v[1].split()[0][:-1]          # drop final vowel sign: ಮೈಸೂರು -> ಮೈಸೂರ
            if re.search(r"(?:^|\s)to " + en, t) or re.search(stem + r".{0,3}ಗೆ", text):
                out["to"] = k
            elif re.search(r"(?:^|\s)from " + en, t) or re.search(stem + r".{0,4}(ದಿಂದ|ನಿಂದ)", text):
                out["from"] = k
        return out

    # ---------------------------------------------------------------------
    def submit(self, ctx, screen, v, data):
        if screen == "main":
            if v["action"] == "cancel":
                return self.cancel_lookup(ctx, v["pnr"])
            return self._buses(ctx, v)
        if screen == "bus":
            return self._pax(ctx, v, data)
        if screen == "pax":
            return self._hold(ctx, v, data)
        return Reply()

    def _buses(self, ctx, v):
        if v["from"] == v["to"]:
            return Errors({"to": L("Destination must be different from origin.","ಗಮ್ಯಸ್ಥಾನ ಆರಂಭ ಸ್ಥಳಕ್ಕಿಂತ ಭಿನ್ನವಾಗಿರಬೇಕು")})
        km, buses = services_for(v["from"], v["to"], v["date"], v["btype"])
        if not buses:
            return Errors({"btype": L("No buses of this class on this route. Choose 'Any class'.",
                                      "ಈ ಮಾರ್ಗದಲ್ಲಿ ಈ ವರ್ಗದ ಬಸ್‌ಗಳಿಲ್ಲ. 'ಯಾವುದೇ ವರ್ಗ' ಆಯ್ಕೆಮಾಡಿ.")})
        opts = []
        for b in buses:
            bt = K.BUS_TYPES[b["type"]]
            opts.append(fk.opt(b["id"], L(f"{hhmm(b['dep'])} → {hhmm(b['arr'])}  •  {bt[0]}", f"{hhmm(b['dep'])} → {hhmm(b['arr'])}  •  {bt[1]}"),
                               L(f"₹{b['fare']} per seat  •  {b['seats']} seats left  •  {b['code']}",
                                 f"ಪ್ರತಿ ಆಸನ ₹{b['fare']}  •  {b['seats']} ಆಸನ ಲಭ್ಯ  •  {b['code']}")))
        route = f"{ctx.t(K.CITY_NAME[v['from']])} → {ctx.t(K.CITY_NAME[v['to']])}"
        head = ctx.t(L(f"*{route}*\nDate: {gen.dmy(v['date'])}  •  Passengers: {v['pax']}  •  ~{km} km",
                       f"*{route}*\nದಿನಾಂಕ: {gen.dmy(v['date'])}  •  ಪ್ರಯಾಣಿಕರು: {v['pax']}  •  ~{km} ಕಿ.ಮೀ"))
        return Screen("bus", L("Select Bus", "ಬಸ್ ಆಯ್ಕೆಮಾಡಿ"), [
            fk.info("route", head),
            fk.radio("bus", L("Available Services", "ಲಭ್ಯವಿರುವ ಸೇವೆಗಳು"), opts)],
            data=dict(v, km=km, buses={b["id"]: b for b in buses}), submit=L("Continue", "ಮುಂದುವರಿಯಿರಿ"))

    def _pax(self, ctx, v, data):
        bus = data["buses"][v["bus"]]
        points = K.BOARDING.get(data["from"]) or [
            L(f"{K.CITIES[data['from']][0]} Central Bus Stand", f"{K.CITIES[data['from']][1]} ಕೇಂದ್ರ ಬಸ್ ನಿಲ್ದಾಣ"),
            L(f"{K.CITIES[data['from']][0]} City Bus Stand", f"{K.CITIES[data['from']][1]} ನಗರ ಬಸ್ ನಿಲ್ದಾಣ")]
        shakti_note = ""
        if K.BUS_TYPES[bus["type"]][3] and K.CITIES[data["from"]][4] and K.CITIES[data["to"]][4]:
            shakti_note = ctx.t(L("\n\n*Shakti*: women passengers travel free on this bus (zero-ticket).",
                                  "\n\n*ಶಕ್ತಿ*: ಈ ಬಸ್‌ನಲ್ಲಿ ಮಹಿಳಾ ಪ್ರಯಾಣಿಕರಿಗೆ ಉಚಿತ ಪ್ರಯಾಣ (ಶೂನ್ಯ ಟಿಕೆಟ್)."))
        info = ctx.t(L(f"{K.BUS_TYPES[bus['type']][0]} ({bus['code']})\nTiming: {hhmm(bus['dep'])} → {hhmm(bus['arr'])}\n₹{bus['fare']} × {data['pax']}",
                       f"{K.BUS_TYPES[bus['type']][1]} ({bus['code']})\nಸಮಯ: {hhmm(bus['dep'])} → {hhmm(bus['arr'])}\n₹{bus['fare']} × {data['pax']}")) + shakti_note
        return Screen("pax", L("Passenger Details", "ಪ್ರಯಾಣಿಕರ ವಿವರ"), [
            fk.info("sel", info),
            fk.text("pname", L("Primary Passenger Name", "ಮುಖ್ಯ ಪ್ರಯಾಣಿಕರ ಹೆಸರು"), pattern=r"^[A-Za-zಀ-೿ .]{3,40}$",
                    placeholder=L("e.g. Kavya Gowda", "ಉದಾ: ಕಾವ್ಯ ಗೌಡ"),
                    error=L("Enter a valid name", "ಮಾನ್ಯ ಹೆಸರು ನಮೂದಿಸಿ")),
            fk.number("age", L("Age", "ವಯಸ್ಸು"), min=5, max=99, placeholder="30",
                      error=L("Enter an age between {min} and {max}. Children below {min} travel free without a seat.",
                              "{min} ರಿಂದ {max} ನಡುವಿನ ವಯಸ್ಸನ್ನು ನಮೂದಿಸಿ. {min} ವರ್ಷದೊಳಗಿನ ಮಕ್ಕಳು ಆಸನವಿಲ್ಲದೆ ಉಚಿತವಾಗಿ ಪ್ರಯಾಣಿಸಬಹುದು.")),
            fk.radio("gender", L("Gender", "ಲಿಂಗ"), [fk.opt("M", L("Male", "ಪುರುಷ")), fk.opt("F", L("Female", "ಮಹಿಳೆ"))]),
            fk.radio("board", L("Boarding Point", "ಹತ್ತುವ ಸ್ಥಳ"), [fk.opt(str(i), p) for i, p in enumerate(points)]),
        ], data=dict(data, bus=bus, points=points), submit=L("Proceed to Pay", "ಪಾವತಿಗೆ ಮುಂದುವರಿಯಿರಿ"))

    def _hold(self, ctx, v, data):
        bus = data["bus"]
        pax = int(data["pax"])
        shakti = (v["gender"] == "F" and K.BUS_TYPES[bus["type"]][3]
                  and K.CITIES[data["from"]][4] and K.CITIES[data["to"]][4])
        total = bus["fare"] * pax - (bus["fare"] if shakti else 0)
        r = gen.rng(time.time())
        start = r.randint(1, 40 - pax)
        seats = [str(s) for s in range(start, start + pax)]
        pnr = f"KS{dt.date.today():%y%m%d}{gen.digits(r, 4)}"
        booking = {"pnr": pnr, "from": data["from"], "to": data["to"], "date": data["date"], "pax": pax,
                   "bus": bus, "seats": seats, "pname": v["pname"], "age": v["age"], "gender": v["gender"],
                   "board": data["points"][int(v["board"])], "total": total, "shakti": bool(shakti), "status": "held"}
        db.rec_put("ksrtc_booking", pnr, booking, ctx.session_id)
        if total == 0:
            return Reply(*self._confirm(ctx, pnr, None))
        pid = payments.create(ctx.session_id, self.key, f"KSRTC {bus['code']}", total, pnr)
        route = f"{ctx.t(K.CITY_NAME[data['from']])} → {ctx.t(K.CITY_NAME[data['to']])}"
        sh = ctx.t(L(f"\nShakti zero-ticket applied for {v['pname']}", f"\n{v['pname']} ಅವರಿಗೆ ಶಕ್ತಿ ಶೂನ್ಯ ಟಿಕೆಟ್ ಅನ್ವಯಿಸಲಾಗಿದೆ")) if shakti else ""
        msg = ctx.t(L(f"*Seats on hold for 10 minutes*\n\nRoute: {route}\nDeparture: {gen.dmy(data['date'])}  •  {hhmm(bus['dep'])}\nBus: {K.BUS_TYPES[bus['type']][0]}\n"
                      f"Seats: {', '.join(seats)}{sh}\n\n*Total: {gen.inr(total)}*",
                      f"*ಆಸನಗಳನ್ನು 10 ನಿಮಿಷ ಕಾಯ್ದಿರಿಸಲಾಗಿದೆ*\n\nಮಾರ್ಗ: {route}\nನಿರ್ಗಮನ: {gen.dmy(data['date'])}  •  {hhmm(bus['dep'])}\nಬಸ್: {K.BUS_TYPES[bus['type']][1]}\n"
                      f"ಆಸನಗಳು: {', '.join(seats)}{sh}\n\n*ಒಟ್ಟು: {gen.inr(total)}*"))
        return Reply(ui.text(msg, cta=ui.cta_pay(ctx.s("pay", amt=gen.inr(total)), pid), buttons=self.menu_buttons(ctx)))

    def on_payment(self, ctx, p):
        return self._confirm(ctx, p["ref"], p)

    def _confirm(self, ctx, pnr, p):
        b = db.rec_get("ksrtc_booking", pnr)
        if not b:
            return [ui.text(ctx.s("payment_missing"))]
        b["status"] = "confirmed"
        b["txn"] = p["txn_id"] if p else "-"
        db.rec_put("ksrtc_booking", pnr, b)
        bus = b["bus"]
        bt = K.BUS_TYPES[bus["type"]]
        route = f"{ctx.t(K.CITY_NAME[b['from']])} → {ctx.t(K.CITY_NAME[b['to']])}"
        doc_id = docs.create(ctx.session_id, "ksrtc_ticket", f"KSRTC_eTicket_{pnr}.pdf", {
            "lang": ctx.lang, "place": ctx.t(K.CITY_NAME[b["from"]]), "verify_url": "ksrtc.karnataka.gov.in", "dept": ctx.t(L("Karnataka State Road Transport Corporation", "ಕರ್ನಾಟಕ ರಾಜ್ಯ ರಸ್ತೆ ಸಾರಿಗೆ ನಿಗಮ")),
            "dept_sub": ctx.t(L("Central Offices, K.H. Road, Shanthinagar, Bengaluru", "ಕೇಂದ್ರ ಕಚೇರಿ, ಕೆ.ಎಚ್. ರಸ್ತೆ, ಶಾಂತಿನಗರ, ಬೆಂಗಳೂರು")),
            "title": ctx.t(L("e-TICKET", "ಇ-ಟಿಕೆಟ್")), "subtitle": route,
            "ref_label": "PNR", "ref": pnr,
            "highlight": {"label": ctx.t(L("Departure", "ನಿರ್ಗಮನ")), "value": f"{gen.dmy(b['date'])}  {hhmm(bus['dep'])}"},
            "sections": [{"rows": [
                [ctx.t(L("Service", "ಸೇವೆ")), f"{ctx.t(L(bt[0], bt[1]))} ({bus['code']})"],
                [ctx.t(L("Arrival", "ಆಗಮನ")), hhmm(bus["arr"])],
                [ctx.t(L("Boarding Point", "ಹತ್ತುವ ಸ್ಥಳ")), ctx.t(b["board"])],
                [ctx.t(L("Passenger", "ಪ್ರಯಾಣಿಕರು")), f"{b['pname']} ({b['age']}, {b['gender']})" + (f" + {b['pax'] - 1}" if b["pax"] > 1 else "")],
                [ctx.t(L("Seat Numbers", "ಆಸನ ಸಂಖ್ಯೆ")), ", ".join(b["seats"])],
                [ctx.t(L("Fare Paid", "ಪಾವತಿಸಿದ ದರ")), gen.inr(b["total"]) + (" (Shakti)" if b["shakti"] else "")],
                [ctx.t(L("Transaction ID", "ವಹಿವಾಟು ಸಂಖ್ಯೆ")), b["txn"]]]}],
            "notes": [ctx.t(L("Report at the boarding point 15 minutes before departure with a valid photo ID.",
                              "ಮಾನ್ಯ ಫೋಟೋ ಗುರುತಿನ ಚೀಟಿಯೊಂದಿಗೆ ನಿರ್ಗಮನಕ್ಕೆ 15 ನಿಮಿಷ ಮುಂಚೆ ಹಾಜರಾಗಿ.")),
                      ctx.t(L("Cancellation: 10% up to 72 hrs, 25% up to 24 hrs, 50% thereafter before departure.",
                              "ರದ್ದತಿ: 72 ಗಂಟೆ ಮುಂಚೆ 10%, 24 ಗಂಟೆ ಮುಂಚೆ 25%, ನಂತರ 50% ಕಡಿತ."))],
            "signatory": {"name": "KSRTC", "designation": ctx.t(L("Online Reservation", "ಆನ್‌ಲೈನ್ ಮುಂಗಡ ಕಾಯ್ದಿರಿಸುವಿಕೆ"))}})
        msg = ctx.t(L(f"*Ticket Confirmed*\n\nPNR: *{pnr}*\nRoute: {route}\nDeparture: {gen.dmy(b['date'])}  •  {hhmm(bus['dep'])}\n"
                      f"Boarding: {ctx.t(b['board'])}\nSeats: *{', '.join(b['seats'])}*\n\nHappy journey! Show this e-ticket to the conductor.",
                      f"*ಟಿಕೆಟ್ ದೃಢೀಕರಿಸಲಾಗಿದೆ*\n\nಪಿಎನ್‌ಆರ್: *{pnr}*\nಮಾರ್ಗ: {route}\nನಿರ್ಗಮನ: {gen.dmy(b['date'])}  •  {hhmm(bus['dep'])}\n"
                      f"ಹತ್ತುವ ಸ್ಥಳ: {ctx.t(b['board'])}\nಆಸನಗಳು: *{', '.join(b['seats'])}*\n\nಶುಭ ಪ್ರಯಾಣ! ಈ ಇ-ಟಿಕೆಟ್ ಅನ್ನು ನಿರ್ವಾಹಕರಿಗೆ ತೋರಿಸಿ."))
        return [ui.text(msg), ui.document(doc_id, f"KSRTC_eTicket_{pnr}.pdf", buttons=self.menu_buttons(ctx))]

    # ---------------------------------------------------------------------
    def _booking_for(self, pnr):
        b = db.rec_get("ksrtc_booking", pnr)
        if b:
            return b
        r = gen.rng("pnr", pnr)
        frm, to = r.sample(["bengaluru", "mysuru", "mangaluru", "hubballi", "shivamogga", "udupi"], 2)
        date = (gen.today() + dt.timedelta(days=r.randint(1, 12))).isoformat()
        km, buses = services_for(frm, to, date, "any")
        bus = r.choice(buses)
        pax = r.randint(1, 3)
        return {"pnr": pnr, "from": frm, "to": to, "date": date, "pax": pax, "bus": bus,
                "seats": [str(r.randint(1, 40))], "pname": gen.person(r)["name"]["en"], "total": bus["fare"] * pax,
                "status": "confirmed", "shakti": False}

    def cancel_lookup(self, ctx, pnr):
        if gen.is_missing(pnr):
            return Errors({"pnr": L("No booking found for this PNR.", "ಈ ಪಿಎನ್‌ಆರ್‌ಗೆ ಯಾವುದೇ ಬುಕಿಂಗ್ ಕಂಡುಬಂದಿಲ್ಲ.")})
        b = self._booking_for(pnr)
        route = f"{ctx.t(K.CITY_NAME[b['from']])} → {ctx.t(K.CITY_NAME[b['to']])}"
        if b.get("status") == "cancelled":
            return Reply(ui.text(ctx.t(L(f"PNR *{pnr}* ({route}) is already cancelled.", f"ಪಿಎನ್‌ಆರ್ *{pnr}* ({route}) ಈಗಾಗಲೇ ರದ್ದಾಗಿದೆ.")),
                                 buttons=self.menu_buttons(ctx)))
        if b.get("status") == "held":
            return Reply(ui.text(ctx.t(L(f"PNR *{pnr}* was not paid, so the seats were released automatically.",
                                         f"ಪಿಎನ್‌ಆರ್ *{pnr}* ಪಾವತಿಯಾಗದ ಕಾರಣ ಆಸನಗಳನ್ನು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಬಿಡುಗಡೆ ಮಾಡಲಾಗಿದೆ.")),
                                 buttons=self.menu_buttons(ctx)))
        dep = dt.datetime.fromisoformat(b["date"]) + dt.timedelta(minutes=b["bus"]["dep"])
        hrs = (dep - dt.datetime.now()).total_seconds() / 3600
        pct = 10 if hrs > 72 else 25 if hrs > 24 else 50
        refund = round(b["total"] * (100 - pct) / 100, 2)
        msg = ctx.t(L(f"*Cancel Ticket*\n\nPNR: *{pnr}*\nRoute: {route}\nDeparture: {gen.dmy(b['date'])}  •  {hhmm(b['bus']['dep'])}\nPassenger: {b['pname']}\n\n"
                      f"Fare paid: {gen.inr(b['total'])}\nCancellation charge: {pct}%\n*Refund: {gen.inr(refund)}* (to source account in 5-7 days)\n\nTap *Confirm Cancellation* to proceed.",
                      f"*ಟಿಕೆಟ್ ರದ್ದತಿ*\n\nಪಿಎನ್‌ಆರ್: *{pnr}*\nಮಾರ್ಗ: {route}\nನಿರ್ಗಮನ: {gen.dmy(b['date'])}  •  {hhmm(b['bus']['dep'])}\nಪ್ರಯಾಣಿಕರು: {b['pname']}\n\n"
                      f"ಪಾವತಿಸಿದ ದರ: {gen.inr(b['total'])}\nರದ್ದತಿ ಶುಲ್ಕ: {pct}%\n*ಮರುಪಾವತಿ: {gen.inr(refund)}* (5-7 ದಿನಗಳಲ್ಲಿ ಮೂಲ ಖಾತೆಗೆ)\n\nಮುಂದುವರಿಯಲು *ರದ್ದತಿ ದೃಢೀಕರಿಸಿ* ಒತ್ತಿರಿ."))
        return Reply(ui.text(msg, buttons=[self.btn(ctx.t(L("Confirm Cancellation", "ರದ್ದತಿ ದೃಢೀಕರಿಸಿ")), f"cancel:{pnr}:{refund}"),
                                           ui.button(ctx.s("main_menu"), "menu")]))

    def on_button(self, ctx, arg):
        if arg.startswith("cancel:"):
            _, pnr, refund = arg.split(":")
            b = self._booking_for(pnr)
            if b.get("status") == "cancelled":
                return Reply(ui.text(ctx.t(L(f"PNR *{pnr}* is already cancelled.", f"ಪಿಎನ್‌ಆರ್ *{pnr}* ಈಗಾಗಲೇ ರದ್ದಾಗಿದೆ.")),
                                     buttons=self.menu_buttons(ctx)))
            b["status"] = "cancelled"
            db.rec_put("ksrtc_booking", pnr, b, ctx.session_id)
            ref = gen.ref_id("RF", 8)
            return Reply(ui.text(ctx.t(L(f"*Ticket Cancelled*\n\nPNR: *{pnr}*\nRefund of *{gen.inr(float(refund))}* initiated.\nRefund Ref: {ref}\n\nAmount will reach your source account in 5-7 working days.",
                                         f"*ಟಿಕೆಟ್ ರದ್ದಾಗಿದೆ*\n\nಪಿಎನ್‌ಆರ್: *{pnr}*\n*{gen.inr(float(refund))}* ಮರುಪಾವತಿ ಪ್ರಾರಂಭಿಸಲಾಗಿದೆ.\nಮರುಪಾವತಿ ಸಂಖ್ಯೆ: {ref}\n\n5-7 ಕೆಲಸದ ದಿನಗಳಲ್ಲಿ ಮೊತ್ತ ನಿಮ್ಮ ಮೂಲ ಖಾತೆಗೆ ಜಮೆಯಾಗುತ್ತದೆ.")),
                                 buttons=self.menu_buttons(ctx)))
        return None

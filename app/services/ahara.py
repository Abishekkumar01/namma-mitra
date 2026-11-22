"""Food, Civil Supplies and Consumer Affairs Department - ration card services.

Seva One services covered: "Application for Family ID/New NPHH (APL) Card", "Issue of New Ration Card",
"Ration Card - Transfer / Change of address / Inclusion of names".
Status, members and Fair Price Shop by any 12-digit ration card number; new card application with
acknowledgement, live status and e-ration card PDF.
"""
import datetime as dt

from .. import db, docs, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service, masked_aadhaar, stage_from_elapsed, timeline

DEPT = L("Food, Civil Supplies and Consumer Affairs Department", "ಆಹಾರ, ನಾಗರಿಕ ಸರಬರಾಜು ಮತ್ತು ಗ್ರಾಹಕ ವ್ಯವಹಾರಗಳ ಇಲಾಖೆ")
RELATIONS = [L("Spouse", "ಪತಿ/ಪತ್ನಿ"), L("Son", "ಮಗ"), L("Daughter", "ಮಗಳು"), L("Mother", "ತಾಯಿ"),
             L("Father", "ತಂದೆ"), L("Daughter-in-law", "ಸೊಸೆ")]
CARD_TYPES = {"phh": L("PHH - Priority Household (BPL)", "ಆದ್ಯತಾ ಕುಟುಂಬ (BPL)"),
              "nphh": L("NPHH - Non-Priority Household (APL)", "ಆದ್ಯತೇತರ ಕುಟುಂಬ (APL)")}
STAGES = [L("Application submitted", "ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ"),
          L("Aadhaar of all members verified", "ಎಲ್ಲಾ ಸದಸ್ಯರ ಆಧಾರ್ ಪರಿಶೀಲನೆ"),
          L("Field verification by Food Inspector", "ಆಹಾರ ನಿರೀಕ್ಷಕರಿಂದ ಸ್ಥಳ ಪರಿಶೀಲನೆ"),
          L("Approved by Deputy Director (Food)", "ಉಪ ನಿರ್ದೇಶಕರ (ಆಹಾರ) ಅನುಮೋದನೆ"),
          L("Ration card issued (e-card)", "ಪಡಿತರ ಚೀಟಿ ವಿತರಣೆ (ಇ-ಕಾರ್ಡ್)")]
NAME_RE = r"^[A-Za-zಀ-೿ .']{3,60}$"


class Ahara(Service):
    key = "ahara"
    order = 7
    icon = "ration"
    title = L("Ration Card Services (Ahara)", "ಪಡಿತರ ಚೀಟಿ ಸೇವೆಗಳು (ಆಹಾರ)")
    subtitle = L("New ration card, card status, members, Fair Price Shop", "ಹೊಸ ಪಡಿತರ ಚೀಟಿ, ಸ್ಥಿತಿ, ಸದಸ್ಯರು, ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿ")
    dept = DEPT
    sevaone = [L("Issue of New Ration Card"), L("Application for Family ID/New NPHH (APL) Card"),
               L("Ration Card - Transfer / Change of address / Inclusion of names")]
    keywords = ["ration", "ration card", "ahara", "ekyc", "e-kyc", "rice", "fair price", "fps", "bpl", "apl", "family id",
                "ಪಡಿತರ", "ರೇಷನ್", "ಆಹಾರ", "ಅಕ್ಕಿ", "ನ್ಯಾಯಬೆಲೆ"]

    def fields(self, ctx):
        apply = {"action": "apply"}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("status", L("Ration Card Status & Members", "ಪಡಿತರ ಚೀಟಿ ಸ್ಥಿತಿ ಮತ್ತು ಸದಸ್ಯರು")),
                fk.opt("fps", L("My Fair Price Shop & Entitlement", "ನನ್ನ ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿ ಮತ್ತು ಅರ್ಹತೆ")),
                fk.opt("apply", L("Apply for New Ration Card / Family ID", "ಹೊಸ ಪಡಿತರ ಚೀಟಿ / ಕುಟುಂಬ ಗುರುತಿನ ಸಂಖ್ಯೆಗೆ ಅರ್ಜಿ")),
                fk.opt("track", L("Track New Card Application", "ಹೊಸ ಚೀಟಿ ಅರ್ಜಿ ಸ್ಥಿತಿ"))]),
            fk.text("rc", L("Enter Ration Card Number", "ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": ["status", "fps"]},
                    placeholder="150100123456", transform="digits", pattern=r"^\d{12}$", input_mode="numeric",
                    error=L("Ration card number must be 12 digits", "ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ 12 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.radio("ctype", L("Card Type", "ಚೀಟಿ ಪ್ರಕಾರ"), [fk.opt(k, v) for k, v in CARD_TYPES.items()], show_if=apply),
            fk.text("head", L("Head of Family (woman, as per Aadhaar)", "ಕುಟುಂಬದ ಮುಖ್ಯಸ್ಥರು (ಮಹಿಳೆ, ಆಧಾರ್ ಪ್ರಕಾರ)"), show_if=apply,
                    pattern=NAME_RE, placeholder=L("e.g. Lakshmi Devi", "ಉದಾ: ಲಕ್ಷ್ಮೀ ದೇವಿ"), error=L("Enter a valid name", "ಮಾನ್ಯ ಹೆಸರು ನಮೂದಿಸಿ")),
            fk.text("aadhaar", L("Aadhaar Number of Head of Family", "ಮುಖ್ಯಸ್ಥರ ಆಧಾರ್ ಸಂಖ್ಯೆ"), show_if=apply, placeholder="2345 6789 0123",
                    transform="digits", pattern=r"^\d{12}$", input_mode="numeric",
                    error=L("Aadhaar number must be exactly 12 digits", "ಆಧಾರ್ ಸಂಖ್ಯೆ ನಿಖರವಾಗಿ 12 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.text("mobile", L("Mobile Number", "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ"), show_if=apply, placeholder="9876543210", transform="digits",
                    pattern=r"^[6-9]\d{9}$", input_mode="numeric", error=L("Enter a valid 10-digit mobile number", "ಮಾನ್ಯ 10 ಅಂಕಿಯ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ")),
            fk.number("members", L("Number of Family Members", "ಕುಟುಂಬ ಸದಸ್ಯರ ಸಂಖ್ಯೆ"), min=1, max=12, placeholder="4", show_if=apply),
            fk.dropdown("district", L("District", "ಜಿಲ್ಲೆ"), K.DISTRICT_OPTIONS, show_if=apply),
            fk.text("taluk", L("Taluk", "ತಾಲ್ಲೂಕು"), show_if=apply, min_len=3, placeholder=L("e.g. Anekal", "ಉದಾ: ಆನೇಕಲ್")),
            fk.textarea("address", L("Residential Address", "ವಾಸಸ್ಥಳದ ವಿಳಾಸ"), show_if=apply, min_len=10,
                        placeholder=L("House no, street, village / ward", "ಮನೆ ಸಂಖ್ಯೆ, ರಸ್ತೆ, ಗ್ರಾಮ / ವಾರ್ಡ್")),
            fk.text("app_no", L("Enter Application Number", "ಅರ್ಜಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": "track"},
                    placeholder="FCS2611220001", transform="upper_nospace", pattern=r"^FCS\d{10}$",
                    error=L("Application number looks like FCS2611220001", "ಅರ್ಜಿ ಸಂಖ್ಯೆ FCS2611220001 ರೀತಿ ಇರುತ್ತದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        if any(w in t for w in ("new ration", "apply", "family id", "ಹೊಸ")):
            return {"action": "apply"}
        if any(w in t for w in ("shop", "fps", "ಅಂಗಡಿ", "entitlement", "ಅರ್ಹತೆ")):
            return {"action": "fps"}
        if any(w in t for w in ("track", "application")):
            return {"action": "track"}
        return {"action": "status"}

    def _family(self, rc):
        r = gen.rng("ahara", rc)
        members = r.randint(2, 6)
        head = gen.person(r, "F")
        aay = r.random() < 0.15
        nphh = (not aay) and r.random() < 0.12
        fam = [(head["name"], L("Head of Family", "ಕುಟುಂಬದ ಮುಖ್ಯಸ್ಥರು"), r.randint(32, 64), True)]
        for i in range(members - 1):
            fam.append((gen.person(r, "M" if i == 0 else None)["name"], RELATIONS[i % len(RELATIONS)], r.randint(4, 70), r.random() < 0.8))
        return r, members, aay, nphh, fam, gen.person(r)["name"]

    def submit(self, ctx, screen, v, data):
        a = v["action"]
        if a == "apply":
            return self._apply(ctx, v)
        if a == "track":
            return self.track(ctx, v["app_no"])
        if gen.is_missing(v["rc"]):
            return Errors({"rc": L("No ration card found with this number. Please check and re-enter.",
                                   "ಈ ಸಂಖ್ಯೆಯ ಪಡಿತರ ಚೀಟಿ ಕಂಡುಬಂದಿಲ್ಲ. ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ನಮೂದಿಸಿ.")})
        return self._status(ctx, v["rc"]) if a == "status" else self._fps(ctx, v["rc"])

    # ---------------------------------------------------------------------
    def _status(self, ctx, rc):
        r, members, aay, nphh, fam, _ = self._family(rc)
        card = (L("AAY - Antyodaya Anna Yojana", "ಅಂತ್ಯೋದಯ ಅನ್ನ ಯೋಜನೆ (AAY)") if aay else
                CARD_TYPES["nphh"] if nphh else CARD_TYPES["phh"])
        pending = [f for f in fam if not f[3]]
        done, todo = ctx.t(L("e-KYC done", "ಇ-ಕೆವೈಸಿ ಪೂರ್ಣ")), ctx.t(L("e-KYC pending", "ಇ-ಕೆವೈಸಿ ಬಾಕಿ"))
        lines = "\n".join(f"{i}. {ctx.t(n)} - {ctx.t(rel)}, {age} - *{done if ok else todo}*" for i, (n, rel, age, ok) in enumerate(fam, 1))
        msg = ctx.t(L(f"*Ration Card Details*\n\nRC No: *{rc}*\nType: *{ctx.t(card)}*\nStatus: *Active*\nMembers: {members}\n\n*Members:*\n{lines}",
                      f"*ಪಡಿತರ ಚೀಟಿ ವಿವರ*\n\nಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ: *{rc}*\nಪ್ರಕಾರ: *{ctx.t(card)}*\nಸ್ಥಿತಿ: *ಸಕ್ರಿಯ*\nಸದಸ್ಯರು: {members}\n\n*ಸದಸ್ಯರು:*\n{lines}"))
        if pending:
            word = "member" if len(pending) == 1 else "members"
            msg += ctx.t(L(f"\n\ne-KYC pending for {len(pending)} {word}. Visit your Fair Price Shop with Aadhaar for biometric e-KYC to continue receiving rations.",
                           f"\n\n{len(pending)} ಸದಸ್ಯರ ಇ-ಕೆವೈಸಿ ಬಾಕಿ ಇದೆ. ಪಡಿತರ ಮುಂದುವರಿಸಲು ಆಧಾರ್‌ನೊಂದಿಗೆ ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿಗೆ ಭೇಟಿ ನೀಡಿ ಬಯೋಮೆಟ್ರಿಕ್ ಇ-ಕೆವೈಸಿ ಮಾಡಿಸಿ."))
        else:
            msg += ctx.t(L("\n\ne-KYC completed for all members.", "\n\nಎಲ್ಲಾ ಸದಸ್ಯರ ಇ-ಕೆವೈಸಿ ಪೂರ್ಣಗೊಂಡಿದೆ."))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("My Fair Price Shop", "ನನ್ನ ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿ")), f"fps:{rc}"))))

    def _fps(self, ctx, rc):
        r, members, aay, nphh, fam, fps_owner = self._family(rc)
        fps_no = r.randint(1, 420)
        if nphh:
            ent = ctx.t(L("Not eligible for free rice (APL card)", "ಉಚಿತ ಅಕ್ಕಿಗೆ ಅರ್ಹರಲ್ಲ (APL ಚೀಟಿ)"))
        elif aay:
            ent = ctx.t(L("35 kg rice per card (free)", "ಪ್ರತಿ ಚೀಟಿಗೆ 35 ಕೆಜಿ ಅಕ್ಕಿ (ಉಚಿತ)"))
        else:
            ent = ctx.t(L(f"{members * 10} kg rice ({members} members × 10 kg, free)", f"{members * 10} ಕೆಜಿ ಅಕ್ಕಿ ({members} ಸದಸ್ಯರು × 10 ಕೆಜಿ, ಉಚಿತ)"))
        month = gen.month_year(gen.today(), ctx.lang)
        msg = ctx.t(L(f"*Fair Price Shop*\n\nFPS No: *{fps_no}*\nDealer: {ctx.t(fps_owner)}\nTimings: 8:00 AM - 12:00 PM, 4:00 PM - 8:00 PM (Tuesday holiday)\n\n"
                      f"*Entitlement for {month}:*\n{ent}\n\nDistribution: 1st to 20th of every month\nAhara helpline: 1967",
                      f"*ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿ*\n\nಅಂಗಡಿ ಸಂಖ್ಯೆ: *{fps_no}*\nವಿತರಕರು: {ctx.t(fps_owner)}\nಸಮಯ: ಬೆಳಿಗ್ಗೆ 8 - ಮಧ್ಯಾಹ್ನ 12, ಸಂಜೆ 4 - ರಾತ್ರಿ 8 (ಮಂಗಳವಾರ ರಜೆ)\n\n"
                      f"*{month} ರ ಅರ್ಹತೆ:*\n{ent}\n\nವಿತರಣೆ: ಪ್ರತಿ ತಿಂಗಳ 1 ರಿಂದ 20 ರವರೆಗೆ\nಆಹಾರ ಸಹಾಯವಾಣಿ: 1967"))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx)))

    def _apply(self, ctx, v):
        app = "FCS" + dt.date.today().strftime("%y%m%d") + gen.ref_id("", 4)
        rec = {k: v[k] for k in ("ctype", "head", "aadhaar", "mobile", "members", "district", "taluk", "address")}
        db.rec_put("rc_app", app, rec, ctx.session_id)
        dist = ctx.t(K.DISTRICT_NAME[v["district"]])
        fname = f"Ration_Card_Acknowledgement_{app}.pdf"
        doc_id = docs.create(ctx.session_id, "rc_ack", fname, {
            "lang": ctx.lang, "place": v["taluk"], "verify_url": "ahara.karnataka.gov.in",
            "dept": ctx.t(DEPT), "dept_sub": ctx.t(L(f"Office of the Deputy Director (Food), {dist}", f"ಉಪ ನಿರ್ದೇಶಕರ (ಆಹಾರ) ಕಚೇರಿ, {dist}")),
            "title": ctx.t(L("ACKNOWLEDGEMENT", "ಸ್ವೀಕೃತಿ ಪತ್ರ")), "subtitle": ctx.t(L("Application for New Ration Card", "ಹೊಸ ಪಡಿತರ ಚೀಟಿಗೆ ಅರ್ಜಿ")),
            "ref_label": ctx.t(L("Application No", "ಅರ್ಜಿ ಸಂಖ್ಯೆ")), "ref": app,
            "sections": [{"rows": [
                [ctx.t(L("Card Type", "ಚೀಟಿ ಪ್ರಕಾರ")), ctx.t(CARD_TYPES[v["ctype"]])], [ctx.t(L("Head of Family", "ಕುಟುಂಬದ ಮುಖ್ಯಸ್ಥರು")), v["head"]],
                [ctx.t(L("Aadhaar", "ಆಧಾರ್")), masked_aadhaar(v["aadhaar"])], [ctx.t(L("Mobile", "ಮೊಬೈಲ್")), v["mobile"]],
                [ctx.t(L("Members", "ಸದಸ್ಯರು")), v["members"]], [ctx.t(L("Address", "ವಿಳಾಸ")), f"{v['address']}, {v['taluk']}, {dist}"]]}],
            "notes": [ctx.t(L("Sakala service guarantee: ration card within 30 working days after field verification.",
                              "ಸಕಾಲ ಸೇವಾ ಖಾತರಿ: ಸ್ಥಳ ಪರಿಶೀಲನೆಯ ನಂತರ 30 ಕೆಲಸದ ದಿನಗಳೊಳಗೆ ಪಡಿತರ ಚೀಟಿ."))],
            "signatory": {"name": ctx.t(L("Deputy Director (Food)", "ಉಪ ನಿರ್ದೇಶಕರು (ಆಹಾರ)")), "designation": dist}})
        msg = ctx.t(L(f"*New Ration Card - Application Submitted*\n\nApplication No: *{app}*\nCard Type: {ctx.t(CARD_TYPES[v['ctype']])}\nHead of Family: {v['head']}\n"
                      f"Members: {v['members']}\nTaluk Office: {v['taluk']}, {dist}\n\nA Food Inspector will verify the family details. Sakala guarantee: *30 working days*.",
                      f"*ಹೊಸ ಪಡಿತರ ಚೀಟಿ - ಅರ್ಜಿ ಸಲ್ಲಿಸಲಾಗಿದೆ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: *{app}*\nಚೀಟಿ ಪ್ರಕಾರ: {ctx.t(CARD_TYPES[v['ctype']])}\nಕುಟುಂಬದ ಮುಖ್ಯಸ್ಥರು: {v['head']}\n"
                      f"ಸದಸ್ಯರು: {v['members']}\nತಾಲ್ಲೂಕು ಕಚೇರಿ: {v['taluk']}, {dist}\n\nಆಹಾರ ನಿರೀಕ್ಷಕರು ಕುಟುಂಬದ ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತಾರೆ. ಸಕಾಲ ಖಾತರಿ: *30 ಕೆಲಸದ ದಿನಗಳು*."))
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Track Status", "ಸ್ಥಿತಿ ನೋಡಿ")), f"track:{app}"))))

    def track(self, ctx, app):
        if gen.is_missing(app[3:]):
            return Errors({"app_no": L("No application found with this number.", "ಈ ಸಂಖ್ಯೆಯ ಅರ್ಜಿ ಕಂಡುಬಂದಿಲ್ಲ.")})
        rec = db.rec_get("rc_app", app)
        if rec:
            stage = stage_from_elapsed(rec["_created_at"], len(STAGES))
        else:
            r = gen.rng("rcapp", app)
            stage = r.choice([1, 2, 3, 4])
            p = gen.person(r, "F")
            rec = {"head": ctx.t(p["name"]), "ctype": r.choice(list(CARD_TYPES)), "members": r.randint(2, 6),
                   "district": r.choice(K.DISTRICTS)[0], "taluk": ctx.t(K.DISTRICT_NAME[r.choice(K.DISTRICTS)[0]]),
                   "address": ctx.t(L("Main Road", "ಮುಖ್ಯ ರಸ್ತೆ")), "aadhaar": gen.digits(r, 12), "mobile": "9" + gen.digits(r, 9)}
        dist = ctx.t(K.DISTRICT_NAME[rec["district"]])
        msg = ctx.t(L(f"*New Ration Card - Application Status*\n\nApplication No: {app}\nHead of Family: {rec['head']}\nCard Type: {ctx.t(CARD_TYPES[rec['ctype']])}\n\n",
                      f"*ಹೊಸ ಪಡಿತರ ಚೀಟಿ - ಅರ್ಜಿ ಸ್ಥಿತಿ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: {app}\nಕುಟುಂಬದ ಮುಖ್ಯಸ್ಥರು: {rec['head']}\nಚೀಟಿ ಪ್ರಕಾರ: {ctx.t(CARD_TYPES[rec['ctype']])}\n\n"))
        msg += timeline(ctx, STAGES, stage)
        if stage == len(STAGES) - 1:
            rc_no = "15" + gen.rng("rcno", app).choice("0123456789") + gen.digits(gen.rng("rcno", app), 9)
            fname = f"e_Ration_Card_{rc_no}.pdf"
            doc_id = docs.create(ctx.session_id, "e_ration_card", fname, {
                "lang": ctx.lang, "place": rec["taluk"], "verify_url": "ahara.karnataka.gov.in", "dept": ctx.t(DEPT),
                "dept_sub": ctx.t(L(f"Office of the Deputy Director (Food), {dist}", f"ಉಪ ನಿರ್ದೇಶಕರ (ಆಹಾರ) ಕಚೇರಿ, {dist}")),
                "title": ctx.t(L("e-RATION CARD", "ಇ-ಪಡಿತರ ಚೀಟಿ")), "subtitle": ctx.t(CARD_TYPES[rec["ctype"]]),
                "ref_label": ctx.t(L("Ration Card No", "ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ")), "ref": rc_no,
                "highlight": {"label": ctx.t(L("Monthly entitlement", "ಮಾಸಿಕ ಅರ್ಹತೆ")),
                              "value": ctx.t(L(f"{int(rec['members']) * 10} kg rice", f"{int(rec['members']) * 10} ಕೆಜಿ ಅಕ್ಕಿ")) if rec["ctype"] == "phh" else ctx.t(L("Not applicable (APL)", "ಅನ್ವಯಿಸುವುದಿಲ್ಲ (APL)"))},
                "sections": [{"rows": [[ctx.t(L("Head of Family", "ಕುಟುಂಬದ ಮುಖ್ಯಸ್ಥರು")), rec["head"]], [ctx.t(L("Aadhaar", "ಆಧಾರ್")), masked_aadhaar(rec["aadhaar"])],
                                       [ctx.t(L("Members", "ಸದಸ್ಯರು")), rec["members"]], [ctx.t(L("Address", "ವಿಳಾಸ")), f"{rec['address']}, {rec['taluk']}, {dist}"],
                                       [ctx.t(L("Application No", "ಅರ್ಜಿ ಸಂಖ್ಯೆ")), app]]}],
                "notes": [ctx.t(L("Complete biometric e-KYC of all members at the Fair Price Shop to activate the card.", "ಚೀಟಿ ಸಕ್ರಿಯಗೊಳಿಸಲು ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿಯಲ್ಲಿ ಎಲ್ಲಾ ಸದಸ್ಯರ ಬಯೋಮೆಟ್ರಿಕ್ ಇ-ಕೆವೈಸಿ ಪೂರ್ಣಗೊಳಿಸಿ."))],
                "signatory": {"name": ctx.t(L("Deputy Director (Food)", "ಉಪ ನಿರ್ದೇಶಕರು (ಆಹಾರ)")), "designation": dist}})
            msg += ctx.t(L(f"\n\nRation Card No: *{rc_no}*\nYour e-ration card is ready. Download it below.", f"\n\nಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ: *{rc_no}*\nನಿಮ್ಮ ಇ-ಪಡಿತರ ಚೀಟಿ ಸಿದ್ಧವಾಗಿದೆ. ಕೆಳಗೆ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ."))
            return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx)))
        msg += ctx.t(L("\n\n_Status updates automatically. Check again shortly._", "\n\n_ಸ್ಥಿತಿ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನವೀಕರಣಗೊಳ್ಳುತ್ತದೆ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪರಿಶೀಲಿಸಿ._"))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx, self.btn(ctx.t(L("Refresh Status", "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ")), f"track:{app}"))))

    def on_button(self, ctx, arg):
        kind, _, val = arg.partition(":")
        if kind == "fps":
            return self._fps(ctx, val)
        if kind == "track":
            return self.track(ctx, val)
        return None

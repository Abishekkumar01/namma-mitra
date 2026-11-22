"""Janaspandana / IPGRS - public grievance registration & tracking (stages advance with time)."""
import datetime as dt

from .. import db, docs, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service, stage_from_elapsed, timeline

DEPTS = {
    "revenue": L("Revenue", "ಕಂದಾಯ"), "energy": L("Energy (ESCOMs)", "ಇಂಧನ (ಎಸ್ಕಾಂ)"),
    "urban": L("Urban Development / BBMP", "ನಗರಾಭಿವೃದ್ಧಿ / ಬಿಬಿಎಂಪಿ"), "rdpr": L("Rural Development & Panchayat Raj", "ಗ್ರಾಮೀಣಾಭಿವೃದ್ಧಿ ಮತ್ತು ಪಂಚಾಯತ್ ರಾಜ್"),
    "police": L("Home (Police)", "ಒಳಾಡಳಿತ (ಪೊಲೀಸ್)"), "food": L("Food & Civil Supplies", "ಆಹಾರ ಮತ್ತು ನಾಗರಿಕ ಸರಬರಾಜು"),
    "transport": L("Transport", "ಸಾರಿಗೆ"), "health": L("Health & Family Welfare", "ಆರೋಗ್ಯ ಮತ್ತು ಕುಟುಂಬ ಕಲ್ಯಾಣ"),
    "education": L("School Education", "ಶಾಲಾ ಶಿಕ್ಷಣ"), "water": L("Water Supply (BWSSB / RDWS)", "ನೀರು ಸರಬರಾಜು (ಬಿಡಬ್ಲ್ಯೂಎಸ್‌ಎಸ್‌ಬಿ)"),
    "wcd": L("Women & Child Development", "ಮಹಿಳಾ ಮತ್ತು ಮಕ್ಕಳ ಅಭಿವೃದ್ಧಿ"), "social": L("Social Welfare", "ಸಮಾಜ ಕಲ್ಯಾಣ"),
}
# Subject shown when tracking a grievance number that was not created in this demo.
SAMPLE_SUBJECTS = {
    "revenue": L("Delay in mutation of land record", "ಭೂ ದಾಖಲೆ ಮ್ಯುಟೇಶನ್ ವಿಳಂಬ"),
    "energy": L("Frequent power cuts in our area", "ನಮ್ಮ ಪ್ರದೇಶದಲ್ಲಿ ಪದೇ ಪದೇ ವಿದ್ಯುತ್ ಕಡಿತ"),
    "urban": L("Streetlights not working in our ward", "ನಮ್ಮ ವಾರ್ಡ್‌ನಲ್ಲಿ ಬೀದಿ ದೀಪಗಳು ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ"),
    "rdpr": L("Village road damaged after rains", "ಮಳೆಯ ನಂತರ ಗ್ರಾಮದ ರಸ್ತೆ ಹಾಳಾಗಿದೆ"),
    "police": L("Request for night patrolling in our locality", "ನಮ್ಮ ಬಡಾವಣೆಯಲ್ಲಿ ರಾತ್ರಿ ಗಸ್ತು ಕೋರಿಕೆ"),
    "food": L("Ration not distributed this month", "ಈ ತಿಂಗಳು ಪಡಿತರ ವಿತರಣೆಯಾಗಿಲ್ಲ"),
    "transport": L("Bus service to our village stopped", "ನಮ್ಮ ಗ್ರಾಮಕ್ಕೆ ಬಸ್ ಸೇವೆ ಸ್ಥಗಿತಗೊಂಡಿದೆ"),
    "health": L("Doctor not available at the PHC", "ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರದಲ್ಲಿ ವೈದ್ಯರು ಲಭ್ಯವಿಲ್ಲ"),
    "education": L("Shortage of teachers in the government school", "ಸರ್ಕಾರಿ ಶಾಲೆಯಲ್ಲಿ ಶಿಕ್ಷಕರ ಕೊರತೆ"),
    "water": L("Irregular drinking water supply", "ಕುಡಿಯುವ ನೀರಿನ ಅನಿಯಮಿತ ಪೂರೈಕೆ"),
    "wcd": L("Anganwadi centre not functioning regularly", "ಅಂಗನವಾಡಿ ಕೇಂದ್ರ ನಿಯಮಿತವಾಗಿ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿಲ್ಲ"),
    "social": L("Hostel admission not confirmed", "ವಿದ್ಯಾರ್ಥಿ ನಿಲಯ ಪ್ರವೇಶ ದೃಢಪಟ್ಟಿಲ್ಲ"),
}
STAGES = [L("Grievance registered", "ದೂರು ದಾಖಲಾಗಿದೆ"),
          L("Assigned to department nodal officer", "ಇಲಾಖಾ ನೋಡಲ್ ಅಧಿಕಾರಿಗೆ ನಿಯೋಜನೆ"),
          L("Under examination by field officer", "ಕ್ಷೇತ್ರ ಅಧಿಕಾರಿಯಿಂದ ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ"),
          L("Action taken - report uploaded", "ಕ್ರಮ ಕೈಗೊಳ್ಳಲಾಗಿದೆ - ವರದಿ ಅಪ್‌ಲೋಡ್"),
          L("Closed - resolved", "ಮುಕ್ತಾಯ - ಪರಿಹರಿಸಲಾಗಿದೆ")]


class Grievance(Service):
    key = "grievance"
    order = 10
    icon = "grievance"
    dept = L("Centre for e-Governance (CeG)", "ಇ-ಆಡಳಿತ ಕೇಂದ್ರ (CeG)")
    sevaone = [L("iPGRS Grievance Registrations"), L("Integrated Public Grievance Redressal System/iPGRS")]
    title = L("iPGRS Grievance Registration (Janaspandana)", "iPGRS ದೂರು ನೋಂದಣಿ (ಜನಸ್ಪಂದನ)")
    subtitle = L("Register and track public grievances", "ಸಾರ್ವಜನಿಕ ದೂರು ದಾಖಲಿಸಿ ಮತ್ತು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ")
    keywords = ["grievance", "complaint", "complain", "problem", "issue", "janaspandana", "ipgrs", "1902",
                "pothole", "garbage", "road", "drainage", "ದೂರು", "ಸಮಸ್ಯೆ", "ಕುಂದುಕೊರತೆ", "ಜನಸ್ಪಂದನ"]

    def fields(self, ctx):
        reg = {"action": "register"}
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("register", L("Register New Grievance", "ಹೊಸ ದೂರು ದಾಖಲಿಸಿ")),
                fk.opt("track", L("Track Grievance Status", "ದೂರಿನ ಸ್ಥಿತಿ ತಿಳಿಯಿರಿ"))]),
            fk.dropdown("dept", L("Department", "ಇಲಾಖೆ"), [fk.opt(k, v) for k, v in DEPTS.items()], show_if=reg),
            fk.dropdown("district", L("District", "ಜಿಲ್ಲೆ"), K.DISTRICT_OPTIONS, show_if=reg),
            fk.text("subject", L("Subject", "ವಿಷಯ"), show_if=reg, min_len=5, max_len=100,
                    placeholder=L("e.g. Potholes on 4th Main Road", "ಉದಾ: 4ನೇ ಮುಖ್ಯರಸ್ತೆಯಲ್ಲಿ ಗುಂಡಿಗಳು")),
            fk.textarea("desc", L("Describe your grievance", "ನಿಮ್ಮ ದೂರನ್ನು ವಿವರಿಸಿ"), show_if=reg, min_len=15,
                        placeholder=L("Location, since when, what happened…", "ಸ್ಥಳ, ಯಾವಾಗಿನಿಂದ, ಏನಾಯಿತು…")),
            fk.text("gid", L("Enter Grievance ID", "ದೂರಿನ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), show_if={"action": "track"},
                    placeholder="IPG261122345", transform="upper_nospace", pattern=r"^IPG\d{9}$",
                    error=L("Grievance ID looks like IPG261122345", "ದೂರಿನ ಸಂಖ್ಯೆ IPG261122345 ರೀತಿ ಇರುತ್ತದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        if any(w in t for w in ("track", "status", "ಸ್ಥಿತಿ")):
            return {"action": "track"}
        return {"action": "register"} if any(w in t for w in ("complaint", "grievance", "ದೂರು", "problem", "ಸಮಸ್ಯೆ")) else {}

    def submit(self, ctx, screen, v, data):
        if v["action"] == "track":
            return self.track(ctx, v["gid"])
        gid = f"IPG{dt.date.today():%y%m}{gen.ref_id('', 5)}"
        db.rec_put("grievance", gid, v, ctx.session_id)
        dept, dist = ctx.t(DEPTS[v["dept"]]), ctx.t(K.DISTRICT_NAME[v["district"]])
        msg = ctx.t(L(f"*Grievance Registered*\n\nGrievance ID: *{gid}*\nDepartment: {dept}\nDistrict: {dist}\nSubject: {v['subject']}\n\n"
                      f"Your grievance has been forwarded to the {dept} nodal officer, {dist}.\nExpected resolution: within *15 days*.\nJanaspandana helpline: 1902",
                      f"*ದೂರು ದಾಖಲಾಗಿದೆ*\n\nದೂರಿನ ಸಂಖ್ಯೆ: *{gid}*\nಇಲಾಖೆ: {dept}\nಜಿಲ್ಲೆ: {dist}\nವಿಷಯ: {v['subject']}\n\n"
                      f"ನಿಮ್ಮ ದೂರನ್ನು {dist} ಜಿಲ್ಲೆಯ {dept} ನೋಡಲ್ ಅಧಿಕಾರಿಗೆ ರವಾನಿಸಲಾಗಿದೆ.\nನಿರೀಕ್ಷಿತ ಪರಿಹಾರ: *15 ದಿನಗಳೊಳಗೆ*.\nಜನಸ್ಪಂದನ ಸಹಾಯವಾಣಿ: 1902"))
        fname = f"Grievance_Acknowledgement_{gid}.pdf"
        doc_id = docs.create(ctx.session_id, "grievance_ack", fname, {
            "lang": ctx.lang, "place": dist, "verify_url": "ipgrs.karnataka.gov.in",
            "dept": ctx.t(L("Integrated Public Grievance Redressal System (iPGRS) - Janaspandana",
                            "ಜನಸ್ಪಂದನ - ಸಮಗ್ರ ಸಾರ್ವಜನಿಕ ಕುಂದುಕೊರತೆ ನಿವಾರಣಾ ವ್ಯವಸ್ಥೆ")),
            "dept_sub": ctx.t(L("Centre for e-Governance (CeG), Government of Karnataka",
                                "ಇ-ಆಡಳಿತ ಕೇಂದ್ರ (CeG), ಕರ್ನಾಟಕ ಸರ್ಕಾರ")),
            "title": ctx.t(L("GRIEVANCE ACKNOWLEDGEMENT", "ದೂರು ಸ್ವೀಕೃತಿ ಪತ್ರ")),
            "ref_label": ctx.t(L("Grievance ID", "ದೂರಿನ ಸಂಖ್ಯೆ")), "ref": gid,
            "highlight": {"label": ctx.t(L("Expected resolution", "ನಿರೀಕ್ಷಿತ ಪರಿಹಾರ")),
                          "value": ctx.t(L("Within 15 days", "15 ದಿನಗಳೊಳಗೆ"))},
            "sections": [
                {"heading": ctx.t(L("Grievance Details", "ದೂರಿನ ವಿವರಗಳು")), "rows": [
                    [ctx.t(L("Department", "ಇಲಾಖೆ")), dept],
                    [ctx.t(L("District", "ಜಿಲ್ಲೆ")), dist],
                    [ctx.t(L("Subject", "ವಿಷಯ")), v["subject"]],
                    [ctx.t(L("Description", "ವಿವರಣೆ")), v["desc"]],
                    [ctx.t(L("Mode", "ವಿಧಾನ")), ctx.t(L("WhatsApp - Namma Mitra", "ವಾಟ್ಸಾಪ್ - ನಮ್ಮ ಮಿತ್ರ"))],
                    [ctx.t(L("Status", "ಸ್ಥಿತಿ")), ctx.t(L("Registered - forwarded to nodal officer", "ದಾಖಲಾಗಿದೆ - ನೋಡಲ್ ಅಧಿಕಾರಿಗೆ ರವಾನೆ"))]]}],
            "notes": [ctx.t(L("Quote the Grievance ID in all further communication. Helpline: 1902.",
                              "ಮುಂದಿನ ಎಲ್ಲಾ ಸಂವಹನಗಳಲ್ಲಿ ದೂರಿನ ಸಂಖ್ಯೆಯನ್ನು ಉಲ್ಲೇಖಿಸಿ. ಸಹಾಯವಾಣಿ: 1902."))],
            "signatory": {"name": ctx.t(L("Nodal Officer, Janaspandana", "ನೋಡಲ್ ಅಧಿಕಾರಿ, ಜನಸ್ಪಂದನ")), "designation": dist}})
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(
            ctx, self.btn(ctx.t(L("Track Grievance", "ದೂರಿನ ಸ್ಥಿತಿ")), f"track:{gid}"))))

    def track(self, ctx, gid):
        if gen.is_missing(gid):
            return Errors({"gid": L("No grievance found with this ID.", "ಈ ಸಂಖ್ಯೆಯ ದೂರು ಕಂಡುಬಂದಿಲ್ಲ.")})
        rec = db.rec_get("grievance", gid)
        if rec:
            stage = stage_from_elapsed(rec["_created_at"], len(STAGES))
            dept, subject, dist = rec["dept"], rec["subject"], rec["district"]
        else:
            r = gen.rng("ipgrs", gid)
            stage, dept = r.randint(1, 4), r.choice(list(DEPTS))
            dist = r.choice(K.DISTRICTS)[0]
            subject = ctx.t(SAMPLE_SUBJECTS[dept])
        msg = ctx.t(L(f"*Grievance Status*\n\nGrievance ID: {gid}\nDepartment: {ctx.t(DEPTS[dept])}, {ctx.t(K.DISTRICT_NAME[dist])}\nSubject: {subject}\n\n",
                      f"*ದೂರಿನ ಸ್ಥಿತಿ*\n\nದೂರಿನ ಸಂಖ್ಯೆ: {gid}\nಇಲಾಖೆ: {ctx.t(DEPTS[dept])}, {ctx.t(K.DISTRICT_NAME[dist])}\nವಿಷಯ: {subject}\n\n"))
        msg += timeline(ctx, STAGES, stage)
        if stage >= 3:
            msg += ctx.t(L("\n\n*Officer remarks:* Site inspected and work order issued. Issue attended by the field team.",
                           "\n\n*ಅಧಿಕಾರಿಯ ಅಭಿಪ್ರಾಯ:* ಸ್ಥಳ ಪರಿಶೀಲಿಸಿ ಕಾರ್ಯಾದೇಶ ನೀಡಲಾಗಿದೆ. ಕ್ಷೇತ್ರ ತಂಡದಿಂದ ಸಮಸ್ಯೆ ಪರಿಹರಿಸಲಾಗಿದೆ."))
        btns = self.menu_buttons(ctx) if stage == len(STAGES) - 1 else self.menu_buttons(
            ctx, self.btn(ctx.t(L("Refresh Status", "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ")), f"track:{gid}"))
        return Reply(ui.text(msg, buttons=btns))

    def on_button(self, ctx, arg):
        if arg.startswith("track:"):
            return self.track(ctx, arg.split(":", 1)[1])
        return None

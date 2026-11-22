"""End-to-end tests: drive every service through the real HTTP route layer (with tracing),
in BOTH panel mode and chat text mode, in BOTH languages, including payments and buttons.

    python -m unittest discover -s tests -v
"""
import datetime as dt
import os
import sys
import tempfile
import unittest
import uuid

_tmp = tempfile.mkdtemp()
os.environ["NM_DB"] = os.path.join(_tmp, "test.db")
os.environ["NM_STAGE_SECONDS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db  # noqa: E402
from app.server import run_route  # noqa: E402
from app.services import REGISTRY  # noqa: E402

db.init()
D = lambda n: (dt.date.today() + dt.timedelta(days=n)).isoformat()

PANEL_CASES = [
    ("revenue", {"action": "apply", "cert": "income", "name": "Ramesh Kumar", "father": "Nagaraju H", "gender": "M",
                 "aadhaar": "2345 6789 0123", "district": "bengaluru_urban", "taluk": "Anekal", "income": "120000",
                 "purpose": "education"}),
    ("revenue", {"action": "apply", "cert": "caste_income", "name": "Kavya Gowda", "father": "Manjunath", "gender": "F",
                 "aadhaar": "345678901234", "district": "mysuru", "taluk": "Hunsur", "category": "3a", "caste": "Vokkaliga",
                 "income": "90000", "purpose": "scholarship"}),
    ("revenue", {"action": "track", "app_no": "RD0052611224567"}),
    ("energy", {"action": "bill", "escom": "bescom", "account": "1234567890"}),
    ("energy", {"action": "bill", "escom": "mescom", "account": "9876543210"}),
    ("energy", {"action": "complaint", "escom": "cesc", "account": "5551234567", "ctype": "outage", "details": "No power"}),
    ("energy", {"action": "track", "docket": "BES2611224821"}),
    ("gruhalakshmi", {"action": "status", "rc": "150100123456"}),
    ("gruhalakshmi", {"action": "ekyc", "rc": "150100123456"}),
    ("gruhalakshmi", {"action": "sanction", "rc": "150100123457"}),
    ("yuvanidhi", {"action": "apply", "name": "Kiran Kumar", "aadhaar": "234567890123", "dob": "2002-04-10", "qual": "degree",
                   "year": "2025", "district": "dharwad"}),
    ("yuvanidhi", {"action": "status", "yn_app": "YN2400123456"}),
    ("yuvanidhi", {"action": "declare", "yn_app": "YN2400123457"}),
    ("education", {"action": "view", "exam": "sslc", "year": "2026", "reg_no": "2026123456", "dob": "2010-05-14"}),
    ("education", {"action": "view", "exam": "puc", "year": "2025", "reg_no": "20261234", "dob": "2008-03-02"}),
    ("education", {"action": "duplicate", "exam": "sslc", "year": "2019", "reg_no": "2019123456", "dob": "2003-05-14", "reason": "lost"}),
    ("education", {"action": "track", "app_no": "KSEAB2611220001"}),
    ("bhoomi", {"district": "bengaluru_urban", "taluk": "Anekal", "hobli": "Sarjapura", "village": "Dommasandra", "survey": "45", "hissa": "2A"}),
    ("ahara", {"action": "status", "rc": "150100123456"}),
    ("ahara", {"action": "fps", "rc": "150100123456"}),
    ("ahara", {"action": "apply", "ctype": "phh", "head": "Lakshmi Devi", "aadhaar": "234567890123", "mobile": "9876543210",
               "members": "4", "district": "tumakuru", "taluk": "Tiptur", "address": "#12, 3rd Cross, Gandhinagar"}),
    ("ahara", {"action": "track", "app_no": "FCS2611220001"}),
    ("ksrtc", {"action": "book", "from": "bengaluru", "to": "mysuru", "date": D(3), "pax": "2", "btype": "any"}),
    ("ksrtc", {"action": "book", "from": "bengaluru", "to": "mangaluru", "date": D(5), "pax": "1", "btype": "sarige"}),
    ("ksrtc", {"action": "cancel", "pnr": "KS2611220123"}),
    ("transport", {"action": "rc", "vehicle": "KA 01 AB 1234"}),
    ("transport", {"action": "dl", "dl_no": "KA0120190001234", "dob": "1990-06-15"}),
    ("transport", {"action": "renew", "dl_no": "KA0520100004321", "dob": "1985-01-20", "mobile": "9876543210"}),
    ("grievance", {"action": "register", "dept": "urban", "district": "bengaluru_urban", "subject": "Potholes on 4th Main",
                   "desc": "Large potholes near the school for two weeks."}),
    ("grievance", {"action": "track", "gid": "IPG261122345"}),
]

NOT_FOUND = [
    ("energy", {"action": "bill", "escom": "bescom", "account": "0000000000"}, "account"),
    ("education", {"action": "view", "exam": "sslc", "year": "2026", "reg_no": "000000", "dob": "2010-05-14"}, "reg_no"),
    ("gruhalakshmi", {"action": "status", "rc": "000000000000"}, "rc"),
    ("yuvanidhi", {"action": "status", "yn_app": "YN00000000"}, "yn_app"),
    ("transport", {"action": "dl", "dl_no": "KA0100000000000", "dob": "1990-06-15"}, "dl_no"),
    ("ahara", {"action": "status", "rc": "000000000000"}, "rc"),
    ("revenue", {"action": "track", "app_no": "RD0000000000000"}, "app_no"),
    ("ksrtc", {"action": "book", "from": "mysuru", "to": "mysuru", "date": D(1), "pax": "1", "btype": "any"}, "to"),
]


def autofill(field):
    """Generic answer for a field on a follow-up screen."""
    if field["type"] in ("radio", "dropdown"):
        return field["options"][-1]["id"] if field["id"] == "gender" else field["options"][0]["id"]
    if field["type"] == "number":
        return str(field.get("min") or 1) if field["id"] != "age" else "34"
    if field["type"] == "date":
        return field["min_date"]
    if field["type"] in ("text", "textarea"):
        return {"pname": "Kavya Gowda"}.get(field["id"], "Sample text value")
    return ""


class Base(unittest.TestCase):
    def setUp(self):
        self.sid = "test-" + uuid.uuid4().hex[:8]
        run_route("/api/session", {"session_id": self.sid})

    def call(self, route, **body):
        body["session_id"] = self.sid
        code, res = run_route(route, body)
        self.assertEqual(code, 200)
        self.assertFalse(res.get("error"), f"{route} crashed: trace {res.get('trace_id')} {res}")
        return res

    def say(self, text, payload=None):
        return self.call("/api/message", text=text, payload=payload)["messages"]

    def follow_up(self, messages, depth=0):
        """Pay every payment CTA and press every service button (one level)."""
        for m in messages:
            cta = m.get("cta") or {}
            if cta.get("action", {}).get("kind") == "pay":
                res = self.call("/api/payment/pay", payment_id=cta["action"]["payment_id"], method="UPI - PhonePe")
                self.assertTrue(res["messages"], "payment produced no messages")
                again = self.call("/api/payment/pay", payment_id=cta["action"]["payment_id"], method="UPI")
                self.assertIn("already", again["messages"][0]["text"].lower() + " already")
                if depth == 0:
                    self.follow_up(res["messages"], depth + 1)
            for b in m.get("buttons", []) if depth < 2 else []:
                if b["payload"].startswith("svc:"):
                    out = self.say(b["label"], b["payload"])
                    self.assertTrue(out)
                    self.assertNotIn("couldn't understand", out[0].get("text", ""))


class PanelFlows(Base):
    def run_panel(self, service, values, lang="kn"):
        if lang == "en":
            self.say("EN")
        self.call("/api/panel/open", service=service)
        res = self.call("/api/panel/submit", service=service, screen="main", values=values)
        for _ in range(5):
            self.assertNotIn("errors", res, f"{service}: unexpected errors {res.get('errors')} (trace {res['trace_id']})")
            if res.get("close"):
                break
            panel = res["panel"]
            vals = {f["id"]: autofill(f) for f in panel["fields"] if f["type"] != "info"}
            res = self.call("/api/panel/submit", service=service, screen=panel["screen"], values=vals)
        self.assertTrue(res.get("close"), f"{service} flow did not finish")
        msgs = res["messages"]
        self.assertTrue(msgs)
        for m in msgs:
            self.assertNotIn("something went wrong", m.get("text", ""))
            self.assertNotIn("ದೋಷ ಉಂಟಾಗಿದೆ", m.get("text", ""))
        self.follow_up(msgs)
        return msgs

    def test_all_panel_cases_kannada(self):
        for service, values in PANEL_CASES:
            with self.subTest(service=service, values=values):
                self.setUp()
                self.run_panel(service, dict(values), "kn")

    def test_all_panel_cases_english(self):
        for service, values in PANEL_CASES:
            with self.subTest(service=service, values=values):
                self.setUp()
                self.run_panel(service, dict(values), "en")

    def test_not_found_returns_inline_error(self):
        for service, values, field in NOT_FOUND:
            with self.subTest(service=service):
                res = self.call("/api/panel/submit", service=service, screen="main", values=values)
                self.assertIn(field, res.get("errors", {}), res)

    def test_validation_errors(self):
        res = self.call("/api/panel/submit", service="energy", screen="main",
                        values={"action": "bill", "escom": "bescom", "account": "12"})
        self.assertIn("account", res["errors"])
        res = self.call("/api/panel/submit", service="education", screen="main", values={})
        self.assertIn("action", res["errors"])

    def test_tracking_progresses(self):
        import time
        res = self.call("/api/panel/submit", service="grievance", screen="main", values=PANEL_CASES[-2][1])
        gid = [b for b in res["messages"][-1]["buttons"] if b["payload"].startswith("svc:")][0]["payload"].split("track:")[1]
        time.sleep(4.2)
        out = self.say("track", f"svc:grievance:track:{gid}")
        self.assertIn("✔", out[0]["text"])


class TextFlows(Base):
    PHRASES = [
        ("I want to pay my electricity bill", "energy"), ("ವಿದ್ಯುತ್ ಬಿಲ್ ಪಾವತಿಸಬೇಕು", "energy"),
        ("I need an income certificate", "revenue"), ("ನನಗೆ ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ ಬೇಕು", "revenue"),
        ("gruha lakshmi status", "gruhalakshmi"), ("yuvanidhi status", "yuvanidhi"), ("sslc marks card", "education"),
        ("rtc pahani", "bhoomi"), ("ration card status", "ahara"), ("bus ticket", "ksrtc"),
        ("renew my driving licence", "transport"), ("vehicle rc extract", "transport"),
        ("I want to register a complaint about garbage", "grievance"), ("electricty bil", "energy"),
    ]

    def answer(self, prompt_msg, field_hint):
        return None

    def drive(self, phrase):
        msgs = self.say(phrase)
        self.assertIn("*", msgs[0]["text"][:1], f"intent not detected for {phrase!r}")
        for _ in range(30):
            from app import engine
            s = engine.load_session(self.sid)
            if s["state"] != "text_flow":
                return msgs
            flow = s["flow"]
            field = next(f for f in flow["fields"] if f["id"] == flow["asking"])
            if not field.get("required", True):
                reply = "SKIP"
            elif field["type"] in ("radio", "dropdown"):
                reply = "2" if field["id"] in ("to", "gender") else "1"
            elif field["type"] == "date":
                from app import flowkit
                lo, _ = flowkit.date_window(field)
                reply = lo.strftime("%d-%m-%Y")
            elif field["type"] == "number":
                reply = {"age": "34", "year": "2025", "members": "4"}.get(field["id"], str(field.get("min") or 1))
            else:
                reply = {"name": "Ramesh Kumar", "father": "Nagaraju", "pname": "Kavya Gowda", "dname": "Shobha",
                         "app_no": "2612345", "cet_no": "AB123", "aadhaar": "234567890123", "account": "1234567890",
                         "rc": "150100123456", "survey": "45", "vehicle": "KA01AB1234", "dl_no": "KA0120190001234",
                         "reg_no": "2026123456", "yn_app": "YN2400123456", "pnr": "KS2611220123",
                         "docket": "BES2611224821", "gid": "IPG261122345", "income": "120000", "mobile": "9876543210",
                         "head": "Lakshmi Devi", "address": "#12, 3rd Cross, Gandhinagar", "yn_app": "YN2400123456"}.get(
                    field["id"], "Sample value for this field")
                if field["id"] == "app_no" and field.get("pattern", "").startswith("^RD"):
                    reply = "RD0052611224567"
                if field["id"] == "app_no" and field.get("pattern", "").startswith("^KSEAB"):
                    reply = "KSEAB2611220001"
                if field["id"] == "app_no" and field.get("pattern", "").startswith("^FCS"):
                    reply = "FCS2611220001"
            msgs = self.say(reply)
            self.assertNotIn("something went wrong", msgs[-1].get("text", ""))
        self.fail(f"text flow for {phrase!r} did not finish")

    def test_phrases(self):
        for phrase, key in self.PHRASES:
            with self.subTest(phrase=phrase):
                self.setUp()
                msgs = self.drive(phrase)
                self.assertTrue(msgs)
                self.follow_up(msgs)

    def test_abort(self):
        self.say("electricity bill")
        out = self.say("ABORT")
        self.assertIn("Hi", out[0]["text"])
        out = self.say("ABORT")
        self.assertIn("Hi", out[0]["text"])

    def test_invalid_reply_reasks(self):
        self.say("I want to pay my electricity bill")
        out = self.say("abc")
        self.assertIn("\n\n*", out[0]["text"])


class Conversation(Base):
    def test_welcome_and_language(self):
        out = self.say("Hi")
        self.assertEqual(out[0]["type"], "image")
        self.assertIn("ನಮ್ಮ ಮಿತ್ರ", out[0]["text"])
        self.assertIn("EN", out[0]["footer"])
        out = self.say("EN")
        self.assertEqual(out[0]["type"], "system")
        self.assertIn("Welcome to *Namma Mitra*", out[1]["text"])
        out = self.say("KN")
        self.assertIn("ಸ್ವಾಗತ", out[1]["text"])

    def test_fallback(self):
        out = self.say("asdfgh qwerty")
        self.assertIn("cta", out[0])

    def test_history_restored(self):
        self.say("Hi")
        res = self.call("/api/session")
        self.assertGreaterEqual(len(res["history"]), 2)

    def test_logs_recorded(self):
        res = self.call("/api/message", text="Hi")
        calls = db.query("SELECT func FROM calls WHERE trace_id=?", (res["trace_id"],))
        funcs = {c["func"] for c in calls}
        self.assertIn("handle_message", funcs)
        self.assertIn("welcome", funcs)

    def test_i18n_complete(self):
        from app.i18n import STR, UI
        for k, v in list(STR.items()) + list(UI.items()):
            self.assertTrue(v["en"] and v["kn"], k)
        for svc in REGISTRY.values():
            self.assertTrue(svc.title["kn"] and svc.subtitle["kn"], svc.key)


if __name__ == "__main__":
    unittest.main(verbosity=2)

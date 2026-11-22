"""Women and Child Development - Gruhalakshmi Yojana.

Seva One services covered: "Gruhalakshmi Yojana", "Track Gruhalakshmi Application Status",
"Gruhalakshmi EKYC service", "Gruhalakshmi sanction order".
Status and DBT history by Ration Card number (deterministic). The sanction order is issued as a PDF.
"""
from .. import docs, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service

RC = r"^\d{12}$"
RC_ERR = L("Ration card number must be 12 digits", "ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ 12 ಅಂಕಿಗಳಾಗಿರಬೇಕು")
DEPT = L("Women and Child Development Department", "ಮಹಿಳಾ ಮತ್ತು ಮಕ್ಕಳ ಅಭಿವೃದ್ಧಿ ಇಲಾಖೆ")


def beneficiary(rc):
    r = gen.rng("gl", rc)
    woman = gen.person(r, "F")
    return {"r": r, "name": woman["name"], "bank": r.choice(K.BANKS), "acct": gen.digits(r, 4),
            "months": r.randint(26, 38), "district": r.choice(K.DISTRICTS)[0], "ekyc": r.random() < 0.85,
            "app_no": "GL" + gen.digits(r, 10), "sanction": "WCD/GL/" + gen.digits(r, 6)}


class Gruhalakshmi(Service):
    key = "gruhalakshmi"
    order = 3
    icon = "gruhalakshmi"
    title = L("Gruhalakshmi Yojana", "ಗೃಹಲಕ್ಷ್ಮಿ ಯೋಜನೆ")
    subtitle = L("Application status, e-KYC and sanction order", "ಅರ್ಜಿ ಸ್ಥಿತಿ, ಇ-ಕೆವೈಸಿ ಮತ್ತು ಮಂಜೂರಾತಿ ಆದೇಶ")
    dept = DEPT
    sevaone = [L("Gruhalakshmi Yojana"), L("Track Gruhalakshmi Application Status"),
               L("Gruhalakshmi EKYC service"), L("Gruhalakshmi sanction order")]
    keywords = ["gruha lakshmi", "gruhalakshmi", "grihalakshmi", "2000", "sanction order", "ಗೃಹಲಕ್ಷ್ಮಿ", "ಗೃಹ ಲಕ್ಷ್ಮಿ", "ಮಂಜೂರಾತಿ"]

    def fields(self, ctx):
        return [
            fk.radio("action", L("Select Service", "ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"), [
                fk.opt("status", L("Track Gruhalakshmi Application Status", "ಗೃಹಲಕ್ಷ್ಮಿ ಅರ್ಜಿ ಸ್ಥಿತಿ")),
                fk.opt("ekyc", L("Gruhalakshmi e-KYC Status", "ಗೃಹಲಕ್ಷ್ಮಿ ಇ-ಕೆವೈಸಿ ಸ್ಥಿತಿ")),
                fk.opt("sanction", L("Download Sanction Order", "ಮಂಜೂರಾತಿ ಆದೇಶ ಡೌನ್‌ಲೋಡ್"))]),
            fk.text("rc", L("Enter Ration Card Number", "ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ"), placeholder="150100123456",
                    transform="digits", pattern=RC, error=RC_ERR, input_mode="numeric",
                    helper=L("The Gruhalakshmi application is linked to the ration card", "ಗೃಹಲಕ್ಷ್ಮಿ ಅರ್ಜಿ ಪಡಿತರ ಚೀಟಿಗೆ ಜೋಡಿಸಲಾಗಿದೆ")),
        ]

    def prefill(self, text):
        t = text.lower()
        if "kyc" in t or "ಕೆವೈಸಿ" in t:
            return {"action": "ekyc"}
        if "sanction" in t or "ಮಂಜೂರಾತಿ" in t:
            return {"action": "sanction"}
        return {"action": "status"}

    def submit(self, ctx, screen, v, data):
        if gen.is_missing(v["rc"]):
            return Errors({"rc": L("No Gruhalakshmi application is linked to this ration card number.",
                                   "ಈ ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆಗೆ ಯಾವುದೇ ಗೃಹಲಕ್ಷ್ಮಿ ಅರ್ಜಿ ಜೋಡಿಸಿಲ್ಲ.")})
        return getattr(self, "_" + v["action"])(ctx, v["rc"])

    def _history(self, ctx, r, n=6):
        lines = []
        for i, m in enumerate(gen.months_back(n)):
            if i == 0 and gen.today().day < 20:
                lines.append(f"{gen.month_year(m, ctx.lang)} - {ctx.t(L('Processing', 'ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ'))}")
                continue
            day = min(r.randint(5, 25), 28)
            lines.append(f"{gen.month_year(m, ctx.lang)} - *₹2,000* ({ctx.t(L('credited', 'ಜಮೆ'))} {day:02d}-{m.month:02d})")
        return "\n".join(lines)

    def _status(self, ctx, rc):
        b = beneficiary(rc)
        r, bank = b["r"], ctx.t(b["bank"])
        msg = ctx.t(L(
            f"*Gruhalakshmi - Application Status*\n\nApplication No: {b['app_no']}\nBeneficiary: *{ctx.t(b['name'])}*\n"
            f"Ration Card: {rc}\nBank: {bank} - A/c XXXXXX{b['acct']}\nStatus: *Approved - Active (DBT enabled)*\n\n"
            f"*Recent instalments (₹2,000 per month):*\n",
            f"*ಗೃಹಲಕ್ಷ್ಮಿ - ಅರ್ಜಿ ಸ್ಥಿತಿ*\n\nಅರ್ಜಿ ಸಂಖ್ಯೆ: {b['app_no']}\nಫಲಾನುಭವಿ: *{ctx.t(b['name'])}*\n"
            f"ಪಡಿತರ ಚೀಟಿ: {rc}\nಬ್ಯಾಂಕ್: {bank} - ಖಾತೆ XXXXXX{b['acct']}\nಸ್ಥಿತಿ: *ಅನುಮೋದಿತ - ಸಕ್ರಿಯ (ಡಿಬಿಟಿ)*\n\n"
            f"*ಇತ್ತೀಚಿನ ಕಂತುಗಳು (ತಿಂಗಳಿಗೆ ₹2,000):*\n"))
        msg += self._history(ctx, r)
        msg += ctx.t(L(f"\n\nTotal received so far: *{gen.inr(b['months'] * 2000, 0)}* ({b['months']} instalments)",
                       f"\n\nಇಲ್ಲಿಯವರೆಗೆ ಒಟ್ಟು ಜಮೆ: *{gen.inr(b['months'] * 2000, 0)}* ({b['months']} ಕಂತುಗಳು)"))
        return Reply(ui.text(msg, buttons=self.menu_buttons(
            ctx, self.btn(ctx.t(L("Download Sanction Order", "ಮಂಜೂರಾತಿ ಆದೇಶ ಡೌನ್‌ಲೋಡ್")), f"sanction:{rc}"))))

    def _ekyc(self, ctx, rc):
        b = beneficiary(rc)
        if b["ekyc"]:
            msg = ctx.t(L(f"*Gruhalakshmi - e-KYC Status*\n\nBeneficiary: {ctx.t(b['name'])}\nRation Card: {rc}\n"
                          f"Aadhaar e-KYC: *Completed*\nBank account seeding: *Verified (NPCI)*\n\nNo action is required. Instalments will continue every month.",
                          f"*ಗೃಹಲಕ್ಷ್ಮಿ - ಇ-ಕೆವೈಸಿ ಸ್ಥಿತಿ*\n\nಫಲಾನುಭವಿ: {ctx.t(b['name'])}\nಪಡಿತರ ಚೀಟಿ: {rc}\n"
                          f"ಆಧಾರ್ ಇ-ಕೆವೈಸಿ: *ಪೂರ್ಣಗೊಂಡಿದೆ*\nಬ್ಯಾಂಕ್ ಖಾತೆ ಜೋಡಣೆ: *ಪರಿಶೀಲಿಸಲಾಗಿದೆ (NPCI)*\n\nಯಾವುದೇ ಕ್ರಮ ಅಗತ್ಯವಿಲ್ಲ. ಕಂತುಗಳು ಪ್ರತಿ ತಿಂಗಳು ಮುಂದುವರಿಯುತ್ತವೆ."))
        else:
            msg = ctx.t(L(f"*Gruhalakshmi - e-KYC Status*\n\nBeneficiary: {ctx.t(b['name'])}\nRation Card: {rc}\n"
                          f"Aadhaar e-KYC: *Pending*\n\nPlease complete biometric e-KYC at the nearest Grama One, Karnataka One or Bapuji Seva Kendra with the beneficiary's Aadhaar. Instalments resume after e-KYC.",
                          f"*ಗೃಹಲಕ್ಷ್ಮಿ - ಇ-ಕೆವೈಸಿ ಸ್ಥಿತಿ*\n\nಫಲಾನುಭವಿ: {ctx.t(b['name'])}\nಪಡಿತರ ಚೀಟಿ: {rc}\n"
                          f"ಆಧಾರ್ ಇ-ಕೆವೈಸಿ: *ಬಾಕಿ*\n\nದಯವಿಟ್ಟು ಹತ್ತಿರದ ಗ್ರಾಮ ಒನ್, ಕರ್ನಾಟಕ ಒನ್ ಅಥವಾ ಬಾಪೂಜಿ ಸೇವಾ ಕೇಂದ್ರದಲ್ಲಿ ಫಲಾನುಭವಿಯ ಆಧಾರ್‌ನೊಂದಿಗೆ ಬಯೋಮೆಟ್ರಿಕ್ ಇ-ಕೆವೈಸಿ ಪೂರ್ಣಗೊಳಿಸಿ. ಇ-ಕೆವೈಸಿ ನಂತರ ಕಂತುಗಳು ಮುಂದುವರಿಯುತ್ತವೆ."))
        return Reply(ui.text(msg, buttons=self.menu_buttons(ctx)))

    def _sanction(self, ctx, rc):
        b = beneficiary(rc)
        dist = ctx.t(K.DISTRICT_NAME[b["district"]])
        fname = f"Gruhalakshmi_Sanction_Order_{b['app_no']}.pdf"
        doc_id = docs.create(ctx.session_id, "gl_sanction", fname, {
            "lang": ctx.lang, "place": dist, "verify_url": "sevasindhugs.karnataka.gov.in",
            "dept": ctx.t(DEPT), "dept_sub": ctx.t(L("Gruhalakshmi Yojana", "ಗೃಹಲಕ್ಷ್ಮಿ ಯೋಜನೆ")),
            "title": ctx.t(L("SANCTION ORDER", "ಮಂಜೂರಾತಿ ಆದೇಶ")),
            "ref_label": ctx.t(L("Sanction No", "ಮಂಜೂರಾತಿ ಸಂಖ್ಯೆ")), "ref": b["sanction"],
            "highlight": {"label": ctx.t(L("Sanctioned assistance", "ಮಂಜೂರಾದ ಸಹಾಯಧನ")), "value": ctx.t(L("₹2,000 per month", "ತಿಂಗಳಿಗೆ ₹2,000"))},
            "sections": [{"text": ctx.t(L(
                f"Under the Gruhalakshmi Yojana of the Government of Karnataka, financial assistance of ₹2,000 per month is sanctioned to "
                f"Smt {ctx.t(b['name'])}, woman head of the family holding Ration Card No. {rc}, {dist} District. The amount will be "
                f"credited every month through Direct Benefit Transfer to the Aadhaar-seeded bank account ending {b['acct']}.",
                f"ಕರ್ನಾಟಕ ಸರ್ಕಾರದ ಗೃಹಲಕ್ಷ್ಮಿ ಯೋಜನೆಯಡಿ, {dist} ಜಿಲ್ಲೆಯ ಪಡಿತರ ಚೀಟಿ ಸಂಖ್ಯೆ {rc} ರ ಕುಟುಂಬದ ಯಜಮಾನಿ ಶ್ರೀಮತಿ {ctx.t(b['name'])} "
                f"ಅವರಿಗೆ ತಿಂಗಳಿಗೆ ₹2,000 ಆರ್ಥಿಕ ಸಹಾಯಧನ ಮಂಜೂರು ಮಾಡಲಾಗಿದೆ. ಈ ಮೊತ್ತವನ್ನು ಪ್ರತಿ ತಿಂಗಳು {b['acct']} ರಿಂದ ಕೊನೆಗೊಳ್ಳುವ "
                f"ಆಧಾರ್ ಜೋಡಿತ ಬ್ಯಾಂಕ್ ಖಾತೆಗೆ ನೇರ ನಗದು ವರ್ಗಾವಣೆ ಮೂಲಕ ಜಮೆ ಮಾಡಲಾಗುವುದು."))},
                {"rows": [[ctx.t(L("Application No", "ಅರ್ಜಿ ಸಂಖ್ಯೆ")), b["app_no"]],
                          [ctx.t(L("Bank", "ಬ್ಯಾಂಕ್")), f"{ctx.t(b['bank'])} - XXXXXX{b['acct']}"],
                          [ctx.t(L("Status", "ಸ್ಥಿತಿ")), ctx.t(L("Approved - Active", "ಅನುಮೋದಿತ - ಸಕ್ರಿಯ"))]]}],
            "signatory": {"name": ctx.t(L("Deputy Director", "ಉಪ ನಿರ್ದೇಶಕರು")), "designation": f"{ctx.t(DEPT)}, {dist}"}})
        msg = ctx.t(L(f"*Gruhalakshmi - Sanction Order*\n\nSanction No: {b['sanction']}\nBeneficiary: {ctx.t(b['name'])}\n\nYour sanction order is attached below.",
                      f"*ಗೃಹಲಕ್ಷ್ಮಿ - ಮಂಜೂರಾತಿ ಆದೇಶ*\n\nಮಂಜೂರಾತಿ ಸಂಖ್ಯೆ: {b['sanction']}\nಫಲಾನುಭವಿ: {ctx.t(b['name'])}\n\nನಿಮ್ಮ ಮಂಜೂರಾತಿ ಆದೇಶವನ್ನು ಕೆಳಗೆ ಲಗತ್ತಿಸಲಾಗಿದೆ."))
        return Reply(ui.text(msg), ui.document(doc_id, fname, buttons=self.menu_buttons(ctx)))

    def on_button(self, ctx, arg):
        if arg.startswith("sanction:"):
            return self._sanction(ctx, arg.split(":", 1)[1])
        return None

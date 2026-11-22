"""Bhoomi - Land records (RTC / Pahani) for any district / taluk / village / survey number."""
from .. import docs, ui
from .. import flowkit as fk
from ..data import gen
from ..data import karnataka as K
from ..i18n import L
from .base import Errors, Reply, Service

COASTAL = {"dakshina_kannada", "udupi", "uttara_kannada"}
MALNAD = {"chikkamagaluru", "kodagu", "shivamogga", "hassan"}
NORTH = {"kalaburagi", "bidar", "raichur", "koppal", "yadgir", "vijayapura", "bagalkote", "ballari",
         "vijayanagara", "gadag", "haveri", "dharwad", "belagavi"}
CROPS = {
    "coastal": [L("Paddy", "ಭತ್ತ"), L("Arecanut", "ಅಡಿಕೆ"), L("Coconut", "ತೆಂಗು"), L("Cashew", "ಗೇರು")],
    "malnad": [L("Coffee", "ಕಾಫಿ"), L("Arecanut", "ಅಡಿಕೆ"), L("Pepper", "ಕಾಳುಮೆಣಸು"), L("Paddy", "ಭತ್ತ")],
    "north": [L("Tur (Red gram)", "ತೊಗರಿ"), L("Jowar", "ಜೋಳ"), L("Cotton", "ಹತ್ತಿ"), L("Bengal gram", "ಕಡಲೆ"), L("Sugarcane", "ಕಬ್ಬು")],
    "south": [L("Ragi", "ರಾಗಿ"), L("Maize", "ಮೆಕ್ಕೆಜೋಳ"), L("Coconut", "ತೆಂಗು"), L("Sugarcane", "ಕಬ್ಬು"), L("Mulberry", "ಹಿಪ್ಪುನೇರಳೆ")],
}
LAND_TYPES = [L("Dry (Khushki)", "ಖುಷ್ಕಿ"), L("Wet (Tari)", "ತರಿ"), L("Garden (Bagayat)", "ಬಾಗಾಯ್ತು")]
SOILS = [L("Red loamy", "ಕೆಂಪು ಗೋಡು"), L("Black cotton", "ಕಪ್ಪು ಎರೆ"), L("Laterite", "ಜಂಬಿಟ್ಟಿಗೆ"), L("Sandy loam", "ಮರಳು ಮಿಶ್ರಿತ")]
WATER = [L("Borewell", "ಕೊಳವೆಬಾವಿ"), L("Canal", "ಕಾಲುವೆ"), L("Rain-fed", "ಮಳೆ ಆಶ್ರಿತ"), L("Tank", "ಕೆರೆ")]


class Bhoomi(Service):
    key = "bhoomi"
    order = 6
    icon = "land"
    title = L("RTC Print (Pahani)", "ಪಹಣಿ ಮುದ್ರಣ (RTC Print)")
    dept = L("Survey, Settlement and Land Records (SSLR) - Revenue Department", "ಭೂಮಾಪನ, ಕಂದಾಯ ವ್ಯವಸ್ಥೆ ಮತ್ತು ಭೂದಾಖಲೆಗಳು (SSLR) - ಕಂದಾಯ ಇಲಾಖೆ")
    sevaone = [L("RTC Print / ಪಹಣಿ ಮುದ್ರಣ")]
    subtitle = L("Print RTC (Pahani) with owner and crop details", "ಪಹಣಿ (ಆರ್‌ಟಿಸಿ), ಮಾಲೀಕರು ಮತ್ತು ಬೆಳೆ ವಿವರ")
    keywords = ["rtc", "pahani", "land", "survey", "bhoomi", "land record", "khata", "mutation",
                "ಭೂಮಿ", "ಪಹಣಿ", "ಜಮೀನು", "ಸರ್ವೆ", "ಭೂದಾಖಲೆ", "ಆರ್‌ಟಿಸಿ"]

    def fields(self, ctx):
        return [
            fk.dropdown("district", L("District", "ಜಿಲ್ಲೆ"), K.DISTRICT_OPTIONS),
            fk.text("taluk", L("Taluk", "ತಾಲ್ಲೂಕು"), min_len=3, placeholder=L("e.g. Anekal", "ಉದಾ: ಆನೇಕಲ್")),
            fk.text("hobli", L("Hobli", "ಹೋಬಳಿ"), min_len=3, placeholder=L("e.g. Sarjapura", "ಉದಾ: ಸರ್ಜಾಪುರ")),
            fk.text("village", L("Village", "ಗ್ರಾಮ"), min_len=3, placeholder=L("e.g. Dommasandra", "ಉದಾ: ದೊಮ್ಮಸಂದ್ರ")),
            fk.text("survey", L("Survey Number", "ಸರ್ವೆ ಸಂಖ್ಯೆ"), placeholder="45", transform="digits",
                    pattern=r"^\d{1,4}$", input_mode="numeric",
                    error=L("Survey number must be 1-4 digits", "ಸರ್ವೆ ಸಂಖ್ಯೆ 1-4 ಅಂಕಿಗಳಾಗಿರಬೇಕು")),
            fk.text("hissa", L("Hissa Number", "ಹಿಸ್ಸಾ ಸಂಖ್ಯೆ"), required=False, placeholder="2A",
                    transform="upper_nospace", pattern=r"^[0-9A-Z/*]{1,8}$"),
        ]

    def submit(self, ctx, screen, v, data):
        if gen.is_missing(v["survey"]):
            return Errors({"survey": L("No RTC found for this survey number in the selected village.",
                                       "ಆಯ್ಕೆ ಮಾಡಿದ ಗ್ರಾಮದಲ್ಲಿ ಈ ಸರ್ವೆ ಸಂಖ್ಯೆಗೆ ಪಹಣಿ ಕಂಡುಬಂದಿಲ್ಲ.")})
        d = v["district"]
        region = "coastal" if d in COASTAL else "malnad" if d in MALNAD else "north" if d in NORTH else "south"
        r = gen.rng("rtc", d, v["taluk"].lower(), v["village"].lower(), v["survey"], v.get("hissa", ""))
        total_g = r.randint(20, 480)                      # guntas (40 guntas = 1 acre)
        n_owners = r.choice([1, 1, 2, 2, 3])
        splits, left = [], total_g
        for i in range(n_owners):
            share = left if i == n_owners - 1 else r.randint(10, max(10, left - 10 * (n_owners - i - 1)))
            splits.append(share)
            left -= share
        owners = [(ctx.t(gen.person(r, "M" if i == 0 else None)["name"]), s) for i, s in enumerate(splits)]
        ag = lambda g: f"{g // 40}-{g % 40:02d}"          # acres-guntas
        land_type = ctx.t(r.choice(LAND_TYPES))
        crops = r.sample(CROPS[region], 2)
        water = ctx.t(r.choice(WATER))
        loan = r.random() < 0.4
        bank = ctx.t(r.choice(K.BANKS))
        loan_amt = gen.inr(r.choice([50000, 100000, 150000, 300000]), 0)
        liability = (f"{bank} - {ctx.t(L('Crop loan', 'ಬೆಳೆ ಸಾಲ'))} {loan_amt}" if loan else ctx.t(L("Nil", "ಇಲ್ಲ")))
        mr = f"MR H{r.randint(1, 60)}/{r.choice(['2019-20', '2021-22', '2023-24', '2024-25'])}"
        sy = v["survey"] + (f"/{v['hissa']}" if v.get("hissa") else "")
        dist = ctx.t(K.DISTRICT_NAME[d])
        owner_lines = "\n".join(f"   {i}. {n} - {ag(s)} {ctx.t(L('A-G', 'ಎ-ಗುಂ'))}" for i, (n, s) in enumerate(owners, 1))
        msg = ctx.t(L(
            f"*RTC (Pahani) - Bhoomi*\n\nLocation: {v['village'].title()}, {v['hobli'].title()} Hobli, {v['taluk'].title()} Tq, {dist} Dist\n"
            f"Survey No: *{sy}*\nTotal Extent: *{ag(total_g)}* (Acres-Guntas)\nLand Type: {land_type}\nIrrigation: {water}\n\n"
            f"*Owners:*\n{owner_lines}\n\nCrops: {ctx.t(crops[0])} (Kharif), {ctx.t(crops[1])} (Rabi)\nLiabilities: {liability}\nLast Mutation: {mr}",
            f"*ಪಹಣಿ (ಆರ್‌ಟಿಸಿ) - ಭೂಮಿ*\n\nಸ್ಥಳ: {v['village']}, {v['hobli']} ಹೋಬಳಿ, {v['taluk']} ತಾ, {dist} ಜಿ\n"
            f"ಸರ್ವೆ ಸಂಖ್ಯೆ: *{sy}*\nಒಟ್ಟು ವಿಸ್ತೀರ್ಣ: *{ag(total_g)}* (ಎಕರೆ-ಗುಂಟೆ)\nಭೂಮಿ ಪ್ರಕಾರ: {land_type}\nನೀರಾವರಿ: {water}\n\n"
            f"*ಮಾಲೀಕರು:*\n{owner_lines}\n\nಬೆಳೆ: {ctx.t(crops[0])} (ಮುಂಗಾರು), {ctx.t(crops[1])} (ಹಿಂಗಾರು)\nಋಣಭಾರ: {liability}\nಕೊನೆಯ ಮ್ಯುಟೇಶನ್: {mr}"))
        doc_id = docs.create(ctx.session_id, "rtc", f"RTC_Sy{sy.replace('/', '-')}.pdf", {
            "lang": ctx.lang, "place": v["taluk"], "verify_url": "landrecords.karnataka.gov.in", "dept": ctx.t(L("Revenue Department - Bhoomi", "ಕಂದಾಯ ಇಲಾಖೆ - ಭೂಮಿ")),
            "dept_sub": ctx.t(L("Record of Rights, Tenancy and Crops (Form 16)", "ಹಕ್ಕು, ಹಿಡುವಳಿ ಮತ್ತು ಬೆಳೆ ಪಹಣಿ (ನಮೂನೆ 16)")),
            "title": ctx.t(L("RTC (PAHANI)", "ಪಹಣಿ (ಆರ್‌ಟಿಸಿ)")), "subtitle": f"{v['village']}, {v['hobli']}, {v['taluk']}, {dist}",
            "ref_label": ctx.t(L("Survey No", "ಸರ್ವೆ ಸಂಖ್ಯೆ")), "ref": sy,
            "sections": [
                {"heading": ctx.t(L("Land Details", "ಭೂಮಿ ವಿವರ")), "rows": [
                    [ctx.t(L("Total Extent (A-G)", "ಒಟ್ಟು ವಿಸ್ತೀರ್ಣ (ಎ-ಗುಂ)")), ag(total_g)],
                    [ctx.t(L("Land Type", "ಭೂಮಿ ಪ್ರಕಾರ")), land_type],
                    [ctx.t(L("Soil Type", "ಮಣ್ಣಿನ ಪ್ರಕಾರ")), ctx.t(r.choice(SOILS))],
                    [ctx.t(L("Water Source", "ನೀರಿನ ಮೂಲ")), water],
                    [ctx.t(L("Kharab (unfit)", "ಖರಾಬು")), f"0-{r.randint(0, 3):02d}"]]},
                {"heading": ctx.t(L("Owners (Column 9)", "ಮಾಲೀಕರು (ಕಾಲಂ 9)")), "table": {
                    "cols": ["#", ctx.t(L("Name", "ಹೆಸರು")), ctx.t(L("Extent (A-G)", "ವಿಸ್ತೀರ್ಣ (ಎ-ಗುಂ)")), ctx.t(L("Khata No", "ಖಾತೆ ಸಂಖ್ಯೆ"))],
                    "rows": [[i, n, ag(s), r.randint(100, 999)] for i, (n, s) in enumerate(owners, 1)]}},
                {"heading": ctx.t(L("Crop Details", "ಬೆಳೆ ವಿವರ")), "table": {
                    "cols": [ctx.t(L("Season", "ಋತು")), ctx.t(L("Crop", "ಬೆಳೆ")), ctx.t(L("Area (A-G)", "ವಿಸ್ತೀರ್ಣ (ಎ-ಗುಂ)"))],
                    "rows": [[ctx.t(L("Kharif 2026", "ಮುಂಗಾರು 2026")), ctx.t(crops[0]), ag(int(total_g * 0.6))],
                             [ctx.t(L("Rabi 2025-26", "ಹಿಂಗಾರು 2025-26")), ctx.t(crops[1]), ag(int(total_g * 0.4))]]}},
                {"heading": ctx.t(L("Liabilities (Column 11)", "ಋಣಭಾರ (ಕಾಲಂ 11)")), "rows": [
                    [ctx.t(L("Encumbrance", "ಋಣಭಾರ")), liability], [ctx.t(L("Mutation", "ಮ್ಯುಟೇಶನ್")), mr]]}],
            "notes": [ctx.t(L("Information copy - not to be used for legal purposes.", "ಮಾಹಿತಿ ಪ್ರತಿ - ಕಾನೂನು ಉದ್ದೇಶಗಳಿಗೆ ಬಳಸಬಾರದು."))],
            "signatory": {"name": ctx.t(L("Village Administrative Officer", "ಗ್ರಾಮ ಆಡಳಿತ ಅಧಿಕಾರಿ")), "designation": v["village"]}})
        return Reply(ui.text(msg), ui.document(doc_id, f"RTC_Sy{sy.replace('/', '-')}.pdf", buttons=self.menu_buttons(ctx)))

"""Deterministic record generation.

The demo must accept ANY well-formed number the presenter types. So instead of a fixed
seed table, every lookup seeds a PRNG from the input itself: the same account ID always
returns the same consumer, bill and history - repeatable on stage, different per input.

Reserved inputs that intentionally return "not found" (to show error handling):
any ID whose digits are all zero, e.g. 0000000000.
"""
import datetime as dt
import hashlib
import random

from ..i18n import L
from . import karnataka as K

MONTHS_KN = ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್",
             "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]


def rng(*parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def is_missing(value):
    digits = [c for c in str(value) if c.isdigit()]
    return bool(digits) and all(c == "0" for c in digits)


def today():
    return dt.date.today()


def inr(amount, decimals=2):
    """Indian digit grouping: 1234567.5 -> ₹12,34,567.50"""
    neg = amount < 0
    amount = abs(amount)
    whole = int(amount)
    frac = f"{amount - whole:.{decimals}f}"[1:] if decimals else ""
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-" if neg else "") + "₹" + s + frac


def dmy(d):
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return d.strftime("%d-%m-%Y")


def month_year(d, lang):
    names = MONTHS_KN if lang == "kn" else MONTHS_EN
    return f"{names[d.month - 1]} {d.year}"


def months_back(n, ref=None):
    """List of first-of-month dates, newest first, n months."""
    ref = ref or today()
    y, m = ref.year, ref.month
    out = []
    for _ in range(n):
        out.append(dt.date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def person(r, gender=None):
    g = gender or r.choice(["M", "F"])
    en, kn = r.choice(K.NAMES_F if g == "F" else K.NAMES_M)
    return {"name": L(en, kn), "gender": g}


def mask_name(name):
    parts = []
    for w in str(name).split():
        parts.append(w if len(w) <= 2 else w[0] + "*" * (len(w) - 2) + w[-1])
    return " ".join(parts)


def digits(r, n):
    return "".join(str(r.randint(0, 9)) for _ in range(n))


def ref_id(prefix, n=8):
    """Fresh (non-deterministic) reference for things created during the demo."""
    return prefix + "".join(str(random.randint(0, 9)) for _ in range(n))

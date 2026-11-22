"""Offline intent matching (no LLM, no API key).

Commands: greetings -> welcome, EN/KN -> language, ABORT -> cancel.
Service routing: weighted keyword match over each service's `keywords`
(English, Kannada script and Kanglish) + typo tolerance via difflib.
"""
import difflib
import re

from .services import REGISTRY
from .tracer import logged

GREETINGS = {"hi", "hii", "hiii", "hello", "hey", "helo", "namaste", "namaskara", "namaskar", "start", "menu",
             "main menu", "home", "ನಮಸ್ಕಾರ", "ಹಾಯ್", "ಹಲೋ", "ಮೆನು", "ನಮಸ್ತೆ"}
EN_CMDS = {"en", "eng", "english", "ಇಂಗ್ಲಿಷ್"}
KN_CMDS = {"kn", "kan", "kannada", "ಕನ್ನಡ"}
ABORT_CMDS = {"abort", "cancel", "stop", "exit", "quit", "ರದ್ದು", "ನಿಲ್ಲಿಸು"}


def normalise(text):
    return re.sub(r"\s+", " ", str(text).strip().lower().strip(".!?,"))


@logged
def command(text):
    t = normalise(text)
    if t in EN_CMDS:
        return "lang_en"
    if t in KN_CMDS:
        return "lang_kn"
    if t in ABORT_CMDS:
        return "abort"
    if t in GREETINGS:
        return "greet"
    return None


def _has(text, kw):
    if kw.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text) is not None
    return kw in text


@logged
def detect_service(text):
    """Return (service_key, score) for the best match, or (None, 0)."""
    t = normalise(text)
    tokens = [w for w in re.findall(r"[a-z]+", t) if len(w) >= 5]
    best, best_score = None, 0
    for svc in REGISTRY.values():
        score = 0
        for kw in svc.keywords:
            if _has(t, kw.lower()):
                score += 2 + len(kw)
        singles = [k for k in svc.keywords if k.isascii() and " " not in k and len(k) >= 5]
        for tok in tokens:
            if difflib.get_close_matches(tok, singles, n=1, cutoff=0.82) and not any(_has(t, k) for k in singles if k == tok):
                score += 4
        if score > best_score:
            best, best_score = svc.key, score
    return best, best_score

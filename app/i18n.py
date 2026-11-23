"""Bilingual text. Kannada (kn) is the default; English (en) on demand.

L("English", "ಕನ್ನಡ") is a tiny dict subclass. Anything user-facing is an L.
tr(obj, lang) picks the language. loc(obj, lang) walks nested lists/dicts and
resolves every L (also plain {"en","kn"} dicts that came back from JSON).
"""


class L(dict):
    def __init__(self, en, kn=None):
        super().__init__(en=en, kn=kn if kn is not None else en)


def _is_l(obj):
    return isinstance(obj, dict) and "en" in obj and set(obj.keys()) <= {"en", "kn"}


def tr(obj, lang):
    if obj is None:
        return None
    if _is_l(obj):
        return obj.get(lang) or obj.get("en")
    return obj


def loc(obj, lang):
    if _is_l(obj):
        return tr(obj, lang)
    if isinstance(obj, dict):
        return {k: loc(v, lang) for k, v in obj.items()}
    if isinstance(obj, list):
        return [loc(v, lang) for v in obj]
    return obj


STR = {
    # ---- welcome (mirrors the Mana Mitra welcome structure line by line) ----
    "welcome": L(
        "Welcome to *Namma Mitra* - Government of Karnataka's Citizen Services Assistant on WhatsApp!\n\n"
        "Access various government services, including certificates, bill payments, land records, "
        "guarantee scheme status, grievance registration and application tracking.\n\n"
        "💬 *Just ask Namma Mitra!*\n"
        "Simply type what you need in your own words, and Namma Mitra will guide you to the right service.\n\n"
        "For example:\n"
        " • \"I want to pay my electricity bill\"\n"
        " • \"I want to apply for an income certificate\"\n\n"
        "You can also choose a service from the menu below.\n\n"
        "Your Government. Just a Message Away.",
        "*ನಮ್ಮ ಮಿತ್ರಕ್ಕೆ ಸ್ವಾಗತ!*\n"
        "ಈಗ ವಾಟ್ಸಾಪ್‌ನಲ್ಲಿ ಸರ್ಕಾರಿ ಸೇವೆಗಳನ್ನು ಪಡೆಯಿರಿ.\n\n"
        "ಬಿಲ್‌ಗಳನ್ನು ಪಾವತಿಸಿ, ಪ್ರಮಾಣಪತ್ರಗಳನ್ನು ಪಡೆಯಿರಿ, ಭೂ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ, "
        "ಗ್ಯಾರಂಟಿ ಯೋಜನೆಗಳ ಸ್ಥಿತಿ ತಿಳಿಯಿರಿ, ದೂರುಗಳನ್ನು ದಾಖಲಿಸಿ ಮತ್ತು ಅರ್ಜಿಗಳನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ.\n\n"
        "💬 ನಿಮಗೆ ಏನು ಬೇಕು ಎಂದು ಟೈಪ್ ಮಾಡಿ!\n\n"
        "ಉದಾಹರಣೆ: *\"ವಿದ್ಯುತ್ ಬಿಲ್ ಪಾವತಿಸಬೇಕು\"* ಅಥವಾ *\"ನನಗೆ ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ ಬೇಕು\"*\n\n"
        "ಕೆಳಗಿನ ಮೆನುವಿನಿಂದಲೂ ಸೇವೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಬಹುದು.\n\n"
        "ನಮ್ಮ ಮಿತ್ರ - ಸರ್ಕಾರಿ ಸೇವೆಗಳು ಈಗ ಸುಲಭ!"),
    # Hint is deliberately in the *other* language, exactly like Mana Mitra.
    "welcome_hint": L("> ಕನ್ನಡ ಭಾಷೆಗಾಗಿ *KN* ಟೈಪ್ ಮಾಡಿ", "> Type *EN* for English language"),
    "choose_service": L("Choose Service", "ಸೇವೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ"),
    "lang_changed": L("Language changed successfully.", "ಭಾಷೆಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಬದಲಾಯಿಸಲಾಗಿದೆ."),

    # ---- flow control ----
    "abort_hint": L("> To stop the flow reply with *ABORT*", "> ಈ ಪ್ರಕ್ರಿಯೆಯನ್ನು ನಿಲ್ಲಿಸಲು *ABORT* ಎಂದು ಉತ್ತರಿಸಿ"),
    "flow_aborted": L("The current request has been cancelled. Type *Hi* to start again.",
                      "ಪ್ರಸ್ತುತ ವಿನಂತಿಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಾರಂಭಿಸಲು *Hi* ಎಂದು ಟೈಪ್ ಮಾಡಿ."),
    "nothing_to_abort": L("There is no active request to cancel. Type *Hi* to see the menu.",
                          "ರದ್ದುಗೊಳಿಸಲು ಯಾವುದೇ ಸಕ್ರಿಯ ವಿನಂತಿ ಇಲ್ಲ. ಮೆನು ನೋಡಲು *Hi* ಎಂದು ಟೈಪ್ ಮಾಡಿ."),
    "fallback": L(
        "Sorry, I couldn't understand that.\n\nYou can type things like:\n"
        " • \"electricity bill\"\n • \"income certificate\"\n • \"SSLC marks card\"\n"
        " • \"Gruha Lakshmi status\"\n • \"bus ticket to Mysuru\"\n\nor choose a service from the menu below.",
        "ಕ್ಷಮಿಸಿ, ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ.\n\nನೀವು ಈ ರೀತಿ ಟೈಪ್ ಮಾಡಬಹುದು:\n"
        " • \"ವಿದ್ಯುತ್ ಬಿಲ್\"\n • \"ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ\"\n • \"ಎಸ್‌ಎಸ್‌ಎಲ್‌ಸಿ ಅಂಕಪಟ್ಟಿ\"\n"
        " • \"ಗೃಹಲಕ್ಷ್ಮಿ ಸ್ಥಿತಿ\"\n • \"ಮೈಸೂರಿಗೆ ಬಸ್ ಟಿಕೆಟ್\"\n\nಅಥವಾ ಕೆಳಗಿನ ಮೆನುವಿನಿಂದ ಸೇವೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ."),
    "intent_start": L("*{title}*\n\nI'll help you with this. Please answer a few quick questions, "
                      "or tap *Open Form* to fill everything at once.",
                      "*{title}*\n\nನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ದಯವಿಟ್ಟು ಕೆಲವು ಪ್ರಶ್ನೆಗಳಿಗೆ ಉತ್ತರಿಸಿ, "
                      "ಅಥವಾ ಒಂದೇ ಬಾರಿಗೆ ಭರ್ತಿ ಮಾಡಲು *ಫಾರ್ಮ್ ತೆರೆಯಿರಿ* ಒತ್ತಿರಿ."),
    "open_form": L("Open Form", "ಫಾರ್ಮ್ ತೆರೆಯಿರಿ"),
    "reply_number": L("Reply with the option number.", "ಆಯ್ಕೆಯ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ."),
    "optional_skip": L("(Optional - reply *SKIP* to skip)", "(ಐಚ್ಛಿಕ - ಬಿಡಲು *SKIP* ಎಂದು ಉತ್ತರಿಸಿ)"),
    "invalid_option": L("Please reply with a number from the list.",
                        "ದಯವಿಟ್ಟು ಪಟ್ಟಿಯಲ್ಲಿರುವ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ."),
    "main_menu": L("Main Menu", "ಮುಖ್ಯ ಮೆನು"),
    "error_generic": L("Sorry, something went wrong while processing your request. Please try again.\n\nType *Hi* for the main menu.",
                       "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುವಾಗ ದೋಷ ಉಂಟಾಗಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.\n\nಮುಖ್ಯ ಮೆನುಗಾಗಿ *Hi* ಟೈಪ್ ಮಾಡಿ."),
    "form_submitted": L("Response sent", "ಪ್ರತಿಕ್ರಿಯೆ ಕಳುಹಿಸಲಾಗಿದೆ"),

    # ---- validation ----
    "required": L("This field is required", "ಈ ಕ್ಷೇತ್ರ ಕಡ್ಡಾಯ"),
    "select_option": L("Select an option", "ಒಂದು ಆಯ್ಕೆಯನ್ನು ಆರಿಸಿ"),
    "invalid_format": L("Invalid format. Please check and re-enter.", "ಅಮಾನ್ಯ ಸ್ವರೂಪ. ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ನಮೂದಿಸಿ."),
    "number_range": L("Enter a number between {min} and {max}", "{min} ರಿಂದ {max} ನಡುವಿನ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ"),
    "min_length": L("Please enter at least {n} characters", "ಕನಿಷ್ಠ {n} ಅಕ್ಷರಗಳನ್ನು ನಮೂದಿಸಿ"),
    "date_invalid": L("Enter a valid date as DD-MM-YYYY", "ಮಾನ್ಯ ದಿನಾಂಕವನ್ನು DD-MM-YYYY ರೂಪದಲ್ಲಿ ನಮೂದಿಸಿ"),
    "date_range": L("Date must be between {a} and {b}", "ದಿನಾಂಕ {a} ಮತ್ತು {b} ನಡುವೆ ಇರಬೇಕು"),
    "date_hint": L("(Format DD-MM-YYYY, e.g. {ex})", "(DD-MM-YYYY ರೂಪದಲ್ಲಿ, ಉದಾ: {ex})"),

    # ---- payments ----
    "already_paid": L("This payment has already been completed.", "ಈ ಪಾವತಿಯನ್ನು ಈಗಾಗಲೇ ಪೂರ್ಣಗೊಳಿಸಲಾಗಿದೆ."),
    "payment_missing": L("Payment request not found or expired. Please start again.",
                         "ಪಾವತಿ ವಿನಂತಿ ಕಂಡುಬಂದಿಲ್ಲ ಅಥವಾ ಅವಧಿ ಮುಗಿದಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಾರಂಭಿಸಿ."),
    "pay": L("Pay {amt}", "{amt} ಪಾವತಿಸಿ"),
}

# Strings the browser needs (panel chrome, composer placeholder, etc.).
UI = {
    "panel_title": L("Service Selection", "ಸೇವೆ ಆಯ್ಕೆ"),
    "panel_heading": L("Choose from one of the Citizens Services", "ನಾಗರಿಕ ಸೇವೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಆಯ್ಕೆಮಾಡಿ"),
    "select_label": L("Select Citizens Service", "ನಾಗರಿಕ ಸೇವೆ ಆಯ್ಕೆಮಾಡಿ"),
    "select_placeholder": L("Please Select One Service", "ದಯವಿಟ್ಟು ಒಂದು ಸೇವೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ"),
    "required_note": L("All fields are required unless marked Optional.", "ಐಚ್ಛಿಕ ಎಂದು ಗುರುತಿಸದ ಹೊರತು ಎಲ್ಲಾ ಕ್ಷೇತ್ರಗಳು ಕಡ್ಡಾಯ."),
    "online": L("online", "ಆನ್‌ಲೈನ್"),
    "secure_notice": L("This business uses a secure service from Meta to manage this chat. Click to learn more.",
                       "ಈ ವ್ಯವಹಾರವು ಈ ಚಾಟ್ ನಿರ್ವಹಿಸಲು Meta ದ ಸುರಕ್ಷಿತ ಸೇವೆಯನ್ನು ಬಳಸುತ್ತದೆ. ಇನ್ನಷ್ಟು ತಿಳಿಯಲು ಕ್ಲಿಕ್ ಮಾಡಿ."),
    "encrypted": L("Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to or share them.",
                   "ಸಂದೇಶಗಳು ಮತ್ತು ಕರೆಗಳು ಎಂಡ್-ಟು-ಎಂಡ್ ಎನ್‌ಕ್ರಿಪ್ಟ್ ಆಗಿವೆ. ಈ ಚಾಟ್‌ನಲ್ಲಿರುವವರು ಮಾತ್ರ ಓದಬಹುದು."),
    "download": L("Download", "ಡೌನ್‌ಲೋಡ್"),
    "pdf_meta": L("PDF document", "PDF ದಾಖಲೆ"),
    "view_response": L("View response", "ಪ್ರತಿಕ್ರಿಯೆ ನೋಡಿ"),
    "your_response": L("Your response", "ನಿಮ್ಮ ಪ್ರತಿಕ್ರಿಯೆ"),
    "response_note": L("These are the details you submitted. They cannot be edited.",
                       "ನೀವು ಸಲ್ಲಿಸಿದ ವಿವರಗಳು ಇವು. ಇವುಗಳನ್ನು ಬದಲಾಯಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ."),
    "confirm": L("Confirm", "ದೃಢೀಕರಿಸಿ"),
    "select_option": STR["select_option"],
    "number_range": STR["number_range"],
    "date_range": STR["date_range"],
    "required": STR["required"],
    "invalid_format": STR["invalid_format"],
    "search": L("Search", "ಹುಡುಕಿ"),
    "type_message": L("Type a message", "ಸಂದೇಶವನ್ನು ಟೈಪ್ ಮಾಡಿ"),
    "choose": L("Choose", "ಆಯ್ಕೆಮಾಡಿ"),
    "optional": L("Optional", "ಐಚ್ಛಿಕ"),
    "pay_title": L("Payment", "ಪಾವತಿ"),
    "pay_now": L("Pay", "ಪಾವತಿಸಿ"),
    "pay_success": L("Payment successful", "ಪಾವತಿ ಯಶಸ್ವಿಯಾಗಿದೆ"),
    "pay_processing": L("Processing payment…", "ಪಾವತಿ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ…"),
    "pay_choose": L("Choose a payment method", "ಪಾವತಿ ವಿಧಾನವನ್ನು ಆಯ್ಕೆಮಾಡಿ"),
    "cancel": L("Cancel", "ರದ್ದುಮಾಡಿ"),
    "today": L("Today", "ಇಂದು"),
    "typing": L("typing…", "ಟೈಪ್ ಮಾಡುತ್ತಿದೆ…"),
    "view_doc": L("Open", "ತೆರೆಯಿರಿ"),
    "network_error": L("Connection problem. Tap to retry.", "ಸಂಪರ್ಕ ಸಮಸ್ಯೆ. ಮರುಪ್ರಯತ್ನಿಸಲು ಒತ್ತಿರಿ."),
}


def t(key, lang, **kw):
    s = tr(STR[key], lang)
    return s.format(**kw) if kw else s


def ui_strings(lang):
    return {k: tr(v, lang) for k, v in UI.items()}

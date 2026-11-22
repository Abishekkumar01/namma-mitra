# NAMMA MITRA (ನಮ್ಮ ಮಿತ್ರ): Master Project Document

> **Status (2026-11-22):** v1.1 built and verified. v1.1 replaced the WhatsApp Web clone with a presentation stage (phone at the centre), removed emoji from all bot text, and added real PDF generation.
> - Ten Karnataka services run end to end in Kannada and English.
> - 13 automated test groups pass. They cover 29 panel cases in both languages, 14 free-text phrases, payments, buttons and not-found errors.
> - A headless-browser walkthrough of the real UI finished with zero errors.
>
> **This file is the single source of truth.** A new Claude session should read §12 Handoff first, then §11 Change Log.

---

## 1. What this project is

Namma Mitra is a **fully offline, working simulation** of a WhatsApp citizen-services assistant for the **Government of Karnataka**. It is built for a demonstration to senior officials. It copies the behaviour of **Mana Mitra**, Andhra Pradesh's live WhatsApp governance platform. Mana Mitra is reached by sending "Hi" to 9552300009. It launched in January 2025 with 161 services and has since grown to more than 1,100.

The browser shows a pixel-faithful **WhatsApp Web clone** in dark theme. The demo user chats with the verified "Government of Karnataka" business account exactly as an AP citizen chats with Mana Mitra.

| Mana Mitra (reference) | Namma Mitra (this project) |
|---|---|
| Telugu first. `EN` switches to English, `TE` switches back | **Kannada first.** `EN` switches to English, `KN` switches back |
| AP emblem welcome image | **Government of Karnataka seal** (`GOK logo.jpg`) |
| "Choose Service" opens a WhatsApp Flow panel with a service dropdown | Same panel, same structure and wording, Karnataka services |
| Free text such as "pay electricity bill" asks step by step in chat, with ABORT | Same: free-text intent, question-by-question flow, `ABORT` |
| Live government backends | **Deterministic mock backends**: any well-formed number works |
| No visible internals | **Every function call is logged to SQLite**, and a `#trace` tag sits on every bubble |

**Out of scope:** the real WhatsApp or Meta API, any LLM or API key, real government integrations and real payments.

## 2. What it solves

1. **A convincing demo.** It shows what Karnataka WhatsApp governance would look like before any integration budget is spent.
2. **No dead ends.** Every service path ends in a result card, a receipt, a PDF or a clean "not found, re-enter" prompt. Crashes are caught and answered with a friendly message, and the session resets itself.
3. **Random input is accepted.** The presenter does not know real hall-ticket or account numbers. Records are therefore generated from the input using a SHA-256 seed, so any valid-format value returns a realistic and repeatable record.
4. **One-line bug reports.** The tester says *"trace 83: expected X"*. Then `/logs?trace=83` shows every function, its arguments, its return value or exception, and its timing.
5. **Rebuildable by any Claude account** from this document (§12).

## 3. How Mana Mitra works (reverse-engineered from the user's 14 screenshots in `reference/screenshots/`)

1. **Trigger.** Any text such as "Hi" produces two Meta system notices, then the welcome message.
2. **Welcome message.** It has these parts in order:
   - the state emblem image
   - the greeting and a services summary
   - "💬 Just ask…" followed by two examples
   - "You can also choose a service from the menu below."
   - the tagline "Your Government. Just a Message Away."
   - a quoted hint written in the *other* language, such as `> Type EN for English language`
   - a green **CTA button**, "Choose Service"
3. **Language switch.** `EN` gets a small bubble saying "Language changed successfully.", then the full welcome again in English.
4. **Flow panel.** It is titled "Service Selection" and contains:
   - a banner and the line "Choose from one of the Citizens Services"
   - an outlined dropdown, "Select Citizens Service" with the placeholder "Please Select One Service". It opens a searchable list of icon, title and subtitle rows.
   - service-specific fields that appear under the dropdown. For example, Education shows "Select Hallticket" radios, then the number inputs, then the stream radios.
   - a red "Select an option" message under empty radio groups
   - a Confirm button that stays disabled until the form is valid
5. **Free text.** "i want to pay electricity bill" leads to "Please reply with your service number." followed by "To stop the flow reply with 'ABORT'".
6. **Catalogue ordering.** About nine headline services come first, then the rest alphabetically.

## 4. Services implemented: ten services from Seva One (all run end to end)

Seva One (sevaone.karnataka.gov.in, branded "Namma Seve") is Karnataka's common citizen-services portal, run by the Directorate of EDCS under the Praja Seva Department. It lists 139 departments and over 1,000 single-sign-on services. On 2026-11-22 the user asked that every Namma Mitra service be one that exists on Seva One. I opened the live portal in a browser and read each department's service list, then rebuilt the catalogue so each module maps to named Seva One services. Each `Service` class now carries `dept` (the Seva One department name) and `sevaone` (the exact service names). The department shows in the left rail and in the service picker.

| # | Namma Mitra service | Seva One department | Seva One services covered | Flows and outputs |
|---|---|---|---|---|
| 1 | Revenue Department Certificates (AJSK) | Revenue Department - AJSK | Caste Certificate (SC/ST), Caste Certificate (Cat-A), Income Certificate, Caste and Income Certificate, Residence Certificate | Apply with review and declaration, ₹25 fee, acknowledgement PDF, live 6-stage status, certificate PDF. Track any RD number |
| 2 | Electricity Services (ESCOMs) | Energy Department - BESCOM, MESCOM, HESCOM, GESCOM, CESC | Online Bill Payment, PGRS (Complaint Registration), Meter Complaints, Line breakdown | View and pay bill with Gruha Jyothi logic, bill and receipt PDFs, complaint docket, 4-stage status |
| 3 | Gruhalakshmi Yojana | Women and Child Development Department | Gruhalakshmi Yojana, Track Gruhalakshmi Application Status, Gruhalakshmi EKYC service, Gruhalakshmi sanction order | Application status with DBT history, e-KYC status, sanction order PDF |
| 4 | Yuvanidhi Scheme | Department of Industrial Training and Employment | Application for Yuvanidhi scheme, Yuvanidhi Application Status Check, Monthly Unemployment Self Declaration | Apply with acknowledgement PDF, 4-stage verification, status with payments, monthly self-declaration |
| 5 | KSEAB Marks Card Services | Karnataka School Examination and Assessment Board | Online Marks Card, Issue of Duplicate Marks Card, SSLC / II PUC Marks Card Verification | Online marks card PDF for any register number; duplicate marks card with ₹150 fee, acknowledgement, 4-stage status and duplicate PDF |
| 6 | RTC Print (Pahani) | Survey, Settlement and Land Records (SSLR) | RTC Print / ಪಹಣಿ ಮುದ್ರಣ | RTC with owners, extent, crops, liabilities; RTC PDF |
| 7 | Ration Card Services (Ahara) | Food, Civil Supplies and Consumer Affairs Department | Issue of New Ration Card, Application for Family ID/New NPHH (APL) Card, Ration Card transfer / inclusion | Card status and members with e-KYC, Fair Price Shop; new card application with acknowledgement PDF, 5-stage status and e-ration card PDF |
| 8 | KSRTC Bus Reservation | Karnataka State Road Transport Corporation | Online Reservation for bus booking KSRTC | 3-screen booking, Shakti zero-ticket, payment, e-ticket PDF, cancellation with refund |
| 9 | Transport Department Services | Transport Department | Issue of RC Extract of Vehicles, Driving License Extract, Renewal of Driving License | RC extract PDF, DL extract PDF, DL renewal with ₹400 fee and renewed e-licence PDF |
| 10 | iPGRS Grievance Registration (Janaspandana) | Centre for e-Governance (CeG) | iPGRS Grievance Registrations, Integrated Public Grievance Redressal System/iPGRS | Register with acknowledgement PDF, live 5-stage status, officer remarks |

**Removed in this round** because Seva One does not list them: Muzrai temple seva booking, KCET rank card (KEA), traffic e-challan (Police), Gruha Jyothi, Anna Bhagya and Shakti status. Gruha Jyothi still appears inside the electricity bill because that is how a real BESCOM bill shows it.

Demo inputs with known outcomes are in [data/TEST_DATA.md](data/TEST_DATA.md).

## 5. Architecture

### 5.1 Stack
- **Python 3.10+ standard library only.** It uses `http.server` (threaded), `sqlite3`, `hashlib`, `difflib` and `contextvars`. Nothing needs pip installing, so nothing can break on the demo machine.
- **Vanilla HTML, CSS and JS** with no build step.
- **One SQLite file** at `data/namma_mitra.db`, in WAL mode.
- **Real PDFs** are produced by the Chrome or Edge already installed on the machine, in headless print mode. No PDF library is needed. If no browser is found, the document opens as a printable HTML page instead.

### 5.2 Request flow
```
Browser (static/app.js)
   │  POST /api/message | /api/panel/open | /api/panel/service | /api/panel/submit | /api/payment/*
   ▼
app/server.py  run_route()  ── tracer.begin() ─────────────────────────┐
   │   persist inbound msg → call engine → stamp + persist outbound     │ every @logged call
   ▼                                                                    │ buffered in the trace
app/engine.py  (session state machine, text-mode walker, panel, pay)    │
   │        ├── app/nlu.py        (commands + service intent)           │
   │        ├── app/flowkit.py    (fields, visibility, validation)      │
   │        └── app/services/*.py (one Service subclass per service)    │
   │                 ├── app/data/gen.py   (deterministic records)      │
   │                 ├── app/payments.py   (payment intents)            │
   │                 └── app/docs.py       (PDF-style documents)        │
   ▼                                                                    │
SQLite: sessions, messages, traces, calls, records, payments, docs ◄────┘ tracer.end() flushes calls
```

### 5.3 Key design decisions
1. **One field definition drives two modes.** A service declares its fields once. The panel renders them all as a form, and text mode asks them one at a time. This is the Mana Mitra split, and it means the two modes can never drift apart.
2. **Outcomes.** `Service.submit()` returns one of three results:
   - `Reply(*messages)` closes the panel or ends the flow.
   - `Screen(...)` moves to the next panel screen, as the KSRTC bus list and passenger screens do.
   - `Errors({field: msg})` shows an inline error, or asks the field again in text mode.
3. **Determinism.** `gen.rng(*inputs)` seeds a PRNG from SHA-256 of the inputs. The same input always gives the same record, and different inputs give different records. Things created during the demo are persisted in `records` and progress over time.
4. **Logging by default.** `Service.__init_subclass__` wraps every method of every service with `@logged`. Core functions are decorated explicitly. Aadhaar values are masked as `XXXXXXXX0123` in the logs.
5. **Crash safety.** `run_route` catches any exception. It logs the traceback to the database and to `logs/namma_mitra.log`, resets the session flow, and replies with "Sorry, something went wrong" plus the trace reference and a Main Menu button.
6. **Specimen documents.** Every generated PDF page carries a SPECIMEN watermark and a "not valid for official use" footer.

### 5.4 Database schema (`app/db.py`)
```
sessions(id, lang, state, flow JSON, created_at, updated_at)
messages(id, session_id, dir in|out, payload JSON, trace_id, ts)
traces(id, session_id, kind, input, status ok|error|running, error, output, started_at, duration_ms)
calls(id, trace_id, seq, depth, module, func, args, result, error, duration_ms, ts)
records(kind, ref, session_id, data JSON, created_at, updated_at)   -- nk_app, escom_complaint, ksrtc_booking, grievance, ...
payments(id, session_id, service, purpose, amount, ref, context, status, method, txn_id, created_at, paid_at)
docs(id, session_id, kind, filename, data JSON, created_at)
```

### 5.5 HTTP API (`app/server.py`)
| Route | Body | Returns |
|---|---|---|
| `POST /api/session` | `{session_id}` | history, lang, ui strings |
| `POST /api/message` | `{session_id, text, payload?, label?}` | `{messages}` |
| `POST /api/panel/open` | `{service?, prefill?}` | `{panel}` |
| `POST /api/panel/service` | `{service}` | `{fields}` |
| `POST /api/panel/submit` | `{service, screen, values}` | `{close, inbound, messages}` or `{panel}` or `{errors}` |
| `POST /api/payment/info` / `pay` | `{payment_id, method}` | payment / `{messages}` |
| `GET /doc/<id>` | | printable document |
| `GET /logs`, `/api/traces`, `/api/logs?trace=N` | | trace viewer and JSON |

## 6. How the code works, file by file

### Root
- **`run.py`** (70 lines) is the entry point. It parses `--port`, `--no-browser` and `--reset`, which deletes the database. It picks a free port and starts `app.server.serve`. It also prints the chat, logs and database locations and opens the browser.
- **`README.md`** is a quick start. **`.gitignore`** excludes the database and logs.

### `app/`
- **`config.py`** holds all tunables, each overridable by environment variable: `NM_DB`, `NM_PORT`, `NM_STAGE_SECONDS` (default 30), `DEFAULT_LANG='kn'` and `LOG_TRUNCATE`.
- **`db.py`** keeps one SQLite connection per thread and serialises writes with a lock. It exposes `init`, `execute`, `executemany`, `query` and `one`, plus the generic `rec_get` and `rec_put` that store JSON records keyed by kind and ref.
- **`tracer.py`** provides `begin(session, kind, payload)`, which creates a trace row and sets a contextvar. `@logged` records the seq, depth, module, function, masked arguments, result or exception and milliseconds for every call made while the trace is active. `end()` flushes the calls in one write and also logs to the rotating file. `dump()` handles JSON safely: objects can define `__log__()` and output is truncated.
- **`i18n.py`** defines `L(en, kn)`, a two-language string. `tr` and `loc` resolve them, and `STR` holds every bot string, including the welcome text mirroring Mana Mitra line by line. `UI` holds the browser chrome strings, and `t(key, lang, **fmt)` looks them up.
- **`ui.py`** contains the outgoing message builders: `text`, `image`, `system`, `document`, `button` (quick reply), `cta_panel` (opens the Flow) and `cta_pay`.
- **`flowkit.py`** builds fields with `radio`, `dropdown`, `text`, `textarea`, `number`, `date`, `info` and `opt`. It also provides:
  - `is_visible` and `visible_fields`, which evaluate `show_if` chains
  - `validate` and `validate_all`, which apply transforms (`upper`, `digits`, `upper_nospace`) and check regex patterns, number ranges, relative date windows and minimum length
  - text-mode helpers: `match_option` (accepts a number, a title in either language, or a fuzzy match), `prompt_for` (the chat prompt for one field) and `localize_fields` (adds `min_date` and `max_date`)
- **`nlu.py`** has `command()`, which recognises greetings, `EN`, `KN` and `ABORT` in both scripts. `detect_service()` scores keywords per service using word boundaries for English and substrings for Kannada, and tolerates typos with difflib, so "electricty bil" still routes to Energy.
- **`engine.py`** holds the conversation state machine:
  - `handle_message` routes payload buttons (`menu` and `svc:<key>:<arg>`, which calls `Service.on_button`), commands, an active text flow, a service intent or the fallback.
  - `_start_text_flow` applies `Service.prefill(text)` and sends an intro with an *Open Form* CTA.
  - `_advance` asks the next visible unanswered field, shows info cards, and submits when complete. It also handles Screen and Errors outcomes. It is bounded, so it cannot loop forever.
  - `_text_flow_reply` validates a single answer and re-asks with a warning when it is wrong.
  - `panel_open`, `panel_service` and `panel_submit` drive the panel. Multi-screen state lives in `session.flow` with `mode='panel'`, and a stale screen resets gracefully.
  - `pay` makes payment idempotent: "already paid" is returned on a repeat.
- **`server.py`** routes HTTP requests. `run_route` wraps every POST in a trace, persists inbound and outbound messages with their trace id, attaches language and UI strings, and catches all exceptions. It also serves static files with a path-traversal guard, document pages, the logs API and health.
- **`payments.py`** provides `create`, `get` and `mark_paid`, with a 12-digit UPI-style transaction id.
- **`pdf.py`** finds Chrome or Edge, runs it headless with `--print-to-pdf`, and caches the result in `data/pdf/<doc_id>.pdf`. The seal is embedded as a data URI so the file page renders identically.
- **`docs.py`** stores documents with `create`. `render` produces an A4 HTML page with the bilingual Government of Karnataka header and seal, the department line, a highlight box, key-value and grid tables, notes, a verification code block, a digital-signature block naming the issuing officer, and a footer stating the document was issued through Namma Mitra. `/doc/<id>` is the HTML view with Download PDF and Print buttons. `/doc/<id>.pdf` is the real PDF.

### `app/data/`
- **`karnataka.py`** holds the reference data:
  - 31 districts in English and Kannada, and male and female name lists in both scripts
  - banks, the five ESCOMs with localities, and 25 KSRTC cities with coordinates and a Karnataka flag
  - bus classes with per-km rates and a Shakti-eligibility flag
  - RTO codes, vehicle models, Bengaluru junctions, traffic offences with fines, and the 27 nakshatras
- **`gen.py`** contains:
  - `rng(*parts)`, the deterministic generator
  - `is_missing()`, which treats an all-zero ID as not found
  - `inr()` for Indian digit grouping, such as ₹12,34,567.50
  - `dmy`, `month_year` (with Kannada month names) and `months_back`
  - `person`, `mask_name`, `digits` and `ref_id` (fresh ids for things created in the demo)

### `app/services/`
- **`base.py`** defines `Reply`, `Screen`, `Errors`, `Ctx` (with `t()`, `s()` and `kn`) and `Service`, whose methods are auto-logged. It also provides `menu_buttons`, `btn` (service quick replies), `stage_from_elapsed` (live status progression) and `timeline` (✅ 🔄 ⏳ lines).
- **`__init__.py`** is the registry. To add a service, write a module and append its class to `_CLASSES`.
- **`revenue.py`** runs the apply flow: a review Screen with a declaration, an `RD` + district + date + random number, a ₹25 payment, an acknowledgement PDF, then 6-stage tracking and a localised certificate body for each certificate type.
- **`energy.py`** builds the consumer from Account ID with `consumer()`. It applies the Gruha Jyothi rule (entitlement equals the 12-month average plus 10%, capped at 200 units) and pins three memorable demo accounts. It also produces the bill and receipt PDFs and handles complaints and tracking.
- **`gruhalakshmi.py`** generates the beneficiary from the ration card number: application status with DBT history, e-KYC status, and a sanction order PDF signed by the Deputy Director, WCD.
- **`yuvanidhi.py`** covers apply (acknowledgement PDF, live 4-stage verification), status with payment history, and the monthly self-declaration, which is stored per month so it cannot be submitted twice.
- **`education.py`** is the KSEAB module. `result()` builds a deterministic marks card for any register number (SSLC or II PUC, any year). Online Marks Card returns it with a PDF. Duplicate Marks Card is apply, ₹150 fee, acknowledgement PDF, live 4-stage status, then the duplicate marks card PDF that cites the application number.
- **`bhoomi.py`** chooses crops by region (coastal, malnad, north or south), splits owners, formats acres-guntas, and adds liabilities, the mutation number and the RTC PDF.
- **`ahara.py`** generates the family, card type and per-member e-KYC status, plus the FPS and entitlement view. New ration card application: acknowledgement PDF, 5-stage status with Food Inspector verification, then an e-ration card PDF with a new card number.
- **`ksrtc.py`** works out distance with haversine × 1.28, generates services per route and date, and handles class filtering. It applies Shakti for women on Sarige buses within Karnataka, holds the seats, takes payment or issues a zero-ticket, and produces the e-ticket PDF. Cancellation uses a slab of 10%, 25% or 50%. `prefill` parses "from X to Y" in English and Kannada case endings.
- **`transport.py`** produces the RC extract (chassis, engine, validity) with PDF, the DL extract with PDF and a Renew button, and DL renewal: ₹400 fee, then a renewed e-licence PDF valid five more years. Renewal is recorded so the extract shows the new validity and a second renewal is refused.
- **`grievance.py`** covers 12 departments, IPG ids, an acknowledgement PDF issued by the Centre for e-Governance (CeG), 5 live stages and officer remarks.

### `static/`
- **`index.html`** is the presentation stage, modelled on the Sakala POC the user supplied in `reference pics from sakala poc/`. It has a white government header bar (seal, title in Kannada and English, SIMULATION badge, Kannada/English toggle, Logs, New chat), a left rail listing the ten services and the demo inputs, a phone in the centre showing the WhatsApp chat, and a right rail "Behind the chat" that shows which pipeline steps ran for the last trace. The old WhatsApp Web sidebar with fake personal chats is gone.
- **`style.css`** has the dark green stage, the phone frame, the WhatsApp light theme (green header, beige wallpaper, white and light-green bubbles, blue CTA rows), the Flow sheet that slides up inside the phone, the payment sheet, and a responsive layout where the phone fills the screen below 760 px.
- **`app.js`**:
  - calls the API and applies language and UI strings
  - formats WhatsApp markup (`*bold*`, `_italic_`, `~strike~`, `> quote`)
  - renders every message type and shows replies with a typing delay
  - runs the Flow sheet: the service list with monochrome line icons and search, dropdown list screens, client-side visibility and validation mirroring `flowkit.py`, a screen stack with Back, and server errors shown inline
  - runs the payment sheet with UPI, card and net-banking choices plus processing and success states
  - fills the "Behind the chat" rail from `/api/logs?trace=N` after every action
  - restores history, shows trace tags (hidden with `?trace=0`), and offers New chat
- **`logs.html`** is the trace viewer. It lists traces with auto-refresh, a session filter, an errors-only filter and "go to trace #". Each trace shows its input, error, messages and an indented call tree with expandable arguments and results.
- **`img/gok_logo.jpg`** is the Government of Karnataka seal, copied from the provided `GOK logo.jpg`.

### `tests/test_flows.py`
It drives the real route layer, including tracing, against a temporary database with `NM_STAGE_SECONDS=1`. It covers:
- 29 panel cases in Kannada and English, following every Screen, paying every CTA (and checking that a repeat payment is refused), and pressing every service button
- not-found inline errors, validation errors and live tracking progression
- 14 free-text phrases driven to completion in text mode, plus ABORT and the invalid-reply re-ask
- the welcome and language switch, the fallback, history restore, logged calls, and i18n completeness

## 7. Running, testing, demo checklist
```bash
python run.py --reset          # fresh DB, opens browser at :8000
python -m unittest discover -s tests -v
```
**Before the demo:**
1. Run `python run.py --reset`.
2. Open http://127.0.0.1:8000/?trace=0 to hide the trace tags under the bubbles.
3. Keep [data/TEST_DATA.md](data/TEST_DATA.md) open.
4. For live status progression, apply about 2 minutes before you show tracking.

## 8. Logging contract (one-line bug reports)
- Each user action is one trace. Its id appears as `#N` beside the bubble time.
- `/logs?trace=N` shows the full chain: the input, then `engine.handle_message`, then `nlu.detect_service`, then `services.energy.Energy.bill`, then `payments.create`, and so on. Each step shows its arguments, result or error, and milliseconds.
- Errors are also written to `logs/namma_mitra.log` with the full traceback.
- **Tester vocabulary:** `trace N: <what you expected>`.

## 9. Reference items
- `reference/screenshots/1.png` to `14.png` are the Mana Mitra screenshots supplied by the user.
- `GOK logo.jpg` is the Karnataka seal.
- `reference pics from sakala poc/` holds screenshots of the user's earlier Sakala AI POC. The v1.1 stage layout follows it: government header, phone in the centre, pipeline on the right.
- **Design rules agreed with the user (2026-11-22):**
  - No emoji in bot messages. Mana Mitra uses none in its service replies. The only exception is the single 💬 in the welcome message, which Mana Mitra also has. Status lines use ✔, ▸ and ○.
  - Nothing from Andhra Pradesh appears in the product. Every department, officer, office and helpline is Karnataka's.
  - Required fields: Mana Mitra shows no asterisk. A field is required unless the form marks it "(Optional)", and the Confirm button stays disabled until every required field is valid. The sheet states this rule in one line at the top.
  - Documents name the real issuing authority (Deputy Tahsildar, Karnataka Examinations Authority, Village Administrative Officer, KSRTC, the ESCOM) and carry a verification code, a digital-signature block and a footer stating they were issued through Namma Mitra.
- Mana Mitra English strings that we mirrored:
  - "Welcome to Mana Mitra - Government of Andhra Pradesh's Citizen Services Assistant on WhatsApp!"
  - "💬 Just ask Mana Mitra!"
  - "Your Government. Just a Message Away."
  - "Language changed successfully."
  - "To stop the flow reply with 'ABORT'"
  - "Choose from one of the Citizens Services"
  - "Please Select One Service"
  - "Select an option"
- Research sources:
  - Seva One: sevaone.karnataka.gov.in, read live on 2026-11-22 (home page: 1,086 single-sign-on services; Departments & Services page: 139 departments). The user also pasted page 1 of the logged-in "View all available services" list.
- Mana Mitra scale: Deccan Herald (161 services), Telangana Today and Deccan Chronicle (1,126 services)
  - Seva Sindhu: NIC Informatics
  - Panchamitra, Karnataka's existing WhatsApp Gram Panchayat channel: Siasat and The South First
  - KCET rank card fields: careers360, pw.live and shiksha
  - Nadakacheri: indiafilings and nadakacherikarnataka.in
- Domain facts used:
  - Gruha Jyothi: average units + 10%, capped at 200
  - Gruha Lakshmi: ₹2,000 per month
  - Anna Bhagya: 10 kg rice per member
  - Shakti: free travel in non-premium state buses within Karnataka
  - Yuva Nidhi: ₹3,000 for graduates and ₹1,500 for diploma holders, with a monthly self-declaration
  - Sakala service guarantee
  - Helplines: ESCOM 1912, Janaspandana 1902, Ahara 1967
  - Seva fees and some formats, such as RD, IPG and KS numbers, are indicative.

## 10. Known limitations and next steps
- The assistant uses a keyword matcher, not an LLM. Very unusual phrasing falls back to the menu. Add keywords in a service's `keywords` list.
- Kannada strings were written by Claude. Have a native speaker review `app/i18n.py` and the `L(...)` strings in the services.
- Possible additions:
  - BBMP property tax, Seva Sindhu application status, Panchamitra (Gram Panchayat) services and a hospital OP appointment
  - Each would follow the same Service pattern of about 100 to 250 lines.

## 11. Change Log
| # | Date | Model | Prompt (summary) | Output / files |
|---|---|---|---|---|
| 1 | 2026-11-22 | Fable 5.1 | Initial brief with 14 Mana Mitra screenshots. Plan a Kannada-first Karnataka simulation with SQLite logs. | First architectural plan, which mapped all 51 Mana Mitra services |
| 2 | 2026-11-22 | Opus 5.5 | User: don't map AP services; research Karnataka's own services; 5-10 services that work fully; random numbers must be accepted; robust and professional for senior officials; build it now. | **Built v1.0.** See the list below. |
| 8 | 2026-11-22 | Fable 5.1 | User: keep all ten services, but every one must be a service that exists on Seva One (sevaone.karnataka.gov.in), mapped correctly, with every workflow working to the end. | Opened the live Seva One portal in headless Chrome and read the department service lists (139 departments). Rebuilt the catalogue to ten Seva One services (§4). New modules `gruhalakshmi.py`, `yuvanidhi.py`; rewrote `education.py` (KSEAB online and duplicate marks card), `ahara.py` (new ration card application and e-card), `transport.py` (RC extract, DL extract, DL renewal); removed `temple.py`, `guarantees.py` and KCET. Retitled revenue, energy, bhoomi, ksrtc and grievance with Seva One names; grievance PDF now issued by CeG. `Service` gained `dept` and `sevaone`; the left rail shows the department. Tests rewritten for the new cases (13 groups green), both-language audits clean, 15 document types render on one page, browser walkthrough green. |
| 7 | 2026-11-22 | Opus 5.5 | User: the 'Grievance Redressal - Response sent' bubble could not be opened. Also asked for a loading screen. | The bubble is the WhatsApp form-receipt, not a file. It now has a 'View response' link that opens a read-only sheet of the submitted answers (`engine._summarize`, `showResponse` in `static/app.js`). Grievance registration now also issues a Grievance Acknowledgement PDF from Janaspandana (`services/grievance.py`). Added a government splash loader (seal, bilingual title, progress bar) shown for about 1.6 s on every load (`static/index.html`, `style.css`, `app.js`). Tests green. |
| 6 | 2026-11-22 | Opus 5.5 | User: final pass. Scan every service action, fix any bug, spelling, wording or grammar, and anything that does not match Mana Mitra. | Ran every service action end to end in English and Kannada through the real route layer (29 panel cases, every payment, every quick-reply button, 14 free-text phrases, commands, not-found cases), captured every bot message and every document, and read them all. No crashes or error messages were found. Fixed: unlabelled value lines (applicant, bank, subjects, II PUC combination, bus, passenger, insurer, RTO, status lines); invisible zero-width characters left before 'Members' by an earlier emoji removal; the ration-card member list had lost its per-member e-KYC status, now shown as 'e-KYC done / pending'; '(AAY (Antyodaya))' double brackets; '35 kg' inside Kannada text; 'e.g. e.g.' in chat prompts; 'installments' to Indian English 'instalments'; 'Zero-tickets' to 'Zero tickets'; percentages always two decimals; temple confirmation split into labelled seva date and reporting time, informal blessing removed; tracked grievances now show a subject matching their department; missing full stop on the KSRTC error. Documents: Place now shows the issuing office (taluk, ESCOM headquarters, temple town, boarding city) instead of always Bengaluru; certificate honorific follows gender (Sri / Smt); verification website is the issuing department's own; PDF file names now match the chat bubble. Tests, both audits and the browser walkthrough are green. |
| 5 | 2026-11-22 | Opus 5.5 | User: a valid-looking 12-digit Aadhaar (123456789012) was rejected, so Confirm stayed disabled; the Form validation step in Behind the chat never lit up. | The Aadhaar rule required a first digit of 2-9 (the UIDAI rule) and the error text didn't say so. Relaxed it to any 12 digits in `revenue.py` and `guarantees.py`, with the message "Aadhaar number must be exactly 12 digits". `flowkit.validate_all` is now `@logged`, so the pipeline marks Form validation done on every submit. While a form is open, that step now shows as waiting instead of skipped (`static/app.js`). Tests green. |
| 4 | 2026-11-22 | Fable 5.1 | User: UI looked cartoonish, remove the fake side chats, follow the Sakala POC reference, make it professional for officials, PDF download did not work, no emoji, everything must be Karnataka, keep every service working to the end. | **v1.1.** New `static/index.html`, `style.css`, `app.js` (stage layout with phone, service rail, live pipeline). New `app/pdf.py` (headless Chrome/Edge PDF). Rewrote `app/docs.py` template (official bilingual header, verification code, signature block, single A4 page). Stripped emoji from all services, `i18n.py`, `engine.py`; every value line now has a label. Added a title-case transform for name and place fields in `flowkit.py`. Added "All fields are required unless marked Optional" to the sheet. Replaced the placeholder caste in generated tracking records. Walkthrough and 13 test groups green. |
| 3 | 2026-11-22 | Opus 5.5 | Self-review from browser screenshots | Fixed the page scrolling instead of the message pane (grid `min-height:0`). Fixed the Kannada bold marker in the welcome. Made PDF filenames ASCII. Translated "units" in Kannada bills. Fixed a Kannada case-ending city parser for KSRTC. Pinned demo accounts 1234567890 (zero bill), 9876543210 (payable) and 1111111111 (not registered). |

**What change #2 built:**
- The standard-library server, engine, tracer, i18n, flowkit and NLU
- Ten Karnataka services with deterministic generators
- Payments and PDF documents
- The WhatsApp Web clone UI and the logs viewer
- The end-to-end tests, TEST_DATA.md, README and this document

**How it was verified:** 13/13 test groups pass, and a headless Chrome walkthrough completed with no errors. The walkthrough covered Hi, EN, the panel, KCET, the 3-screen KSRTC booking with payment, Kannada text-mode billing, a document page, the logs page and the mobile layout.

## 12. Handoff: rebuilding or continuing on a fresh Claude account
1. Copy the whole `Namma Mitra` folder. If you only have this document, recreate the files from §6. Each file's purpose and logic are described there, and the folder layout is:
   ```
   run.py  README.md  NAMMA_MITRA_MASTER.md  GOK logo.jpg
   app/{__init__,config,db,tracer,i18n,ui,flowkit,nlu,engine,server,payments,docs}.py
   app/data/{__init__,karnataka,gen}.py
   app/services/{__init__,base,revenue,energy,guarantees,education,bhoomi,ahara,ksrtc,temple,transport,grievance}.py
   static/{index.html,style.css,app.js,logs.html,img/gok_logo.jpg}
   tests/test_flows.py   data/TEST_DATA.md   reference/screenshots/*.png
   ```
2. Open Claude Code in the folder and paste:
   > "Read NAMMA_MITRA_MASTER.md fully. Continue from the last entry in §11. Follow the architecture in §5 and its conventions. Every service is a Service subclass with fields, submit and on_payment/on_button; every user-facing string is L(en, kn); never leave a path without a terminal message. After every change, run `python -m unittest discover -s tests`, then update §6 and §11 and keep data/TEST_DATA.md in sync."
3. **Environment:** Windows 11 and Python 3.10+. Nothing needs installing. Run `python run.py`, then open http://127.0.0.1:8000 for the chat and /logs for traces.
4. **Bug protocol:** the user reports `trace N: expected X`. Open `http://127.0.0.1:8000/api/logs?trace=N`, or query the `calls` table for that trace id. Fix the bug, add a test case, and add a change-log row.
5. **Non-negotiables:**
   - Kannada is the default, and `EN` / `KN` toggle the language.
   - All logging goes through `@logged`.
   - No API keys.
   - Any well-formed input must be accepted.
   - Mana Mitra is the behaviour reference for anything ambiguous.

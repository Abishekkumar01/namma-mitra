# Namma Mitra: Demo Test Data

All ten services are services listed on **Seva One** (sevaone.karnataka.gov.in, "Namma Seve"), with the department names Seva One uses.

**Any well-formed number works.** Records are generated from the input itself, so the same input always gives the same answer. You can type random numbers on stage and they will be accepted. The IDs below are memorable ones with known outcomes.

**Documents:** clicking any PDF bubble opens the real PDF in a new tab. The HTML view at `/doc/<id>` has Download PDF and Print buttons.

**Not-found demo:** any ID whose digits are all zero (`0000000000`, `RD0000000000000`, `YN00000000`) returns a clean "no record found" error and asks again.

**Status that progresses live:** anything you create during the demo moves one stage every 30 seconds: certificate, duplicate marks card, ration card and Yuvanidhi applications, ESCOM complaints and grievances. Apply, wait about 2 minutes, then tap *Track Status*. Change the speed with the `NM_STAGE_SECONDS` environment variable.

| Service (Seva One department) | Input | What you'll see |
|---|---|---|
| Revenue Department Certificates (AJSK) | any name, Aadhaar `2345 6789 0123` | Review, declaration, `RD…` number, ₹25 fee, acknowledgement PDF, track, certificate PDF |
| Revenue, track | `RD0052611224567` | Deterministic status; some numbers show *issued* with the certificate PDF |
| Electricity (BESCOM) | BESCOM, `1234567890` | Shivakumar S, **zero bill under Gruha Jyothi**, bill PDF |
| Electricity (BESCOM) | BESCOM, `9876543210` | Gruha Jyothi exceeded, **₹347.27 payable**, Pay, receipt PDF |
| Electricity, PGRS complaint | any 10-digit account | Docket like `BES2611221234`, trackable |
| Gruhalakshmi (WCD) | RC `150100123456` | Nethra K, application status, ₹2,000 DBT history; e-KYC pending; sanction order PDF |
| Yuvanidhi (Industrial Training and Employment) | apply with any name and Aadhaar | `YN…` number, acknowledgement PDF, 4-stage verification, then monthly self-declaration |
| Yuvanidhi, status | `YN2400123456` | Approved, payment history, *Submit Self-Declaration* button |
| KSEAB Online Marks Card | SSLC, 2026, Reg `2026123456`, any DOB | Marks card and PDF |
| KSEAB Duplicate Marks Card | SSLC, any year, any register number, reason | ₹150 fee, acknowledgement PDF, 4-stage status, duplicate marks card PDF |
| KSEAB, track | `KSEAB2611220001` | Deterministic status |
| RTC Print (SSLR) | Bengaluru Urban, Anekal, Sarjapura, Dommasandra, Sy `45` | Owners, extent, crops, liabilities, RTC PDF |
| Ration card (Food and Civil Supplies) | RC `150100123456` | AAY card, members with e-KYC status, Fair Price Shop |
| New ration card | any head of family, Aadhaar, mobile, address | `FCS…` number, acknowledgement PDF, 5-stage status, e-ration card PDF |
| Ration card, track | `FCS2611220001` | Deterministic status |
| KSRTC Reservation | Bengaluru to Mysuru, any date, 2 pax, *Any class* | Bus list, passenger form, pay, e-ticket PDF |
| KSRTC Shakti | pick a **Karnataka Sarige** bus, gender *Female* | Primary passenger fare is ₹0 |
| KSRTC cancel | `KS2611220123` or any PNR you booked | Refund calculation, *Confirm Cancellation* |
| Transport, RC Extract | `KA01AB1234` | Hyundai Creta SX, insurance and PUC validity, RC extract PDF |
| Transport, DL Extract | `KA0120190001234`, DOB 15-06-1990 | Active licence, DL extract PDF, *Renew this Licence* button |
| Transport, DL Renewal | any `KA` + 13 digits, DOB, mobile | ₹400 fee, renewed e-licence PDF valid 5 more years |
| iPGRS Grievance (CeG) | any department, district, subject, description of 15+ characters | `IPG…` ID, acknowledgement PDF, live 5-stage status |
| Grievance, track | `IPG261122345` | Deterministic status |

## Free-text phrases that route straight into a service

- `I want to pay my electricity bill` / `ವಿದ್ಯುತ್ ಬಿಲ್ ಪಾವತಿಸಬೇಕು`
- `I need an income certificate` / `ನನಗೆ ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ ಬೇಕು`
- `ಬೆಂಗಳೂರಿನಿಂದ ಮೈಸೂರಿಗೆ ಬಸ್ ಟಿಕೆಟ್` fills From and To automatically
- `gruha lakshmi status`, `yuvanidhi status`, `sslc marks card`, `rtc pahani`, `ration card status`, `renew my driving licence`, `complaint about garbage`

## Commands

| Command | Effect |
|---|---|
| `Hi`, `Hello`, `ನಮಸ್ಕಾರ`, `menu` | Welcome message and menu |
| Kannada / English buttons in the header | Same as typing `KN` / `EN` |
| `EN` / `KN` | Switch language. The welcome message is re-sent in the new language |
| `ABORT` | Cancel the current question-by-question flow |
| `SKIP` | Skip an optional question in text mode |

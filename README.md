# Namma Mitra (ನಮ್ಮ ಮಿತ್ರ)

A working simulation of a WhatsApp citizen-services assistant for the Government of Karnataka, modelled on Andhra Pradesh's **Mana Mitra**. Kannada comes first and you type `EN` or `KN` to switch. Ten real Karnataka services run end to end, and every function call is logged to SQLite.

## Run it

```bash
python run.py            # opens http://127.0.0.1:8000
python run.py --reset    # fresh database before a demo
```

You need Python 3.10 or newer. There is nothing to pip install and no API keys.

- **Chat:** http://127.0.0.1:8000
- **Trace logs:** http://127.0.0.1:8000/logs
- **Tests:** `python -m unittest discover -s tests -v`
- **Demo inputs:** [data/TEST_DATA.md](data/TEST_DATA.md)
- **Full documentation and handoff:** [NAMMA_MITRA_MASTER.md](NAMMA_MITRA_MASTER.md)

## Reporting a bug

Every bot message shows a small `#N` trace tag. Report issues as **"trace N: what you expected"**.

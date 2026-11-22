"""Central configuration. Every tunable lives here; override with environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NM_DB", BASE_DIR / "data" / "namma_mitra.db"))
STATIC_DIR = BASE_DIR / "static"
LOG_DIR = BASE_DIR / "logs"

HOST = os.environ.get("NM_HOST", "127.0.0.1")
PORT = int(os.environ.get("NM_PORT", "8000"))

DEFAULT_LANG = "kn"          # Kannada first, exactly like Mana Mitra is Telugu first
APP_NAME = "Namma Mitra"
APP_VERSION = "1.0.0"

# Seconds per status stage for things you create during the demo (applications,
# complaints, grievances). Apply, wait ~2 minutes, track -> you see real progress.
STAGE_SECONDS = int(os.environ.get("NM_STAGE_SECONDS", "30"))

# Max characters of args/results stored per logged call.
LOG_TRUNCATE = 4000

"""Real PDF generation with the locally installed Chrome or Edge (headless print-to-PDF).

Kannada text, fonts and layout come out exactly as the HTML page renders. PDFs are cached in
data/pdf/<doc_id>.pdf. If no browser is found, the caller falls back to the HTML view.
"""
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from . import config
from .tracer import logged

PDF_DIR = config.DB_PATH.parent / "pdf"
_locks = {}
_locks_guard = threading.Lock()

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def browser_path():
    env = os.environ.get("NM_BROWSER")
    if env and Path(env).exists():
        return env
    for p in CANDIDATES:
        if Path(p).exists():
            return p
    for name in ("chrome", "msedge", "chromium", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _lock(doc_id):
    with _locks_guard:
        return _locks.setdefault(doc_id, threading.Lock())


@logged
def render_pdf(doc_id, html):
    """Return the path of the PDF for this document, generating it on first use."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    out = PDF_DIR / f"{doc_id}.pdf"
    if out.exists() and out.stat().st_size > 0:
        return out
    exe = browser_path()
    if not exe:
        return None
    with _lock(doc_id):
        if out.exists() and out.stat().st_size > 0:
            return out
        tmpdir = Path(tempfile.mkdtemp(prefix="nm_doc_"))
        src = tmpdir / "doc.html"
        src.write_text(html, encoding="utf-8")
        cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--disable-extensions", "--no-pdf-header-footer", f"--user-data-dir={tmpdir / 'profile'}",
               f"--print-to-pdf={out}", src.as_uri()]
        try:
            subprocess.run(cmd, capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired:
            return None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return out if out.exists() and out.stat().st_size > 0 else None

"""Namma Mitra - start the simulation.

    python run.py                 # start on http://127.0.0.1:8000 and open the browser
    python run.py --port 8080     # different port
    python run.py --no-browser    # don't open a browser tab
    python run.py --reset         # wipe chats, logs and records (fresh demo)

No third-party packages. Python 3.10+.
"""
import argparse
import socket
import sys
import threading
import webbrowser

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import config  # noqa: E402


def free_port(host, start):
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) != 0:
                return port
    return start


def main():
    ap = argparse.ArgumentParser(description="Namma Mitra simulation server")
    ap.add_argument("--host", default=config.HOST)
    ap.add_argument("--port", type=int, default=config.PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--reset", action="store_true", help="delete the database for a fresh demo")
    args = ap.parse_args()

    if args.reset and config.DB_PATH.exists():
        for suffix in ("", "-wal", "-shm"):
            p = config.DB_PATH.with_name(config.DB_PATH.name + suffix)
            if p.exists():
                p.unlink()
        print("Database reset.")

    from app.server import serve
    port = free_port(args.host, args.port)
    httpd = serve(args.host, port)
    url = f"http://{args.host}:{port}"
    print("=" * 60)
    print(f"  Namma Mitra v{config.APP_VERSION} - Government of Karnataka (simulation)")
    print(f"  Chat      : {url}")
    print(f"  Logs      : {url}/logs")
    print(f"  Database  : {config.DB_PATH}")
    print("  Stop      : Ctrl+C")
    print("=" * 60)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

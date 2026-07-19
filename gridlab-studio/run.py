"""Convenience launcher: `python run.py` starts the studio on :8000."""
from __future__ import annotations

import argparse
import webbrowser
from threading import Timer

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the gridlab studio web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes")
    parser.add_argument("--no-open", action="store_true", help="don't open a browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"
    if not args.no_open:
        Timer(1.2, lambda: webbrowser.open(url)).start()

    print(f"\n  gridlab studio  ->  {url}\n  (Ctrl+C to stop)\n")
    uvicorn.run("backend.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

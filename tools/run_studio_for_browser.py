"""Run the source Studio on a test port for browser-level verification."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "gridlab" / "src"), str(ROOT / "gridlab-studio")]
os.environ["GRIDLAB_STUDIO_DATABASE"] = str(
    ROOT / "gridlab-studio" / ".studio" / "playwright.sqlite3"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()

"""Export the authoritative FastAPI schema consumed by the typed Studio."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app import app


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "gridlab-studio" / "frontend-typed" / "openapi.json"


def main() -> None:
    OUTPUT.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Exported {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

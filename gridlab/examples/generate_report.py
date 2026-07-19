"""Generate a standalone HTML report you can open directly in a browser.

    python examples/generate_report.py
    # -> writes examples/report.html
"""
from __future__ import annotations

import os

from gridlab import run_backtest


def main() -> None:
    spec = {
        "symbol": "ETHUSDT",
        "market_type": "spot",
        "initial_cash": 10_000.0,
        "grid": {"levels": 16, "lower": 80.0, "upper": 120.0,
                 "spacing": "geometric", "direction": "long"},
        "sizing": {"mode": "fixed_quote", "value": 80.0},
        "fees": {"maker": 0.0002, "taker": 0.0005},
        "fill": {"mode": "conservative"},
        "data": {"kind": "synthetic", "n": 2500, "start_price": 100.0,
                 "regime": "range", "seed": 21},
    }

    out = run_backtest(spec, with_report=True)
    path = os.path.join(os.path.dirname(__file__), "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out["html_report"])
    print(f"Wrote {path} ({len(out['html_report']):,} bytes)")
    print("Open it directly in your browser — no build step required.")


if __name__ == "__main__":
    main()

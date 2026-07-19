"""Quickstart: run a single grid backtest and print the headline metrics.

    python examples/quickstart.py
"""
from __future__ import annotations

from gridlab import run_backtest


def main() -> None:
    spec = {
        "symbol": "BTCUSDT",
        "market_type": "spot",
        "initial_cash": 10_000.0,
        # A long-only geometric grid between 80 and 120.
        "grid": {
            "levels": 14,
            "lower": 80.0,
            "upper": 120.0,
            "spacing": "geometric",
            "direction": "long",
        },
        "sizing": {"mode": "fixed_quote", "value": 100.0},
        "fees": {"maker": 0.0002, "taker": 0.0005},
        "slippage": {"spread_frac": 0.0, "impact_frac": 0.0005},
        "fill": {"mode": "conservative"},     # next-bar eligibility (no lookahead)
        "data": {"kind": "synthetic", "n": 2000, "start_price": 100.0,
                 "regime": "range", "seed": 7},
    }

    out = run_backtest(spec)
    m = out["metrics"]
    bnh = out["benchmarks"]["buy_and_hold"]

    print(f"Symbol            : {out['symbol']}  ({out['bars']} bars)")
    print(f"Total return      : {m['total_return'] * 100:7.2f}%")
    print(f"Buy & hold return : {bnh['total_return'] * 100:7.2f}%")
    print(f"Final equity      : {m['final_equity']:,.2f}")
    print(f"Closed trades     : {int(m['n_trades'])}")
    print(f"Win rate          : {(m['win_rate'] or 0) * 100:7.2f}%")
    print(f"Profit factor     : {m['profit_factor']}")
    print(f"Max drawdown      : {m['max_drawdown'] * 100:7.2f}%")
    print(f"Sharpe (ann.)     : {m['sharpe']:7.2f}")
    print(f"Deflated Sharpe   : {(m['deflated_sharpe'] or 0) * 100:7.2f}%")
    print(f"Fees paid         : {m['fees_paid']:,.2f}")
    print(f"Rejections        : {out['rejections']}")


if __name__ == "__main__":
    main()

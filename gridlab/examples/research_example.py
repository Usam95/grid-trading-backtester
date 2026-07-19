"""Research example: parameter grid search + walk-forward + Monte Carlo.

    python examples/research_example.py
"""
from __future__ import annotations

from gridlab.api.facade import run_backtest
from gridlab.research.grid_search import ParamSpace, grid_search
from gridlab.research.monte_carlo import monte_carlo_trades
from gridlab.research.walk_forward import walk_forward

BASE = {
    "symbol": "BTCUSDT",
    "initial_cash": 10_000.0,
    "grid": {"levels": 12, "lower": 85.0, "upper": 115.0, "direction": "long",
             "spacing": "geometric"},
    "sizing": {"mode": "fixed_quote", "value": 80.0},
    "fees": {"maker": 0.0002, "taker": 0.0005},
    "fill": {"mode": "conservative"},
    "data": {"kind": "synthetic", "n": 2000, "regime": "range", "seed": 3},
}


def main() -> None:
    print("== Grid search (ranked by deflated Sharpe) ==")
    space = ParamSpace({
        "grid.levels": [8, 12, 20],
        "sizing.value": [50.0, 100.0],
        "grid.spacing": ["arithmetic", "geometric"],
    })
    ranked = grid_search(BASE, space, objective="deflated_sharpe", top_k=5)
    for r in ranked:
        m = r["metrics"]
        print(f"  {r['params']}  ret={m['total_return']*100:6.2f}%  "
              f"DSR={(r['score'] or 0)*100:6.2f}%  trades={int(m['n_trades'])}")

    print("\n== Walk-forward (out-of-sample) ==")
    wf = walk_forward(BASE, ParamSpace({"grid.levels": [8, 12, 20]}),
                      n_splits=4, objective="total_return")
    for f in wf["folds"]:
        print(f"  fold {f['fold']}: best={f['best_params']} "
              f"IS={f['is_score']:.4f} OOS_ret={f['oos_total_return']*100:6.2f}%")
    print(f"  summary: {wf['summary']}")

    print("\n== Monte Carlo (trade bootstrap) ==")
    out = run_backtest(BASE)
    pnls = [t["pnl"] for t in out["trades"]]
    mc = monte_carlo_trades(pnls, 10_000.0, n_sims=2000)
    print(f"  prob_loss={mc['prob_loss']*100:.1f}%  "
          f"median_return={mc['final_return']['p50']*100:.2f}%  "
          f"p5_return={mc['final_return']['p5']*100:.2f}%  "
          f"worst_dd={mc['worst_max_drawdown']*100:.2f}%")


if __name__ == "__main__":
    main()

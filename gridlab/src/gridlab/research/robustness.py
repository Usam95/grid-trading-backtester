"""Deployment robustness scorecard.

A single backtest number is the easiest thing in trading to fool yourself with.
Before risking real money on a grid configuration you want one honest, combined
read on *how likely the edge is to survive contact with the live market*. This
module fuses the three independent robustness lenses gridlab already provides
into a single 0–100 **deployment trust score** with a transparent breakdown:

* **Out-of-sample (walk-forward)** — does the edge hold on data the optimiser
  never saw? Measured by the fraction of OOS folds that stay profitable.
* **Overfitting (deflated Sharpe)** — is the headline Sharpe real after
  discounting for the number of configurations tried?
* **Path risk (Monte-Carlo)** — across plausible re-orderings of the same
  trades, how often do we end up losing, and how deep can the drawdown get?

The score is deliberately conservative: it is the capital-weighted blend of the
three components, and any single catastrophic signal (e.g. >50% chance of loss
in Monte-Carlo) caps the overall grade. This is decision-support, not a
guarantee — a high score means "worth forward-testing", never "guaranteed".
"""
from __future__ import annotations

from typing import Optional

from gridlab.api.facade import run_backtest
from gridlab.research.grid_search import ParamSpace
from gridlab.research.monte_carlo import monte_carlo
from gridlab.research.walk_forward import walk_forward


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _grade(score: float) -> str:
    if score >= 75:
        return "Deploy-ready (forward-test first)"
    if score >= 60:
        return "Promising — needs forward testing"
    if score >= 40:
        return "Fragile — tighten before risking capital"
    return "Do not deploy"


def robustness_report(
    base_spec: dict, space: dict | ParamSpace | None = None, *,
    n_splits: int = 4, mc_method: str = "trades", mc_sims: int = 2000,
    objective: str = "deflated_sharpe", seed: int = 0,
) -> dict:
    """Run the three robustness checks and fuse them into a trust score.

    ``space`` is the parameter grid to walk-forward optimise over; if ``None``
    or empty, the walk-forward component is skipped and its weight is
    redistributed (useful for scoring a single fixed configuration).
    """
    components: dict[str, dict] = {}

    # --- 1) Out-of-sample (walk-forward) ---------------------------------
    oos_component: Optional[float] = None
    if space:
        ps = space if isinstance(space, ParamSpace) else ParamSpace(
            {k: list(v) for k, v in space.items()})
        try:
            wf = walk_forward(base_spec, ps, n_splits=n_splits, objective=objective)
            summary = wf["summary"]
            n_folds = max(1, summary.get("n_folds", 0) or 0)
            pos = summary.get("positive_oos_folds", 0) or 0
            frac_pos = pos / n_folds
            mean_ret = summary.get("mean_oos_return")
            oos_component = _clip01(frac_pos)
            components["out_of_sample"] = {
                "score": round(100 * oos_component, 1),
                "positive_oos_folds": pos,
                "n_folds": n_folds,
                "mean_oos_return": mean_ret,
                "detail": wf["folds"],
            }
        except ValueError as exc:  # not enough data for the requested splits
            components["out_of_sample"] = {"score": None, "error": str(exc)}

    # --- 2) Overfitting (deflated Sharpe) + base run ---------------------
    n_trials = 1
    if space:
        ps = space if isinstance(space, ParamSpace) else ParamSpace(
            {k: list(v) for k, v in space.items()})
        n_trials = max(1, ps.size())
    base_run = run_backtest({**base_spec, "n_trials": n_trials}, include_trades=True)
    m = base_run["metrics"]
    dsr = m.get("deflated_sharpe")
    overfit_component = _clip01(dsr) if dsr is not None else 0.5
    components["overfitting"] = {
        "score": round(100 * overfit_component, 1),
        "deflated_sharpe": dsr,
        "sharpe": m.get("sharpe"),
        "n_trials": n_trials,
    }

    # --- 3) Path risk (Monte-Carlo) -------------------------------------
    initial = float(base_spec.get("initial_cash", 10_000.0))
    mc = monte_carlo(
        {"equity_curve": base_run["series"]["equity"] if "series" in base_run
         else base_run.get("equity_curve", []),
         "trades": base_run.get("trades", [])},
        initial, method=mc_method, n_sims=mc_sims, seed=seed)
    prob_loss = mc.get("prob_loss")
    worst_dd = mc.get("worst_max_drawdown")
    if prob_loss is None:
        path_component = 0.3
    else:
        # Reward low loss probability and shallow worst-case drawdown.
        dd_pen = _clip01(1.0 + (worst_dd or 0.0) / 0.5)  # -50% dd -> 0
        path_component = _clip01((1.0 - prob_loss) * 0.7 + dd_pen * 0.3)
    components["path_risk"] = {
        "score": round(100 * path_component, 1),
        "prob_loss": prob_loss,
        "worst_max_drawdown": worst_dd,
        "mean_final_return": mc.get("mean_final_return"),
        "method": mc.get("method"),
    }

    # --- Fuse ------------------------------------------------------------
    weights: list[tuple[float, float]] = []  # (component, weight)
    if oos_component is not None:
        weights.append((oos_component, 0.45))
    weights.append((overfit_component, 0.30))
    weights.append((path_component, 0.25))
    total_w = sum(w for _, w in weights)
    blended = sum(c * w for c, w in weights) / total_w if total_w else 0.0
    score = 100 * blended

    # Hard caps: a single catastrophic signal limits the overall grade.
    if prob_loss is not None and prob_loss > 0.5:
        score = min(score, 35.0)
    if base_run["metrics"].get("liquidated"):
        score = min(score, 20.0)

    return {
        "trust_score": round(score, 1),
        "grade": _grade(score),
        "components": components,
        "weights": {"out_of_sample": 0.45 if oos_component is not None else 0.0,
                    "overfitting": 0.30, "path_risk": 0.25},
        "base_metrics": {
            "total_return": m.get("total_return"),
            "return_over_buy_hold": m.get("return_over_buy_hold"),
            "max_drawdown": m.get("max_drawdown"),
            "sharpe": m.get("sharpe"),
            "profit_factor": m.get("profit_factor"),
            "n_trades": m.get("n_trades"),
        },
        "notes": [
            "Trust score blends out-of-sample, overfitting and path-risk lenses.",
            "A high score means 'worth forward-testing', never a profit guarantee.",
            "Always paper-trade a config before committing real capital.",
        ],
    }

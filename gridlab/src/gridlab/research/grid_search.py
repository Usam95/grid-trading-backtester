"""Parameter search with built-in overfitting awareness.

`grid_search` runs the cartesian product of a parameter space and ranks results
by an objective metric. Crucially, it passes the number of configurations tried
through as `n_trials`, so the **deflated Sharpe** of each result discounts for
the multiple-testing/selection bias — the single most important guard against
the "great backtest, dead live" failure mode documented in the research summary.
"""
from __future__ import annotations

import copy
import itertools
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Iterable

from gridlab.api.facade import BacktestSpec, run_backtest


@dataclass(slots=True)
class ParamSpace:
    """Maps dotted spec paths to candidate values, e.g. {'grid.levels': [8, 12]}."""
    space: dict[str, list[Any]] = field(default_factory=dict)

    def combinations(self) -> Iterable[dict[str, Any]]:
        if not self.space:
            yield {}
            return
        keys = list(self.space.keys())
        for combo in itertools.product(*(self.space[k] for k in keys)):
            yield dict(zip(keys, combo))

    def size(self) -> int:
        n = 1
        for v in self.space.values():
            n *= max(1, len(v))
        return n


def _set_path(d: dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = d
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value


def _spec_to_dict(spec: BacktestSpec | dict) -> dict:
    if isinstance(spec, BacktestSpec):
        from dataclasses import asdict
        return asdict(spec)
    return copy.deepcopy(spec)


def _run_one(args: tuple[dict, dict, str]) -> dict:
    """Module-level worker (picklable) for one parameter combination."""
    spec_dict, params, objective = args
    out = run_backtest(spec_dict, include_trades=False)
    return {
        "params": params,
        "score": out["metrics"].get(objective),
        "metrics": out["metrics"],
    }


def grid_search(base_spec: BacktestSpec | dict, space: ParamSpace | dict,
                *, objective: str = "deflated_sharpe", maximize: bool = True,
                top_k: int | None = None, workers: int = 1) -> list[dict]:
    """Run every parameter combination and rank by `objective`.

    Returns a list of {params, metrics, score} sorted best-first. The objective
    defaults to the deflated Sharpe so the ranking already penalises overfit
    configurations.

    ``workers`` > 1 fans the (independent, CPU-bound) runs out across processes
    via a ProcessPoolExecutor — large sweeps over many symbols/parameters scale
    near-linearly with cores. ``workers`` = 1 keeps the deterministic serial
    path (used by the studio) untouched.
    """
    if isinstance(space, dict):
        space = ParamSpace(space)
    n_trials = max(1, space.size())
    base = _spec_to_dict(base_spec)

    jobs: list[tuple[dict, dict, str]] = []
    for params in space.combinations():
        spec_dict = copy.deepcopy(base)
        for key, val in params.items():
            _set_path(spec_dict, key, val)
        spec_dict["n_trials"] = n_trials
        jobs.append((spec_dict, params, objective))

    if workers and workers > 1 and len(jobs) > 1:
        chunk = max(1, len(jobs) // (workers * 4))
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(_run_one, jobs, chunksize=chunk))
    else:
        results = [_run_one(j) for j in jobs]

    def sort_key(r: dict) -> float:
        s = r["score"]
        if s is None:
            return float("-inf") if maximize else float("inf")
        return s

    results.sort(key=sort_key, reverse=maximize)
    return results[:top_k] if top_k else results

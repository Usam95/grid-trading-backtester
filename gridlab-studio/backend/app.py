"""FastAPI application — REST surface + static SPA host for gridlab-studio.

Run with ``python run.py`` or ``uvicorn backend.app:app``. All compute routes
are thin wrappers around :mod:`backend.service`; engine ``ValueError`` (bad
config) is surfaced as a clean HTTP 400 so the UI can show a friendly message.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend import __version__
from backend import service
from backend.presets import (
    ECONOMICS_METRICS,
    GUIDE,
    HEADLINE_METRICS,
    METRIC_META,
    PRESET_INDEX,
    PRESETS,
    VENUES,
)
from backend.schemas import (
    GridPreviewBody,
    GridSearchBody,
    MonteCarloBody,
    RobustnessBody,
    RunBacktestBody,
    WalkForwardBody,
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="gridlab studio",
    version=__version__,
    description="A beautiful, informative studio for the gridlab grid-trading backtester.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _guard(fn, *args, **kwargs):
    """Run a service call, translating engine errors into HTTP 400."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"{type(exc).__name__}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "gridlab-studio", "version": __version__}


@app.get("/api/meta")
def meta() -> dict:
    """Everything the UI needs to render the configurator and explainers."""
    return {
        "presets": PRESETS,
        "default_spec": PRESET_INDEX["spot-neutral-range"]["spec"],
        "metric_meta": METRIC_META,
        "headline_metrics": HEADLINE_METRICS,
        "guide": GUIDE,
        "enums": {
            "market_type": ["spot"],
            "spacing": ["arithmetic", "geometric", "atr"],
            "direction": ["neutral", "long"],
            "sizing_mode": [
                "fixed_quote",
                "fixed_base",
                "percent_equity",
                "martingale",
            ],
            "fill_mode": ["conservative", "optimistic"],
            "regime": ["range", "trend", "random"],
            "filter_kind": ["none", "trend", "regime", "rsi"],
            "data_kind": ["binance", "synthetic"],
            "interval": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "bootstrap_side": ["LONG"],
        },
        "venues": VENUES,
        "economics_metrics": ECONOMICS_METRICS,
        "objectives": [
            "deflated_sharpe",
            "sharpe",
            "total_return",
            "calmar",
            "profit_factor",
            "sortino",
        ],
    }


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


@app.post("/api/backtest")
def backtest(body: RunBacktestBody) -> dict:
    spec = body.spec.to_spec()
    return _guard(
        service.run_backtest,
        spec,
        with_report=body.options.with_report,
        include_trades=body.options.include_trades,
    )


@app.post("/api/grid-preview")
def grid_preview(body: GridPreviewBody) -> dict:
    spec = body.spec.to_spec()
    return _guard(service.compute_grid_levels, spec)


@app.post("/api/report")
def report(body: RunBacktestBody) -> StreamingResponse:
    spec = body.spec.to_spec()
    result = _guard(service.run_backtest, spec, with_report=True, include_trades=True)
    html = result.get("html_report", "<h1>No report</h1>")
    buf = io.BytesIO(html.encode("utf-8"))
    fname = f"gridlab-report-{body.spec.symbol}.html"
    return StreamingResponse(
        buf,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


@app.post("/api/research/grid-search")
def research_grid_search(body: GridSearchBody) -> dict:
    base = body.base.to_spec()
    return _guard(
        service.run_grid_search,
        base,
        body.space,
        objective=body.objective,
        maximize=body.maximize,
        top_k=body.top_k,
    )


@app.post("/api/research/walk-forward")
def research_walk_forward(body: WalkForwardBody) -> dict:
    base = body.base.to_spec()
    return _guard(
        service.run_walk_forward,
        base,
        body.space,
        n_splits=body.n_splits,
        objective=body.objective,
    )


@app.post("/api/research/monte-carlo")
def research_monte_carlo(body: MonteCarloBody) -> dict:
    base = body.base.to_spec()
    return _guard(
        service.run_monte_carlo,
        base,
        method=body.method,
        n_sims=body.n_sims,
        seed=body.seed,
    )


@app.post("/api/research/robustness")
def research_robustness(body: RobustnessBody) -> dict:
    base = body.base.to_spec()
    return _guard(
        service.run_robustness,
        base,
        body.space,
        n_splits=body.n_splits,
        mc_sims=body.mc_sims,
    )


# ---------------------------------------------------------------------------
# Static SPA (mounted last so /api/* always wins)
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

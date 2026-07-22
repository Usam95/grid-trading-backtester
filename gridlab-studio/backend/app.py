"""FastAPI application — REST surface + static SPA host for gridlab-studio.

Run with ``python run.py`` or ``uvicorn backend.app:app``. All compute routes
are thin wrappers around :mod:`backend.service`; engine ``ValueError`` (bad
config) is surfaced as a clean HTTP 400 so the UI can show a friendly message.
"""

from __future__ import annotations

import io
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
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
    BinanceDatasetPreview,
    BinanceDatasetRequest,
    DatasetManifest,
    GridPreviewBody,
    GridSearchBody,
    ImportDatasetBody,
    ManifestedBacktestBody,
    MonteCarloBody,
    ProductionDatasetProvenance,
    RobustnessBody,
    RunBacktestBody,
    StudioBacktestRun,
    StudioConfiguration,
    StudioPrimaryResult,
    WalkForwardBody,
)
from backend.studio_datasets import StudioDatasetRepository, studio_dataset_repository
from backend.studio_runs import SqliteStudioRunStore, studio_run_store

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
TYPED_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend-typed-dist"

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


@app.get("/api/studio/configuration", response_model=StudioConfiguration)
def studio_configuration() -> StudioConfiguration:
    """Return the canonical defaults for Ticket 02's migrated static Spot slice."""
    return StudioConfiguration(
        default_spec=PRESET_INDEX["spot-neutral-range"]["spec"],
        spacing=["geometric", "arithmetic"],
        data_regimes=["range", "trend", "random"],
    )


@app.post("/api/studio/datasets/binance/preview", response_model=BinanceDatasetPreview)
def preview_binance_dataset(
    body: BinanceDatasetRequest,
    repository: StudioDatasetRepository = Depends(studio_dataset_repository),
) -> BinanceDatasetPreview:
    """Resolve official source identities and sizes before archive download."""
    preview = _guard(
        repository.preview,
        service.ArchiveRequest(body.symbol, body.interval, body.start, body.end),
    )
    return BinanceDatasetPreview.model_validate(asdict(preview))


@app.post(
    "/api/studio/datasets/binance/import",
    response_model=DatasetManifest,
    status_code=201,
)
def import_binance_dataset(
    body: ImportDatasetBody,
    repository: StudioDatasetRepository = Depends(studio_dataset_repository),
) -> DatasetManifest:
    """Download and admit only checksum-verified, continuous production history."""
    manifest = _guard(repository.acquire, body.preview_id)
    manifest.pop("manifest_path", None)
    return DatasetManifest.model_validate(manifest)


@app.get("/api/studio/datasets/{dataset_id}", response_model=DatasetManifest)
def get_studio_dataset(
    dataset_id: str,
    repository: StudioDatasetRepository = Depends(studio_dataset_repository),
) -> DatasetManifest:
    return DatasetManifest.model_validate(_guard(repository.manifest, dataset_id))


@app.post("/api/studio/backtests", response_model=StudioBacktestRun, status_code=201)
def create_studio_backtest(
    body: RunBacktestBody,
    store: SqliteStudioRunStore = Depends(studio_run_store),
) -> StudioBacktestRun:
    """Execute and durably record the typed Studio's migrated Research slice."""
    specification = body.spec.to_spec()
    result = _guard(
        service.run_backtest,
        specification,
        with_report=body.options.with_report,
        include_trades=body.options.include_trades,
    )
    metrics = result["metrics"]
    run = StudioBacktestRun(
        id=str(uuid4()),
        status="completed",
        created_at=datetime.now(timezone.utc),
        specification=specification,
        primary_result=StudioPrimaryResult(
            net_return=metrics["total_return"],
            final_equity=result["final_equity"],
            max_drawdown=metrics["max_drawdown"],
            completed_trades=result["n_closed_trades"],
            fees_paid=result["fees_paid"],
            verdict=result["verdict"]["label"],
        ),
        result=result,
    )
    store.save(run)
    return run


@app.post(
    "/api/studio/backtests/manifested",
    response_model=StudioBacktestRun,
    status_code=201,
)
def create_manifested_studio_backtest(
    body: ManifestedBacktestBody,
    repository: StudioDatasetRepository = Depends(studio_dataset_repository),
    store: SqliteStudioRunStore = Depends(studio_run_store),
) -> StudioBacktestRun:
    """Replay one admitted production dataset without any network dependency."""
    specification = body.spec.to_spec()
    specification["data"] = {
        "kind": "manifested_parquet",
        "dataset_id": body.dataset_id,
    }
    manifest_path = _guard(repository.manifest_path, body.dataset_id)
    fingerprinted = _guard(
        service.fingerprint_manifested_backtest, specification, manifest_path
    )
    result = _guard(
        service.run_manifested_backtest,
        specification,
        manifest_path,
        include_trades=body.options.include_trades,
    )
    manifest = _guard(repository.manifest, body.dataset_id)
    metrics = result["metrics"]
    requested = manifest["requested_range"]
    normalization = manifest["normalization"]
    run = StudioBacktestRun(
        id=str(uuid4()),
        status="completed",
        created_at=datetime.now(timezone.utc),
        specification=specification,
        primary_result=StudioPrimaryResult(
            net_return=metrics["total_return"],
            final_equity=result["final_equity"],
            max_drawdown=metrics["max_drawdown"],
            completed_trades=result["n_closed_trades"],
            fees_paid=result["fees_paid"],
            verdict=result["verdict"]["label"],
        ),
        result=result,
        provenance=ProductionDatasetProvenance(
            dataset_id=manifest["dataset_id"],
            manifest_identity=manifest["manifest_sha256"],
            source_provider=manifest["source_provider"],
            history_environment="production",
            testnet_history_used=False,
            symbol=manifest["symbol"],
            interval=manifest["interval"],
            requested_start=requested["start_inclusive"],
            requested_end=requested["end_exclusive"],
            retrieved_at=manifest["retrieved_at"],
            source_urls=[source["url"] for source in manifest["sources"]],
            normalized_sha256=normalization["sha256"],
            candle_sequence_sha256=normalization["candle_sequence_sha256"],
            backtest_fingerprint=fingerprinted["backtest_fingerprint"],
        ),
    )
    store.save(run)
    return run


@app.get("/api/studio/backtests/{run_id}", response_model=StudioBacktestRun)
def get_studio_backtest(
    run_id: str,
    store: SqliteStudioRunStore = Depends(studio_run_store),
) -> StudioBacktestRun:
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Studio backtest run not found")
    return run


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
# Static SPAs (mounted last so /api/* always wins)
# ---------------------------------------------------------------------------

if TYPED_FRONTEND_DIR.exists():
    app.mount(
        "/studio",
        StaticFiles(directory=str(TYPED_FRONTEND_DIR), html=True),
        name="typed-frontend",
    )

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

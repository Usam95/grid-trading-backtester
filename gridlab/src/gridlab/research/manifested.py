"""Offline deterministic research over admitted manifested market evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from gridlab.api.facade import BacktestSpec, run_backtest_with_data
from gridlab.data.binance_archive import load_manifested_candles
from gridlab.data.source import InMemoryDataSource


def run_manifested_backtest(spec: dict | BacktestSpec, manifest_path: Path) -> dict:
    """Run and fingerprint a backtest solely from verified local Parquet evidence."""
    if isinstance(spec, dict):
        spec = BacktestSpec.from_dict(spec)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if spec.symbol != manifest["symbol"]:
        raise ValueError(
            f"backtest symbol {spec.symbol} does not match dataset {manifest['symbol']}"
        )
    data = InMemoryDataSource(
        symbol=spec.symbol,
        _candles=load_manifested_candles(manifest_path),
    )
    result = run_backtest_with_data(spec, data, with_report=False, include_trades=True)
    fingerprint_input = {
        "contract": "gridlab.manifested-backtest-fingerprint.v1",
        "dataset_id": manifest["dataset_id"],
        "candle_sequence_sha256": manifest["normalization"]["candle_sequence_sha256"],
        "specification": asdict(spec),
        "result": result,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_input,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return {
        "dataset_id": manifest["dataset_id"],
        "candle_sequence_sha256": manifest["normalization"]["candle_sequence_sha256"],
        "backtest_fingerprint": fingerprint,
        "result": result,
    }

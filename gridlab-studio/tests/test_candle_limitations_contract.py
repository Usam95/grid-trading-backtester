from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.studio_runs import SqliteStudioRunStore, studio_run_store


SMALL_SPEC = {
    "symbol": "TESTUSDT",
    "market_type": "spot",
    "initial_cash": 10_000.0,
    "grid": {
        "levels": 8,
        "lower": 90.0,
        "upper": 110.0,
        "spacing": "geometric",
        "direction": "neutral",
    },
    "sizing": {"mode": "fixed_quote", "value": 50.0},
    "data": {
        "kind": "synthetic",
        "n": 100,
        "start_price": 100.0,
        "seed": 7,
        "sigma": 0.01,
        "regime": "range",
    },
}


def test_studio_backtest_contract_labels_candle_limitations(tmp_path: Path) -> None:
    database = tmp_path / "studio.sqlite3"

    def override_store():
        with SqliteStudioRunStore(database) as store:
            yield store

    app.dependency_overrides[studio_run_store] = override_store
    try:
        with TestClient(app) as client:
            response = client.post("/api/studio/backtests", json={"spec": SMALL_SPEC})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["result"]["simulation"]["mode"] == "candle"
    assert payload["result"]["simulation"]["venue_execution_proof"] is False
    assert payload["result"]["simulation"]["canonical_core"] is False
    assert payload["result"]["simulation"]["limitations"]

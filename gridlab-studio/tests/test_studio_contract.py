from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
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


@contextmanager
def _client(database: Path) -> Iterator[TestClient]:
    def override_store() -> Iterator[SqliteStudioRunStore]:
        with SqliteStudioRunStore(database) as store:
            yield store

    app.dependency_overrides[studio_run_store] = override_store
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_typed_studio_executes_and_retrieves_a_durable_backtest(tmp_path: Path) -> None:
    with _client(tmp_path / "studio.sqlite3") as client:
        response = client.post(
            "/api/studio/backtests",
            json={"spec": SMALL_SPEC, "options": {"include_trades": True}},
        )

        assert response.status_code == 201, response.text
        run = response.json()
        assert run["status"] == "completed"
        assert run["specification"] == {**SMALL_SPEC, "n_trials": 1}
        assert run["result"]["symbol"] == "TESTUSDT"
        assert (
            run["result"]["metrics"]["total_return"]
            == run["primary_result"]["net_return"]
        )
        assert run["primary_result"]["final_equity"] > 0
        assert run["primary_result"]["completed_trades"] >= 0

        retrieved = client.get(f"/api/studio/backtests/{run['id']}")
        assert retrieved.status_code == 200
        assert retrieved.json() == run


def test_typed_studio_run_survives_store_reopen(tmp_path: Path) -> None:
    database = tmp_path / "studio.sqlite3"
    with _client(database) as first_client:
        created = first_client.post(
            "/api/studio/backtests", json={"spec": SMALL_SPEC}
        ).json()

    with _client(database) as second_client:
        retrieved = second_client.get(f"/api/studio/backtests/{created['id']}")

        assert retrieved.status_code == 200
        assert retrieved.json()["specification"] == {**SMALL_SPEC, "n_trials": 1}
        assert retrieved.json()["result"] == created["result"]


def test_typed_studio_contract_is_explicit_in_openapi() -> None:
    schema = app.openapi()
    create = schema["paths"]["/api/studio/backtests"]["post"]
    read = schema["paths"]["/api/studio/backtests/{run_id}"]["get"]

    assert create["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StudioBacktestRun"
    }
    assert read["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StudioBacktestRun"
    }
    primary = schema["components"]["schemas"]["StudioPrimaryResult"]["properties"]
    assert set(primary) == {
        "net_return",
        "final_equity",
        "max_drawdown",
        "completed_trades",
        "fees_paid",
        "verdict",
    }


def test_typed_studio_configuration_exposes_only_the_migrated_static_spot_path() -> None:
    with TestClient(app) as client:
        response = client.get("/api/studio/configuration")

    assert response.status_code == 200
    configuration = response.json()
    assert configuration["spacing"] == ["geometric", "arithmetic"]
    assert configuration["data_regimes"] == ["range", "trend", "random"]
    assert configuration["default_spec"]["market_type"] == "spot"
    assert configuration["default_spec"]["grid"]["direction"] == "neutral"
    assert configuration["default_spec"]["sizing"]["mode"] == "fixed_quote"


def test_built_typed_studio_and_legacy_frontend_are_both_served() -> None:
    with TestClient(app) as client:
        typed = client.get("/studio/")
        legacy = client.get("/")

    assert typed.status_code == 200
    assert "Gridlab Operator Studio" in typed.text
    assert legacy.status_code == 200
    assert "gridlab studio" in legacy.text.lower()

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


def test_typed_studio_configuration_exposes_only_the_migrated_static_spot_path() -> (
    None
):
    with TestClient(app) as client:
        response = client.get("/api/studio/configuration")

    assert response.status_code == 200
    configuration = response.json()
    assert configuration["spacing"] == ["geometric", "arithmetic"]
    assert configuration["data_regimes"] == ["range", "trend", "random"]
    assert configuration["default_spec"]["market_type"] == "spot"
    assert configuration["default_spec"]["grid"]["direction"] == "neutral"
    assert configuration["default_spec"]["sizing"]["mode"] == "fixed_quote"


def test_canonical_adaptive_contract_is_exact_typed_and_deterministic() -> None:
    request = {
        "symbol": "BTCEUR",
        "decision_time": "2025-01-02T00:00:00Z",
        "trend": "0.0000",
        "volatility": "0.0100",
        "reference_price": "100.00",
        "complete": True,
        "evidence_quality": "ADMITTED",
    }
    with TestClient(app) as client:
        first = client.post("/api/studio/canonical-adaptive", json=request)
        second = client.post("/api/studio/canonical-adaptive", json=request)
        incomplete = client.post(
            "/api/studio/canonical-adaptive",
            json={
                **request,
                "complete": False,
                "evidence_quality": "INCOMPLETE",
            },
        )

    assert first.status_code == 200, first.text
    assert second.json() == first.json()
    payload = first.json()
    assert payload["configuration"]["configuration_id"].startswith("sha256:")
    assert payload["observation"]["observation_id"].startswith("sha256:")
    assert payload["observation"]["event_id"].startswith("sha256:")
    assert payload["decision"]["adaptation_state"] == "RANGE_NORMAL"
    assert payload["derived_plan"]["epoch_id"].startswith("sha256:")
    assert payload["activation"]["lifecycle"] == "BOOTSTRAPPING"
    assert payload["activation"]["ladder_placement_allowed"] is False
    assert payload["activation"]["activation_pending"] is False
    assert payload["activation"]["automatically_armed"] is False
    assert payload["activation"]["replay_fingerprint"].startswith("sha256:")
    assert payload["derived_plan"]["lower"]["value"] == "96.000000"
    assert payload["derived_plan"]["upper"]["value"] == "104.000000"
    assert (
        payload["derived_plan"]["maximum_planned_inventory"]["kind"] == "base_quantity"
    )
    assert (
        payload["derived_plan"]["bootstrap_obligation"]["gross_base_required"]["kind"]
        == "base_quantity"
    )
    assert payload["configuration"]["operator_inputs"]["maker_fee"] == {
        "kind": "fee_rate",
        "value": "0.0010",
    }
    assert payload["legacy_comparison"]["bounded_bars"] == 120
    assert payload["legacy_comparison"]["legacy_adaptive"] is True
    assert payload["legacy_comparison"]["legacy_spacing"] == "geometric"
    assert payload["legacy_comparison"]["effective_atr_multiplier"] == "2.0"
    assert payload["legacy_comparison"]["cancelled_orders"] > 0
    assert len(payload["legacy_comparison"]["semantic_differences"]) == 5
    assert incomplete.status_code == 200
    assert incomplete.json()["decision"]["adaptation_state"] == "UNCERTAIN"
    assert incomplete.json()["decision"]["intent"] == "FROZEN"
    assert incomplete.json()["activation"]["lifecycle"] == "REJECTED"
    assert incomplete.json()["activation"]["activation_pending"] is False
    assert incomplete.json()["activation"]["automatically_armed"] is False
    assert incomplete.json()["derived_plan"] is None


def test_safety_posture_contract_is_typed_separate_and_deterministic() -> None:
    with TestClient(app) as client:
        first = client.get("/api/studio/safety-posture")
        second = client.get("/api/studio/safety-posture")

    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    payload = first.json()
    assert payload["safety"]["posture"] == "REDUCE_ONLY"
    assert payload["lifecycle"] == {
        "grid_lifecycle": "RANGE_EXHAUSTED",
        "adaptation_state": "TREND_DOWN",
        "epoch_transition_state": "IDLE",
        "runtime_lifecycle": "OPERATING",
        "reconciliation_state": "RECONCILED",
    }
    assert len(payload["freshness"]) == 5
    assert payload["venue"]["condition"] == "DELISTING"
    assert payload["venue"]["wind_down_deadline"] == "2025-01-09T12:00:00Z"
    assert payload["safety"]["placement_allowed"] is False
    assert payload["safety"]["downward_bound_shift_allowed"] is False
    assert payload["fingerprint"].startswith("sha256:")
    schema = app.openapi()
    assert schema["paths"]["/api/studio/safety-posture"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SafetyPosturePresentation"
    }


def test_initial_epoch_contract_supports_arithmetic_and_blocks_boundaries() -> None:
    request = {
        "symbol": "BTCEUR",
        "decision_time": "2025-01-02T00:00:00Z",
        "trend": "0.0000",
        "volatility": "0.0100",
        "reference_price": "100.00",
        "activation_price": "100.00",
        "complete": True,
        "evidence_quality": "ADMITTED",
        "spacing": "ARITHMETIC",
    }
    with TestClient(app) as client:
        arithmetic = client.post("/api/studio/canonical-adaptive", json=request)
        boundary = client.post(
            "/api/studio/canonical-adaptive",
            json={**request, "activation_price": "96.00"},
        )

    assert arithmetic.status_code == 200, arithmetic.text
    payload = arithmetic.json()
    assert payload["configuration"]["spacing"] == "ARITHMETIC"
    assert [rung["role"] for rung in payload["derived_plan"]["quantized_rungs"]] == [
        "BUY",
        "BUY",
        "INACTIVE",
        "SELL",
        "SELL",
    ]
    assert boundary.status_code == 200
    assert boundary.json()["activation"]["lifecycle"] == "REJECTED"
    assert boundary.json()["derived_plan"] is None


def test_complete_bootstrap_evidence_activates_without_changing_epoch_identity() -> (
    None
):
    request = {
        "symbol": "BTCEUR",
        "decision_time": "2025-01-02T00:00:00Z",
        "trend": "0.0000",
        "volatility": "0.0100",
        "reference_price": "100.00",
        "activation_price": "100.00",
        "complete": True,
        "evidence_quality": "ADMITTED",
    }
    with TestClient(app) as client:
        pending = client.post("/api/studio/canonical-adaptive", json=request).json()
        required = pending["derived_plan"]["bootstrap_obligation"]["net_base_required"][
            "value"
        ]
        active = client.post(
            "/api/studio/canonical-adaptive",
            json={
                **request,
                "bootstrap_complete": True,
                "bootstrap_confirmed_base": required,
                "bootstrap_evidence_id": "sha256:" + "b" * 64,
            },
        )

    assert active.status_code == 200, active.text
    payload = active.json()
    assert payload["activation"]["lifecycle"] == "ACTIVE"
    assert payload["activation"]["ladder_placement_allowed"] is True
    assert payload["derived_plan"]["epoch_id"] == pending["derived_plan"]["epoch_id"]


def test_canonical_adaptive_boundary_rejects_ambiguous_numeric_payloads() -> None:
    with TestClient(app) as client:
        binary_float = client.post(
            "/api/studio/canonical-adaptive",
            json={
                "decision_time": "2025-01-02T00:00:00Z",
                "trend": 0.01,
            },
        )
        exponent = client.post(
            "/api/studio/canonical-adaptive",
            json={
                "decision_time": "2025-01-02T00:00:00Z",
                "trend": "1e-2",
            },
        )
        future = client.post(
            "/api/studio/canonical-adaptive",
            json={
                "decision_time": "2025-01-01T00:00:00Z",
                "trend": "0.0000",
            },
        )
        wrong_quote = client.post(
            "/api/studio/canonical-adaptive",
            json={
                "symbol": "BTCUSDT",
                "decision_time": "2025-01-01T00:00:00Z",
            },
        )

    assert binary_float.status_code == 422
    assert exponent.status_code == 422
    assert future.status_code == 200
    assert wrong_quote.status_code == 422


def test_built_typed_studio_and_legacy_frontend_are_both_served() -> None:
    with TestClient(app) as client:
        typed = client.get("/studio/")
        legacy = client.get("/")

    assert typed.status_code == 200
    assert "Gridlab Operator Studio" in typed.text
    assert legacy.status_code == 200
    assert "gridlab studio" in legacy.text.lower()

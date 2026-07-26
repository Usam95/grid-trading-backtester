from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app, resume_local_research_jobs
from backend.studio_runs import SqliteStudioRunStore, studio_run_store


SPEC = {
    "symbol": "TESTUSDT",
    "market_type": "spot",
    "initial_cash": 10_000,
    "grid": {"levels": 8, "lower": 90, "upper": 110, "spacing": "geometric", "direction": "neutral"},
    "sizing": {"mode": "fixed_quote", "value": 50},
    "data": {"kind": "synthetic", "n": 100, "start_price": 100, "seed": 7, "sigma": 0.01, "regime": "range"},
}


def test_research_job_is_durable_identity_bound_and_resumable(tmp_path: Path) -> None:
    def override_store():
        with SqliteStudioRunStore(tmp_path / "studio.sqlite3") as store:
            yield store

    app.dependency_overrides[studio_run_store] = override_store
    try:
        with TestClient(app) as client:
            created = client.post("/api/studio/research/jobs", json={
                "spec": SPEC, "dataset_identity": "dataset:fixture-v1", "venue_rules_identity": "venue:v1",
                "fee_identity": "fees:v1", "execution_model_identity": "candle:v1", "schema_identity": "schema:v1", "seed": 7,
            })
            assert created.status_code == 202, created.text
            job = created.json()
            assert job["status"] in {"QUEUED", "RUNNING", "COMPLETED", "RESUMABLE"}
            assert job["identity"]["dataset"] == "dataset:fixture-v1"
            assert job["identity"]["seed"] == "seed:7"
            for _ in range(100):
                job = client.get(f"/api/studio/research/jobs/{job['id']}").json()
                if job["status"] in {"COMPLETED", "RESUMABLE", "FAILED"}:
                    break
                time.sleep(0.02)
            assert job["status"] == "COMPLETED", (job["status"], job.get("error"), job.get("checkpoint"))
            assert job["result"]["net_return"] == job["result"]["net_return"]
            assert {gate["name"] for gate in job["result"]["gates"]} == {"correctness", "accounting", "risk", "data", "replay"}
            assert job["result"]["visualization"]["overlays"][-1]["kind"] == "safety"
            assert "net-long base exposure" in job["result"]["inventory_basis"]
            assert client.get("/api/studio/research/jobs").json()[0]["id"] == job["id"]
        with SqliteStudioRunStore(tmp_path / "studio.sqlite3") as store:
            reopened = store.get_job(job["id"])
        assert reopened is not None
        assert reopened.status == "COMPLETED"
        assert reopened.result is not None
    finally:
        app.dependency_overrides.clear()


def test_research_job_cancellation_is_explicit(tmp_path: Path) -> None:
    def override_store():
        with SqliteStudioRunStore(tmp_path / "studio.sqlite3") as store:
            yield store

    app.dependency_overrides[studio_run_store] = override_store
    try:
        with TestClient(app) as client:
            created = client.post("/api/studio/research/jobs", json={
                "spec": SPEC, "dataset_identity": "dataset:cancel", "venue_rules_identity": "venue:v1",
                "fee_identity": "fees:v1", "execution_model_identity": "candle:v1", "schema_identity": "schema:v1", "seed": 8,
            }).json()
            cancelled = client.post(f"/api/studio/research/jobs/{created['id']}/cancel")
            assert cancelled.status_code == 200
            assert cancelled.json()["status"] in {"CANCELLED", "COMPLETED"}
    finally:
        app.dependency_overrides.clear()


def test_service_restart_resumes_unfinished_job(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "studio.sqlite3"
    monkeypatch.setenv("GRIDLAB_STUDIO_DATABASE", str(database))
    request = {
        "spec": SPEC, "dataset_identity": "dataset:restart", "venue_rules_identity": "venue:v1",
        "fee_identity": "fees:v1", "execution_model_identity": "candle:v1", "schema_identity": "schema:v1", "seed": 9,
    }
    with TestClient(app) as response:
        created_payload = response.post("/api/studio/research/jobs", json=request).json()
    with SqliteStudioRunStore(database) as store:
        job = store.get_job(created_payload["id"])
        assert job is not None
        store.save_job(job.model_copy(update={"status": "RESUMABLE", "phase": "FAILED"}))
    resume_local_research_jobs()
    for _ in range(100):
        with SqliteStudioRunStore(database) as store:
            resumed = store.get_job(created_payload["id"])
        if resumed and resumed.status == "COMPLETED":
            break
        time.sleep(0.02)
    assert resumed is not None
    assert resumed.status == "COMPLETED"

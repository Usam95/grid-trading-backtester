from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import _execute_research_job, app, resume_local_research_jobs
from backend import service
from backend.research_jobs import identity_for
from backend.schemas import ResearchJob, ResearchJobRequest
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


def test_admitted_research_job_replays_the_selected_local_archive(
    tmp_path: Path, monkeypatch
) -> None:
    dataset_id = "a" * 64
    start = "2020-01-03T08:00:00Z"
    end = "2020-02-01T00:00:00Z"
    request = ResearchJobRequest.model_validate({
        "spec": {**SPEC, "symbol": "BTCEUR"},
        "dataset_identity": dataset_id,
        "dataset_start": start,
        "dataset_end": end,
        "venue_rules_identity": "venue:v1",
        "fee_identity": "fees:v1",
        "execution_model_identity": "candle:v1",
        "schema_identity": "schema:v1",
        "seed": 7,
    })
    snapshot = {
        "manifest_path": str(tmp_path / "snapshot.json"),
        "symbol": "BTCEUR",
        "manifest_sha256": "b" * 64,
    }
    calls: list[tuple[dict, Path]] = []

    class FakeArchive:
        def create_snapshot(self, selected_id, selected_start, selected_end):
            assert selected_id == dataset_id
            assert selected_start.isoformat() == "2020-01-03T08:00:00+00:00"
            assert selected_end.isoformat() == "2020-02-01T00:00:00+00:00"
            return snapshot

    def fake_archive_backtest(specification, manifest_path, *, include_trades):
        calls.append((specification, manifest_path))
        assert include_trades is True
        return {
            "metrics": {"total_return": 0.12, "max_drawdown": -0.03},
            "final_equity": 112.0,
            "fees_paid": 1.25,
            "n_closed_trades": 2,
            "series": {"price": [10.0, 11.0], "equity": [100.0, 112.0], "drawdown": [0.0, -0.03]},
            "trades": [{"order_id": "archive-fill", "price": "10.50", "quantity": "1", "pnl": "2"}],
        }

    monkeypatch.setattr("backend.app.studio_production_panel_repository", lambda: FakeArchive())
    monkeypatch.setattr(service, "run_archive_snapshot_backtest", fake_archive_backtest)
    database = tmp_path / "studio.sqlite3"
    job = ResearchJob(
        id="job-local-archive",
        status="QUEUED",
        created_at=request.dataset_start,
        updated_at=request.dataset_start,
        request=request,
        identity=identity_for(request),
        progress=0,
        phase="QUEUED",
    )
    with SqliteStudioRunStore(database) as store:
        store.save_job(job)
    _execute_research_job(job.id, request, database)
    with SqliteStudioRunStore(database) as store:
        completed = store.get_job(job.id)
    assert completed is not None
    assert completed.status == "COMPLETED"
    assert completed.result is not None
    assert completed.result.data_source == "verified local production archive"
    assert completed.result.dataset_symbol == "BTCEUR"
    assert completed.result.manifest_identity == "b" * 64
    assert len(calls) == 1
    assert calls[0][0]["data"] == {
        "kind": "manifested_parquet",
        "dataset_id": dataset_id,
        "start": "2020-01-03T08:00:00+00:00",
        "end": "2020-02-01T00:00:00+00:00",
    }

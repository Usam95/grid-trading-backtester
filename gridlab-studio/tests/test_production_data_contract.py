from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.studio_datasets import StudioDatasetRepository, studio_dataset_repository
from backend.studio_runs import SqliteStudioRunStore, studio_run_store


class FixtureArchiveClient:
    def __init__(self, archive: bytes) -> None:
        self.archive = archive

    def checksum(self, _url: str) -> str:
        return hashlib.sha256(self.archive).hexdigest()

    def content_length(self, _url: str) -> int:
        return len(self.archive)

    def download(self, _url: str) -> bytes:
        return self.archive


def _archive() -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for minute in range(1440):
        opened = int((start + timedelta(minutes=minute)).timestamp() * 1_000_000)
        writer.writerow(
            [
                opened,
                "93000.00000000",
                "93100.00000000",
                "92900.00000000",
                "93050.00000000",
                "1.25000000",
                opened + 59_999_999,
                "116312.50000000",
                42,
                "0.75000000",
                "69787.50000000",
                0,
            ]
        )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("BTCUSDT-1m-2025-01-01.csv", output.getvalue())
    return buffer.getvalue()


@contextmanager
def _client(root: Path) -> Iterator[TestClient]:
    repository = StudioDatasetRepository(
        root / "datasets", FixtureArchiveClient(_archive())
    )

    def override_runs() -> Iterator[SqliteStudioRunStore]:
        with SqliteStudioRunStore(root / "studio.sqlite3") as store:
            yield store

    app.dependency_overrides[studio_dataset_repository] = lambda: repository
    app.dependency_overrides[studio_run_store] = override_runs
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_typed_api_previews_imports_and_replays_production_history(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        preview_response = client.post(
            "/api/studio/datasets/binance/preview",
            json={
                "symbol": "BTCUSDT",
                "interval": "1m",
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-02T00:00:00Z",
            },
        )
        assert preview_response.status_code == 200, preview_response.text
        preview = preview_response.json()
        assert preview["market"] == "spot-production-archive"
        assert preview["estimated_bytes"] > 0
        assert len(preview["sources"][0]["expected_sha256"]) == 64

        import_response = client.post(
            "/api/studio/datasets/binance/import",
            json={"preview_id": preview["preview_id"]},
        )
        assert import_response.status_code == 201, import_response.text
        manifest = import_response.json()
        assert manifest["history_environment"] == "production"
        assert manifest["quality"]["gaps"] == 0
        assert manifest["normalization"]["format"] == "parquet"
        assert len(manifest["manifest_sha256"]) == 64

        backtest_response = client.post(
            "/api/studio/backtests/manifested",
            json={
                "dataset_id": manifest["dataset_id"],
                "spec": {
                    "symbol": "BTCUSDT",
                    "market_type": "spot",
                    "initial_cash": 10000,
                    "grid": {
                        "levels": 8,
                        "lower": 92500,
                        "upper": 93500,
                        "spacing": "geometric",
                        "direction": "neutral",
                    },
                    "sizing": {"mode": "fixed_quote", "value": 50},
                    "fees": {"maker": 0.001, "taker": 0.001},
                },
            },
        )
        assert backtest_response.status_code == 201, backtest_response.text
        run = backtest_response.json()
        assert run["result"]["bars"] == 1440
        assert run["provenance"]["dataset_id"] == manifest["dataset_id"]
        assert run["provenance"]["manifest_identity"] == manifest["manifest_sha256"]
        assert run["provenance"]["history_environment"] == "production"
        assert run["provenance"]["testnet_history_used"] is False
        assert len(run["provenance"]["backtest_fingerprint"]) == 64
        assert run["result"]["data_source"] == {
            "kind": "manifested_parquet",
            "is_real": True,
            "label": "Manifested Binance production history",
            "description": "Checksum-verified production candles loaded from typed Parquet.",
            "venue": None,
            "exchange_rules_on": False,
        }

        assert client.get(f"/api/studio/backtests/{run['id']}").json() == run


def test_manifested_backtest_rejects_non_static_neutral_spot_specs(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        preview = client.post(
            "/api/studio/datasets/binance/preview",
            json={
                "symbol": "BTCUSDT",
                "interval": "1m",
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-02T00:00:00Z",
            },
        ).json()
        manifest = client.post(
            "/api/studio/datasets/binance/import",
            json={"preview_id": preview["preview_id"]},
        ).json()

        invalid_specs = [
            {"symbol": "BTCUSDT", "market_type": "futures"},
            {
                "symbol": "BTCUSDT",
                "market_type": "spot",
                "grid": {"direction": "short"},
            },
            {
                "symbol": "BTCUSDT",
                "market_type": "spot",
                "grid": {"direction": "neutral", "adaptive": True},
            },
        ]
        for spec in invalid_specs:
            response = client.post(
                "/api/studio/backtests/manifested",
                json={"dataset_id": manifest["dataset_id"], "spec": spec},
            )
            assert response.status_code == 422, response.text
            assert "static neutral Spot" in response.text


def test_production_data_contract_is_explicit_in_openapi() -> None:
    schema = app.openapi()

    assert schema["paths"]["/api/studio/datasets/binance/preview"]["post"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BinanceDatasetPreview"
    }
    assert schema["paths"]["/api/studio/datasets/binance/import"]["post"]["responses"][
        "201"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DatasetManifest"
    }
    provenance = schema["components"]["schemas"]["ProductionDatasetProvenance"]
    assert "backtest_fingerprint" in provenance["properties"]
    assert "testnet_history_used" in provenance["properties"]

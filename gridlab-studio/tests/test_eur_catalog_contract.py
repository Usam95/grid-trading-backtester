from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.studio_catalogs import StudioCatalogRepository, studio_catalog_repository
from backend.studio_datasets import StudioDatasetRepository, studio_dataset_repository
from backend.studio_runs import SqliteStudioRunStore, studio_run_store
from gridlab.data.binance_catalog import ArchiveCoverage, CatalogAdmissionError


NOW = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)


def _symbol(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "TRADING",
        "baseAsset": symbol.removesuffix("EUR"),
        "quoteAsset": "EUR",
        "isSpotTradingAllowed": True,
        "orderTypes": ["LIMIT", "LIMIT_MAKER", "MARKET"],
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
            {"filterType": "LOT_SIZE", "stepSize": "0.0001"},
            {"filterType": "NOTIONAL", "minNotional": "5"},
        ],
    }


class FixtureCatalogClient:
    production_url = "https://data-api.binance.vision/api/v3/exchangeInfo"
    testnet_url = "https://testnet.binance.vision/api/v3/exchangeInfo"
    archive_root = "https://data.binance.vision/data"
    market_root = "https://data-api.binance.vision/api/v3"

    def _exchange_info(self) -> dict[str, object]:
        return {
            "timezone": "UTC",
            "serverTime": int(NOW.timestamp() * 1000),
            "symbols": [_symbol("BTCEUR"), _symbol("ETHEUR")],
        }

    def production_exchange_info(self) -> dict[str, object]:
        return self._exchange_info()

    def testnet_exchange_info(self) -> dict[str, object]:
        return self._exchange_info()

    def daily_klines(self, _symbol: str) -> list[list[object]]:
        rows = []
        for index in range(30):
            opened = NOW - timedelta(days=31 - index)
            rows.append(
                [
                    int(opened.timestamp() * 1000),
                    "100",
                    "102",
                    "99",
                    str(100 + index),
                    "10",
                    int(
                        (
                            opened + timedelta(days=1) - timedelta(milliseconds=1)
                        ).timestamp()
                        * 1000
                    ),
                    str(1_000_000 + index),
                    100 + index,
                    "5",
                    "500000",
                    "0",
                ]
            )
        return rows

    def ticker(self, symbol: str) -> dict[str, object]:
        return {
            "symbol": symbol,
            "bidPrice": "100",
            "askPrice": "100.10",
            "count": 1234,
        }

    def archive_coverage(self, symbol: str, _as_of: date) -> ArchiveCoverage:
        return ArchiveCoverage(
            first_date=date(2022, 1, 1),
            last_date=date(2026, 7, 21),
            intervals=("1m", "5m", "1h"),
            known_gap_dates=(date(2025, 1, 2),) if symbol == "BTCEUR" else (),
            evidence_urls=(f"https://data.binance.vision/{symbol}",),
        )


class PreviewArchiveClient:
    @staticmethod
    def _archive(url: str) -> bytes:
        match = re.search(r"(ETHEUR)-1m-(\d{4}-\d{2}-\d{2})\.zip", url)
        if match is None:
            raise AssertionError(f"unexpected fixture URL {url}")
        symbol, day_text = match.groups()
        day = datetime.fromisoformat(day_text).replace(tzinfo=timezone.utc)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        for minute in range(1440):
            opened = int((day + timedelta(minutes=minute)).timestamp() * 1_000_000)
            writer.writerow(
                [
                    opened,
                    "3300.00000000",
                    "3310.00000000",
                    "3290.00000000",
                    "3305.00000000",
                    "10.00000000",
                    opened + 59_999_999,
                    "33050.00000000",
                    50,
                    "5.00000000",
                    "16525.00000000",
                    0,
                ]
            )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            entry = zipfile.ZipInfo(f"{symbol}-1m-{day_text}.csv")
            entry.date_time = (2025, 1, 1, 0, 0, 0)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, output.getvalue())
        return buffer.getvalue()

    def checksum(self, url: str) -> str:
        return hashlib.sha256(self._archive(url.removesuffix(".CHECKSUM"))).hexdigest()

    def content_length(self, url: str) -> int:
        return len(self._archive(url))

    def download(self, url: str) -> bytes:
        return self._archive(url)


@contextmanager
def _client(root: Path) -> Iterator[TestClient]:
    catalogs = StudioCatalogRepository(
        root / "catalogs",
        FixtureCatalogClient(),
        clock=lambda: NOW,
    )
    datasets = StudioDatasetRepository(root / "datasets", PreviewArchiveClient())

    def override_runs() -> Iterator[SqliteStudioRunStore]:
        with SqliteStudioRunStore(root / "studio.sqlite3") as store:
            yield store

    app.dependency_overrides[studio_catalog_repository] = lambda: catalogs
    app.dependency_overrides[studio_dataset_repository] = lambda: datasets
    app.dependency_overrides[studio_run_store] = override_runs
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_typed_api_discovers_catalog_and_previews_a_selected_eur_range(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        response = client.get("/api/studio/catalogs/binance/eur?refresh=true")
        assert response.status_code == 200, response.text
        catalog = response.json()
        assert catalog["quote_asset"] == "EUR"
        assert [item["symbol"] for item in catalog["symbols"]] == ["BTCEUR", "ETHEUR"]
        assert catalog["symbols"][0]["coverage"]["first_date"] == "2022-01-01"
        assert catalog["symbols"][0]["liquidity"]["observed_days"] == 30
        assert len(catalog["catalog_id"]) == 64

        preview_response = client.post(
            "/api/studio/datasets/binance/preview",
            json={
                "catalog_id": catalog["catalog_id"],
                "symbol": "ETHEUR",
                "interval": "1m",
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-03T00:00:00Z",
            },
        )
        assert preview_response.status_code == 200, preview_response.text
        preview = preview_response.json()
        assert preview["catalog_identity"] == catalog["catalog_id"]
        assert preview["symbol_metadata"]["quote_asset"] == "EUR"
        assert preview["limits"] == {
            "max_days": 7,
            "max_objects": 7,
            "max_bytes": 268435456,
        }
        assert len(preview["sources"]) == 2

        imported = client.post(
            "/api/studio/datasets/binance/import",
            json={"preview_id": preview["preview_id"]},
        )
        assert imported.status_code == 201, imported.text
        manifest = imported.json()
        assert manifest["catalog_identity"] == catalog["catalog_id"]
        assert manifest["symbol_metadata"]["quote_asset"] == "EUR"
        assert manifest["quality"]["rows"] == 2880
        assert manifest["quality"]["gaps"] == 0

        backtest = client.post(
            "/api/studio/backtests/manifested",
            json={
                "dataset_id": manifest["dataset_id"],
                "spec": {
                    "symbol": "ETHEUR",
                    "market_type": "spot",
                    "initial_cash": 10_000,
                    "grid": {
                        "levels": 8,
                        "lower": 3000,
                        "upper": 3100,
                        "spacing": "geometric",
                        "direction": "neutral",
                    },
                    "sizing": {"mode": "fixed_quote", "value": 50},
                    "fees": {"maker": 0.001, "taker": 0.001},
                },
            },
        )
        assert backtest.status_code == 201, backtest.text
        run = backtest.json()
        assert run["result"]["bars"] == 2880
        assert run["result"]["metrics"]["win_rate"] is None
        assert run["provenance"]["catalog_identity"] == catalog["catalog_id"]
        assert run["provenance"]["quote_asset"] == "EUR"
        assert run["provenance"]["testnet_history_used"] is False
        assert len(run["provenance"]["backtest_fingerprint"]) == 64


def test_typed_api_rejects_unknown_symbols_and_known_archive_gaps(
    tmp_path: Path,
) -> None:
    with _client(tmp_path) as client:
        catalog = client.get("/api/studio/catalogs/binance/eur?refresh=true").json()
        unknown = client.post(
            "/api/studio/datasets/binance/preview",
            json={
                "catalog_id": catalog["catalog_id"],
                "symbol": "SOLEUR",
                "interval": "1m",
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-02T00:00:00Z",
            },
        )
        assert unknown.status_code == 400
        assert "not admitted by catalog" in unknown.json()["detail"]

        gap = client.post(
            "/api/studio/datasets/binance/preview",
            json={
                "catalog_id": catalog["catalog_id"],
                "symbol": "BTCEUR",
                "interval": "1m",
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-03T00:00:00Z",
            },
        )
        assert gap.status_code == 400
        assert "known archive gap 2025-01-02" in gap.json()["detail"]


def test_catalog_repository_rehashes_persisted_snapshots(tmp_path: Path) -> None:
    repository = StudioCatalogRepository(
        tmp_path / "catalogs",
        FixtureCatalogClient(),
        clock=lambda: NOW,
    )
    catalog = repository.refresh()
    snapshot = repository.snapshots / f"{catalog.catalog_id}.json"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["symbols"][0]["status"] = "BREAK"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogAdmissionError, match="identity mismatch"):
        repository.get(catalog.catalog_id)


def test_catalog_repository_refuses_conflicting_content_addressed_write(
    tmp_path: Path,
) -> None:
    repository = StudioCatalogRepository(
        tmp_path / "catalogs",
        FixtureCatalogClient(),
        clock=lambda: NOW,
    )
    catalog = repository.refresh()
    snapshot = repository.snapshots / f"{catalog.catalog_id}.json"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["symbols"][0]["status"] = "BREAK"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogAdmissionError, match="conflicts"):
        repository.refresh()

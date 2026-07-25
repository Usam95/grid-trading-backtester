from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from calendar import monthrange
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.studio_panels import StudioProductionPanelRepository, studio_production_panel_repository
from backend.studio_runs import SqliteStudioRunStore, studio_run_store
from gridlab.data.binance_catalog import ArchiveCoverage
from gridlab.data.binance_panel import FROZEN_EUR_SYMBOLS

NOW = datetime(2025, 2, 4, tzinfo=timezone.utc)
FIRST_DATES = {
    "BTCEUR": date(2024, 12, 31),
    "ETHEUR": date(2025, 1, 1),
    "SOLEUR": date(2025, 1, 5),
    "XRPEUR": date(2025, 1, 10),
    "ADAEUR": date(2025, 1, 15),
    "PEPEEUR": date(2025, 1, 20),
    "BNBEUR": date(2025, 1, 25),
    "DOGEEUR": date(2025, 2, 1),
    "XLMEUR": date(2025, 2, 2),
    "LTCEUR": date(2025, 2, 3),
}


def _symbol(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": "TRADING",
        "baseAsset": symbol.removesuffix("EUR"),
        "quoteAsset": "EUR",
        "isSpotTradingAllowed": True,
        "orderTypes": ["LIMIT", "LIMIT_MAKER", "MARKET"],
    }


class FixtureCatalogClient:
    production_url = "https://data-api.binance.vision/api/v3/exchangeInfo"

    def production_exchange_info(self) -> dict[str, object]:
        return {
            "timezone": "UTC",
            "serverTime": int(NOW.timestamp() * 1000),
            "symbols": [_symbol(symbol) for symbol in FROZEN_EUR_SYMBOLS],
        }

    def archive_coverage(self, symbol: str, _as_of: date) -> ArchiveCoverage:
        return ArchiveCoverage(
            first_date=FIRST_DATES[symbol],
            last_date=date(2025, 2, 3),
            intervals=("1m", "5m", "1h", "1d"),
            known_gap_dates=(),
            evidence_urls=(f"https://data.binance.vision/coverage/{symbol}",),
        )


class FixtureArchiveClient:
    def checksum(self, url: str) -> str:
        return hashlib.sha256(self._payload(url.removesuffix(".CHECKSUM"))).hexdigest()

    def content_length(self, url: str) -> int:
        return len(self._payload(url))

    def download(self, url: str) -> bytes:
        return self._payload(url)

    def _payload(self, url: str) -> bytes:
        name = url.rsplit("/", 1)[-1].removesuffix(".zip")
        symbol, _interval, period = name.split("-", 2)
        if "/monthly/" in url:
            year, month = map(int, period.split("-"))
            end_day = date(year, month, monthrange(year, month)[1])
            return _archive(
                symbol,
                period,
                start_day=max(FIRST_DATES[symbol], date(year, month, 1)),
                end_day=end_day,
            )
        day = date.fromisoformat(period)
        return _archive(symbol, period, start_day=day, end_day=day)


def _archive(symbol: str, label: str, *, start_day: date, end_day: date) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    day = start_day
    while day <= end_day:
        resolution = 1_000 if day < date(2025, 1, 1) else 1_000_000
        price = Decimal(str(100 + FROZEN_EUR_SYMBOLS.index(symbol)))
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        for minute in range(24 * 60):
            opened = start + timedelta(minutes=minute)
            open_raw = int(opened.timestamp() * resolution)
            writer.writerow(
                [
                    open_raw,
                    f"{price:.8f}",
                    f"{(price + Decimal('1')):.8f}",
                    f"{(price - Decimal('1')):.8f}",
                    f"{(price + Decimal('0.5')):.8f}",
                    "1.00000000",
                    open_raw + 60 * resolution - 1,
                    f"{(price * Decimal('1.5')):.8f}",
                    42,
                    "0.50000000",
                    f"{price:.8f}",
                    0,
                ]
            )
        day += timedelta(days=1)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo(f"{symbol}-1m-{label}.csv")
        entry.date_time = (2025, 2, 4, 0, 0, 0)
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, output.getvalue())
    return buffer.getvalue()


@contextmanager
def _client(root: Path) -> Iterator[TestClient]:
    class FixedRepository(StudioProductionPanelRepository):
        def get(self, *, refresh: bool = False) -> dict[str, object]:
            existing = self.root / "index.json"
            if existing.is_file() and not refresh:
                return service.read_synchronized_production_archive(self.root)
            return service.preview_synchronized_production_archive(
                self.catalog_client,
                self.archive_client,
                self.root,
                retrieved_at=NOW,
            )

        def synchronize(self) -> dict[str, object]:
            return service.synchronize_synchronized_production_archive(
                self.catalog_client,
                self.archive_client,
                self.root,
                retrieved_at=NOW,
            )

        def create_snapshot(self, dataset_id: str, start: datetime, end: datetime) -> dict[str, object]:
            return service.create_production_snapshot_manifest(
                self.root,
                dataset_id,
                start,
                end,
                retrieved_at=NOW,
            )

    from backend import service

    repository = FixedRepository(root, FixtureCatalogClient(), FixtureArchiveClient())

    def override_runs() -> Iterator[SqliteStudioRunStore]:
        with SqliteStudioRunStore(root / "studio.sqlite3") as store:
            yield store

    app.dependency_overrides[studio_production_panel_repository] = lambda: repository
    app.dependency_overrides[studio_run_store] = override_runs
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_typed_api_exposes_the_synchronized_ten_symbol_eur_archive(tmp_path: Path) -> None:
    with _client(tmp_path / "archive") as client:
        preview_response = client.get("/api/studio/archives/binance/eur?refresh=true")
        assert preview_response.status_code == 200, preview_response.text
        preview = preview_response.json()
        assert preview["status"] == "pending"
        assert preview["quote_asset"] == "EUR"
        assert preview["symbols"] == list(FROZEN_EUR_SYMBOLS)
        assert preview["preview"]["source_objects"] == 35

        sync_response = client.post("/api/studio/archives/binance/eur/synchronize")
        assert sync_response.status_code == 200, sync_response.text
        archive = sync_response.json()
        assert archive["status"] == "ready"
        assert len(archive["datasets"]) == 10
        assert archive["preview"]["pending_partitions"] == 0
        assert archive["datasets"][0]["verified_ranges"] == [
            {"start": "2024-12-31T00:00:00Z", "end": "2025-02-04T00:00:00Z"}
        ]


def test_typed_api_replays_local_eur_archive_snapshot(tmp_path: Path) -> None:
    with _client(tmp_path / "archive") as client:
        archive = client.post("/api/studio/archives/binance/eur/synchronize").json()
        dataset = next(item for item in archive["datasets"] if item["symbol"] == "ETHEUR")

        response = client.post(
            "/api/studio/backtests/production-archive",
            json={
                "dataset_id": dataset["dataset_id"],
                "start": "2025-01-02T00:00:00Z",
                "end": "2025-01-05T00:00:00Z",
                "spec": {
                    "symbol": "ETHEUR",
                    "market_type": "spot",
                    "initial_cash": 10000,
                    "grid": {
                        "levels": 8,
                        "lower": 90,
                        "upper": 120,
                        "spacing": "geometric",
                        "direction": "neutral",
                    },
                    "sizing": {"mode": "fixed_quote", "value": 50},
                    "fees": {"maker": 0.001, "taker": 0.001},
                },
            },
        )
        assert response.status_code == 201, response.text
        run = response.json()
        assert run["result"]["bars"] == 3 * 1440
        assert run["provenance"]["dataset_id"] == dataset["dataset_id"]
        assert run["provenance"]["quote_asset"] == "EUR"
        assert run["provenance"]["candle_count"] == 3 * 1440
        assert run["provenance"]["partition_identities"]
        assert run["provenance"]["source_provider"] == "official Binance public archive"


def test_production_archive_contract_is_explicit_in_openapi() -> None:
    schema = app.openapi()

    assert schema["paths"]["/api/studio/archives/binance/eur"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {"$ref": "#/components/schemas/FrozenProductionPanel"}
    assert schema["paths"]["/api/studio/archives/binance/eur/synchronize"]["post"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/FrozenProductionPanel"
    }
    assert schema["paths"]["/api/studio/backtests/production-archive"]["post"]["responses"][
        "201"
    ]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StudioBacktestRun"
    }
    provenance = schema["components"]["schemas"]["ProductionDatasetProvenance"]
    assert "partition_identities" in provenance["properties"]
    assert "candle_count" in provenance["properties"]

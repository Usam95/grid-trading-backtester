from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from gridlab.data.binance_catalog import ArchiveCoverage
from gridlab.data.binance_panel import (
    FROZEN_EUR_SYMBOLS,
    create_production_snapshot_manifest,
    load_production_snapshot_candles,
    preview_synchronized_production_archive,
    synchronize_synchronized_production_archive,
)

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

    def __init__(
        self,
        *,
        last_date: date,
        gaps: dict[str, tuple[date, ...]] | None = None,
        server_time: datetime = NOW,
    ) -> None:
        self.last_date = last_date
        self.gaps = gaps or {}
        self.server_time = server_time

    def production_exchange_info(self) -> dict[str, object]:
        return {
            "timezone": "UTC",
            "serverTime": int(self.server_time.timestamp() * 1000),
            "symbols": [_symbol(symbol) for symbol in FROZEN_EUR_SYMBOLS],
        }

    def archive_coverage(self, symbol: str, _as_of: date) -> ArchiveCoverage:
        return ArchiveCoverage(
            first_date=FIRST_DATES[symbol],
            last_date=self.last_date,
            intervals=("1m", "5m", "1h", "1d"),
            known_gap_dates=self.gaps.get(symbol, ()),
            evidence_urls=(f"https://data.binance.vision/coverage/{symbol}",),
        )


class FixtureArchiveClient:
    def __init__(self, *, duplicate_source: tuple[str, str] | None = None) -> None:
        self.duplicate_source = duplicate_source
        self.downloaded_urls: list[str] = []

    def checksum(self, url: str) -> str:
        return hashlib.sha256(self._payload(url.removesuffix(".CHECKSUM"))).hexdigest()

    def content_length(self, url: str) -> int:
        return len(self._payload(url))

    def download(self, url: str) -> bytes:
        self.downloaded_urls.append(url)
        return self._payload(url)

    def _payload(self, url: str) -> bytes:
        name = url.rsplit("/", 1)[-1].removesuffix(".zip")
        symbol, interval, period = name.split("-", 2)
        if "/monthly/" in url:
            year, month = map(int, period.split("-"))
            return _archive(
                symbol, period, first_day=max(FIRST_DATES[symbol], date(year, month, 1))
            )
        if "/daily/" in url:
            day = date.fromisoformat(period)
            duplicate = self.duplicate_source == (symbol, day.isoformat())
            return _archive(
                symbol, day.isoformat(), first_day=day, last_day=day, duplicate=duplicate
            )
        raise AssertionError(url)


class PartialFirstDayArchiveClient(FixtureArchiveClient):
    def __init__(self, *, symbol: str, month: str, skip_minutes: int) -> None:
        super().__init__()
        self.symbol = symbol
        self.month = month
        self.skip_minutes = skip_minutes

    def _payload(self, url: str) -> bytes:
        payload = super()._payload(url)
        name = url.rsplit("/", 1)[-1].removesuffix(".zip")
        symbol, _interval, period = name.split("-", 2)
        if "/monthly/" not in url or symbol != self.symbol or period != self.month:
            return payload
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            filename = archive.namelist()[0]
            rows = list(csv.reader(io.StringIO(archive.read(filename).decode("utf-8"))))
        trimmed = rows[self.skip_minutes :]
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerows(trimmed)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            entry = zipfile.ZipInfo(filename)
            entry.date_time = (2025, 2, 4, 0, 0, 0)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, output.getvalue())
        return buffer.getvalue()


def _minute_rows(symbol: str, day: date) -> list[list[object]]:
    resolution = 1_000 if day < date(2025, 1, 1) else 1_000_000
    price = Decimal(str(100 + FROZEN_EUR_SYMBOLS.index(symbol)))
    rows: list[list[object]] = []
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    for minute in range(24 * 60):
        opened = start + timedelta(minutes=minute)
        open_raw = int(opened.timestamp() * resolution)
        rows.append(
            [
                open_raw,
                f"{price:.8f}",
                f"{(price + Decimal('1')):.8f}",
                f"{(price - Decimal('1')):.8f}",
                f"{(price + Decimal('0.5')):.8f}",
                "1.00000000",
                open_raw + 60 * resolution - 1,
                f"{(price * Decimal('1.5')):.8f}",
                minute + 1,
                "0.50000000",
                f"{price:.8f}",
                0,
            ]
        )
    return rows


def _archive(
    symbol: str,
    label: str,
    *,
    first_day: date,
    last_day: date | None = None,
    duplicate: bool = False,
) -> bytes:
    if last_day is None:
        year, month = map(int, label.split("-"))
        last_day = date(year, month, monthrange(year, month)[1])
        filename = f"{symbol}-1m-{label}.csv"
    else:
        filename = f"{symbol}-1m-{label}.csv"
    rows: list[list[object]] = []
    day = max(first_day, FIRST_DATES[symbol])
    final_day = last_day
    while day <= final_day:
        rows.extend(_minute_rows(symbol, day))
        day += timedelta(days=1)
    if duplicate and rows:
        rows.insert(1, rows[0])
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo(filename)
        entry.date_time = (2025, 2, 4, 0, 0, 0)
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, output.getvalue())
    return buffer.getvalue()


def test_preview_reports_ten_symbol_eur_work_before_download(tmp_path: Path) -> None:
    preview = preview_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        FixtureArchiveClient(),
        tmp_path,
        retrieved_at=NOW,
    )

    assert preview["status"] == "pending"
    assert preview["quote_asset"] == "EUR"
    assert preview["symbols"] == list(FROZEN_EUR_SYMBOLS)
    assert preview["preview"]["source_objects"] == 35
    assert preview["preview"]["pending_partitions"] == 18
    assert preview["preview"]["estimated_download_bytes"] > 0
    assert preview["preview"]["estimated_storage_bytes"] > 0
    assert preview["datasets"][0]["coverage"]["first_date"] == "2024-12-31"
    assert preview["preview"]["symbols"][0]["plans"][0]["month"] == "2024-12"
    assert (tmp_path / "previews").is_dir()


def test_sync_publishes_monthly_partitions_and_snapshot_ranges(tmp_path: Path) -> None:
    archive = synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        FixtureArchiveClient(),
        tmp_path,
        retrieved_at=NOW,
        max_workers=2,
    )

    assert archive["status"] == "ready"
    assert archive["preview"]["pending_partitions"] == 0
    assert archive["preview"]["verified_partitions"] == 18

    btc = archive["datasets"][0]
    assert btc["symbol"] == "BTCEUR"
    assert btc["dataset_id"]
    assert btc["verified_ranges"] == [
        {"start": "2024-12-31T00:00:00+00:00", "end": "2025-02-04T00:00:00+00:00"}
    ]
    assert len([item for item in btc["partitions"] if item["active"]]) == 3

    eth = next(item for item in archive["datasets"] if item["symbol"] == "ETHEUR")
    snapshot = create_production_snapshot_manifest(
        tmp_path,
        eth["dataset_id"],
        datetime(2025, 1, 2, tzinfo=timezone.utc),
        datetime(2025, 2, 4, tzinfo=timezone.utc),
        retrieved_at=NOW,
    )
    assert snapshot["candle_count"] == 33 * 1440
    assert snapshot["partition_identities"]
    candles = load_production_snapshot_candles(Path(snapshot["manifest_path"]))
    assert len(candles) == 33 * 1440
    assert candles[0].timestamp == datetime(2025, 1, 2, tzinfo=timezone.utc)
    assert candles[-1].timestamp == datetime(2025, 2, 3, 23, 59, tzinfo=timezone.utc)


def test_sync_resumes_incrementally_without_redownloading_verified_months(tmp_path: Path) -> None:
    initial_at = NOW
    resumed_at = NOW + timedelta(days=1)
    initial_client = FixtureArchiveClient()
    synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        initial_client,
        tmp_path,
        retrieved_at=initial_at,
        max_workers=2,
    )
    resumed_client = FixtureArchiveClient()
    archive = synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 4), server_time=resumed_at),
        resumed_client,
        tmp_path,
        retrieved_at=resumed_at,
        max_workers=2,
    )

    assert archive["status"] == "ready"
    assert archive["preview"]["pending_partitions"] == 0
    assert resumed_client.downloaded_urls
    assert all("/daily/" in url for url in resumed_client.downloaded_urls)
    assert len(resumed_client.downloaded_urls) == 10


def test_sync_redownloads_a_tampered_partition_instead_of_reusing_it(tmp_path: Path) -> None:
    synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        FixtureArchiveClient(),
        tmp_path,
        retrieved_at=NOW,
        max_workers=2,
    )
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    eth = next(item for item in index["datasets"] if item["symbol"] == "ETHEUR")
    january = next(item for item in eth["partitions"] if item["month"] == "2025-01" and item["active"])
    parquet_path = tmp_path / january["path"]
    parquet_path.write_bytes(parquet_path.read_bytes() + b"tamper")

    resumed_client = FixtureArchiveClient()
    archive = synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        resumed_client,
        tmp_path,
        retrieved_at=NOW,
        max_workers=2,
    )

    assert archive["status"] == "ready"
    assert any("/monthly/klines/ETHEUR/1m/ETHEUR-1m-2025-01.zip" in url for url in resumed_client.downloaded_urls)


def test_sync_accepts_a_partial_first_listing_day_in_the_initial_month(tmp_path: Path) -> None:
    archive = synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        PartialFirstDayArchiveClient(symbol="ETHEUR", month="2025-01", skip_minutes=8 * 60),
        tmp_path,
        retrieved_at=NOW,
        max_workers=2,
    )

    assert archive["status"] == "ready"
    eth = next(item for item in archive["datasets"] if item["symbol"] == "ETHEUR")
    assert eth["verified_ranges"][0]["start"] == "2025-01-01T08:00:00+00:00"


def test_gap_or_duplicate_findings_block_partition_admission(tmp_path: Path) -> None:
    archive = synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3), gaps={"ETHEUR": (date(2025, 1, 13),)}),
        FixtureArchiveClient(duplicate_source=("BTCEUR", "2025-02-03")),
        tmp_path,
        retrieved_at=NOW,
        max_workers=2,
    )

    assert archive["status"] == "blocked"
    assert any(
        "ETHEUR 2025-01 has official gap coverage days" in reason
        for reason in archive["blocking_reasons"]
    )
    assert any("BTCEUR 2025-02 blocked" in reason for reason in archive["blocking_reasons"])
    with pytest.raises(ValueError, match="not fully covered"):
        create_production_snapshot_manifest(
            tmp_path,
            archive["datasets"][0]["dataset_id"],
            datetime(2025, 2, 1, tzinfo=timezone.utc),
            datetime(2025, 2, 4, tzinfo=timezone.utc),
            retrieved_at=NOW,
        )


def test_snapshot_replay_fails_closed_when_a_partition_manifest_is_tampered(tmp_path: Path) -> None:
    archive = synchronize_synchronized_production_archive(
        FixtureCatalogClient(last_date=date(2025, 2, 3)),
        FixtureArchiveClient(),
        tmp_path,
        retrieved_at=NOW,
        max_workers=2,
    )
    eth = next(item for item in archive["datasets"] if item["symbol"] == "ETHEUR")
    snapshot = create_production_snapshot_manifest(
        tmp_path,
        eth["dataset_id"],
        datetime(2025, 1, 2, tzinfo=timezone.utc),
        datetime(2025, 1, 3, tzinfo=timezone.utc),
        retrieved_at=NOW,
    )
    manifest_path = tmp_path / snapshot["partitions"][0]["manifest_path"]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["row_count"] = 1
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="partition manifest checksum mismatch|partition row_count drifted from the index"):
        load_production_snapshot_candles(Path(snapshot["manifest_path"]))

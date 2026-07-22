from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gridlab.api.facade import BacktestSpec
from gridlab.data.binance_archive import (
    ArchiveRequest,
    DataAdmissionError,
    acquire_binance_archive,
    load_manifested_candles,
    preview_binance_archive,
    validate_timestamp_unit,
)
from gridlab.research.manifested import run_manifested_backtest


class FixtureArchiveClient:
    def __init__(self, archive: bytes | None = None) -> None:
        self.archive = archive
        self.downloaded: list[str] = []

    def checksum(self, url: str) -> str:
        assert url.endswith(".zip.CHECKSUM")
        return hashlib.sha256(self.archive).hexdigest() if self.archive else "a" * 64

    def content_length(self, url: str) -> int:
        assert url.endswith(".zip")
        return len(self.archive) if self.archive else 123_456

    def download(self, url: str) -> bytes:
        self.downloaded.append(url)
        if self.archive is None:
            raise AssertionError("preview must not download archive bytes")
        return self.archive


def _archive(
    *,
    day: datetime = datetime(2025, 1, 1, tzinfo=timezone.utc),
    omit_minute: int | None = None,
    duplicate_minute: int | None = None,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    start = day
    resolution = 1_000_000 if day.date() >= datetime(2025, 1, 1).date() else 1_000
    for minute in range(1440):
        if minute == omit_minute:
            continue
        open_time = int((start + timedelta(minutes=minute)).timestamp() * resolution)
        writer.writerow(
            [
                open_time,
                "93000.00000000",
                "93100.00000000",
                "92900.00000000",
                "93050.00000000",
                "1.25000000",
                open_time + 60 * resolution - 1,
                "116312.50000000",
                42,
                "0.75000000",
                "69787.50000000",
                0,
            ]
        )
        if minute == duplicate_minute:
            writer.writerow(
                [
                    open_time,
                    "93000.00000000",
                    "93100.00000000",
                    "92900.00000000",
                    "93050.00000000",
                    "1.25000000",
                    open_time + 60 * resolution - 1,
                    "116312.50000000",
                    42,
                    "0.75000000",
                    "69787.50000000",
                    0,
                ]
            )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"BTCUSDT-1m-{day.date().isoformat()}.csv", output.getvalue())
    return buffer.getvalue()


def test_preview_identifies_bounded_official_spot_sources_before_download() -> None:
    client = FixtureArchiveClient()
    request = ArchiveRequest(
        symbol="BTCUSDT",
        interval="1m",
        start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    preview = preview_binance_archive(request, client)

    assert preview.symbol == "BTCUSDT"
    assert preview.interval == "1m"
    assert preview.start.isoformat() == "2025-01-01T00:00:00+00:00"
    assert preview.end.isoformat() == "2025-01-02T00:00:00+00:00"
    assert preview.estimated_bytes == 123_456
    assert len(preview.preview_id) == 64
    assert preview.sources[0].url == (
        "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2025-01-01.zip"
    )
    assert preview.sources[0].expected_sha256 == "a" * 64
    assert client.downloaded == []


def test_timestamp_units_follow_the_official_spot_archive_era() -> None:
    assert (
        validate_timestamp_unit([1735603200000, 1735603259999], datetime(2024, 12, 31).date())
        == "milliseconds"
    )
    assert (
        validate_timestamp_unit([1735689600000000, 1735689659999999], datetime(2025, 1, 1).date())
        == "microseconds"
    )


@pytest.mark.parametrize(
    ("values", "archive_date"),
    [
        ([17356896000000], datetime(2025, 1, 1).date()),
        ([1735689600000, 1735689660000000], datetime(2025, 1, 1).date()),
        ([1735689600000000], datetime(2024, 12, 31).date()),
    ],
)
def test_ambiguous_mixed_or_wrong_era_timestamp_units_are_rejected(
    values: list[int], archive_date: object
) -> None:
    with pytest.raises(DataAdmissionError, match="timestamp unit"):
        validate_timestamp_unit(values, archive_date)  # type: ignore[arg-type]


def test_verified_archive_becomes_a_complete_typed_manifested_dataset(
    tmp_path: Path,
) -> None:
    client = FixtureArchiveClient(_archive())
    request = ArchiveRequest(
        "BTCUSDT",
        "1m",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    preview = preview_binance_archive(request, client)

    manifest = acquire_binance_archive(
        preview,
        client,
        tmp_path,
        retrieved_at=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert manifest["history_environment"] == "production"
    assert manifest["source_provider"] == "official Binance public archive"
    assert manifest["quality"] == {
        "rows": 1440,
        "gaps": 0,
        "duplicates": 0,
        "out_of_order": 0,
        "invalid_records": 0,
    }
    assert manifest["timestamp"]["source_units"] == ["microseconds"]
    assert manifest["timestamp"]["normalized_unit"] == "microseconds"
    assert manifest["normalization"]["format"] == "parquet"
    assert manifest["normalization"]["schema"][0] == {
        "name": "open_time",
        "type": "timestamp[us, tz=UTC]",
        "nullable": False,
    }
    assert len(manifest["dataset_id"]) == 64
    assert len(manifest["manifest_sha256"]) == 64
    assert Path(manifest["manifest_path"]).is_file()

    candles = load_manifested_candles(Path(manifest["manifest_path"]))
    assert len(candles) == 1440
    assert candles[0].timestamp == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert candles[-1].timestamp == datetime(2025, 1, 1, 23, 59, tzinfo=timezone.utc)
    assert [candle.index for candle in candles] == list(range(1440))


def test_pre_2025_archive_is_admitted_as_millisecond_source_evidence(
    tmp_path: Path,
) -> None:
    day = datetime(2024, 12, 31, tzinfo=timezone.utc)
    client = FixtureArchiveClient(_archive(day=day))
    preview = preview_binance_archive(
        ArchiveRequest("BTCUSDT", "1m", day, day + timedelta(days=1)), client
    )

    manifest = acquire_binance_archive(
        preview,
        client,
        tmp_path,
        retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )

    assert manifest["timestamp"]["source_units"] == ["milliseconds"]
    assert manifest["timestamp"]["normalized_unit"] == "microseconds"


def test_offline_reader_rejects_missing_or_modified_source_evidence(
    tmp_path: Path,
) -> None:
    client = FixtureArchiveClient(_archive())
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )
    manifest = acquire_binance_archive(
        preview,
        client,
        tmp_path,
        retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )
    manifest_path = Path(manifest["manifest_path"])
    source_path = manifest_path.parent / manifest["sources"][0]["archive_path"]
    original = source_path.read_bytes()

    source_path.unlink()
    with pytest.raises(DataAdmissionError, match="source archive is missing"):
        load_manifested_candles(manifest_path)

    source_path.write_bytes(original + b"changed")
    with pytest.raises(DataAdmissionError, match="source archive checksum mismatch"):
        load_manifested_candles(manifest_path)


def test_reacquisition_rejects_a_corrupt_existing_content_id(
    tmp_path: Path,
) -> None:
    client = FixtureArchiveClient(_archive())
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )
    manifest = acquire_binance_archive(
        preview,
        client,
        tmp_path,
        retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )
    manifest_path = Path(manifest["manifest_path"])
    parquet_path = manifest_path.parent / manifest["normalization"]["path"]
    parquet_path.write_bytes(parquet_path.read_bytes() + b"corrupt")

    with pytest.raises(DataAdmissionError, match="Parquet checksum mismatch"):
        acquire_binance_archive(
            preview,
            client,
            tmp_path,
            retrieved_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
        )


def test_discontinuous_archive_is_not_admitted(tmp_path: Path) -> None:
    client = FixtureArchiveClient(_archive(omit_minute=17))
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )

    with pytest.raises(DataAdmissionError, match="gaps=1"):
        acquire_binance_archive(
            preview,
            client,
            tmp_path,
            retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )

    assert list(tmp_path.rglob("manifest.json")) == []


def test_duplicate_archive_is_not_admitted(tmp_path: Path) -> None:
    client = FixtureArchiveClient(_archive(duplicate_minute=17))
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )

    with pytest.raises(DataAdmissionError, match="duplicates=1"):
        acquire_binance_archive(
            preview,
            client,
            tmp_path,
            retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )


def test_replaced_corrupt_and_missing_source_evidence_is_reported(tmp_path: Path) -> None:
    original = _archive()
    client = FixtureArchiveClient(original)
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )

    client.archive = _archive(omit_minute=3)
    with pytest.raises(DataAdmissionError, match="replaced source evidence"):
        acquire_binance_archive(
            preview,
            client,
            tmp_path,
            retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )

    corrupt = FixtureArchiveClient(b"not a zip")
    corrupt_preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        corrupt,
    )
    with pytest.raises(DataAdmissionError, match="corrupt source archive"):
        acquire_binance_archive(
            corrupt_preview,
            corrupt,
            tmp_path,
            retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )

    class MissingClient(FixtureArchiveClient):
        def download(self, url: str) -> bytes:
            raise DataAdmissionError(f"missing official source archive: {url}")

    missing = MissingClient(original)
    missing_preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        missing,
    )
    with pytest.raises(DataAdmissionError, match="missing official source archive"):
        acquire_binance_archive(
            missing_preview,
            missing,
            tmp_path,
            retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )


def test_offline_parquet_reproduces_the_backtest_fingerprint(tmp_path: Path) -> None:
    client = FixtureArchiveClient(_archive())
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )
    manifest = acquire_binance_archive(
        preview,
        client,
        tmp_path,
        retrieved_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )
    specification = {
        "symbol": "BTCUSDT",
        "market_type": "spot",
        "initial_cash": 10_000.0,
        "grid": {
            "levels": 8,
            "lower": 92_500.0,
            "upper": 93_500.0,
            "spacing": "geometric",
            "direction": "neutral",
        },
        "sizing": {"mode": "fixed_quote", "value": 50.0},
        "fees": {"maker": 0.001, "taker": 0.001},
        "n_trials": 1,
    }

    first = run_manifested_backtest(specification, Path(manifest["manifest_path"]))
    second = run_manifested_backtest(specification, Path(manifest["manifest_path"]))
    typed = run_manifested_backtest(
        BacktestSpec.from_dict(specification), Path(manifest["manifest_path"])
    )

    assert first == second == typed
    assert first["dataset_id"] == manifest["dataset_id"]
    assert first["result"]["bars"] == 1440
    assert len(first["backtest_fingerprint"]) == 64

    with pytest.raises(ValueError, match="does not match dataset BTCUSDT"):
        run_manifested_backtest(
            {**specification, "symbol": "ETHUSDT"},
            Path(manifest["manifest_path"]),
        )

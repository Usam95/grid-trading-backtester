"""Synchronize a deterministic ten-symbol Binance Spot EUR production archive."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tempfile
import time
import zipfile
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence, cast

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from gridlab.core.models import Candle

from .binance_archive import validate_timestamp_unit
from .binance_catalog import ArchiveCoverage

FROZEN_EUR_SYMBOLS = (
    "BTCEUR",
    "ETHEUR",
    "SOLEUR",
    "XRPEUR",
    "ADAEUR",
    "PEPEEUR",
    "BNBEUR",
    "DOGEEUR",
    "XLMEUR",
    "LTCEUR",
)
QUOTE_ASSET = "EUR"
INTERVAL = "1m"
ARCHIVE_ID = hashlib.sha256(
    json.dumps(
        {
            "schema_version": "gridlab.synchronized-production-archive.v1",
            "symbols": FROZEN_EUR_SYMBOLS,
            "quote_asset": QUOTE_ASSET,
            "interval": INTERVAL,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
MAX_SYNC_WORKERS = 4
DOWNLOAD_RETRIES = 3
ROW_STORAGE_ESTIMATE_BYTES = 120
_NORMALIZER = "gridlab.binance-eur-production-monthly-partition.v1"
_PARTITION_ORDERING = ["open_time", "source_sha256", "source_row"]
_DECIMAL = pa.decimal128(38, 18)
_PARTITION_SCHEMA = pa.schema(
    [
        pa.field("open_time", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("open", _DECIMAL, nullable=False),
        pa.field("high", _DECIMAL, nullable=False),
        pa.field("low", _DECIMAL, nullable=False),
        pa.field("close", _DECIMAL, nullable=False),
        pa.field("volume", _DECIMAL, nullable=False),
        pa.field("close_time", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("quote_volume", _DECIMAL, nullable=False),
        pa.field("trade_count", pa.int64(), nullable=False),
        pa.field("taker_buy_base_volume", _DECIMAL, nullable=False),
        pa.field("taker_buy_quote_volume", _DECIMAL, nullable=False),
        pa.field("source_sha256", pa.string(), nullable=False),
        pa.field("source_row", pa.int32(), nullable=False),
    ]
)


class ProductionArchiveError(ValueError):
    """The synchronized production archive cannot admit the observed evidence."""


class ProductionArchiveCatalogClient(Protocol):
    production_url: str

    def production_exchange_info(self) -> Mapping[str, object]: ...

    def archive_coverage(self, symbol: str, as_of: date) -> ArchiveCoverage: ...


class ProductionArchiveClient(Protocol):
    def checksum(self, url: str) -> str: ...

    def content_length(self, url: str) -> int: ...

    def download(self, url: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class _SourcePlan:
    source_kind: str
    label: str
    url: str
    checksum_url: str
    expected_sha256: str
    estimated_bytes: int
    coverage_start: datetime
    coverage_end: datetime


@dataclass(frozen=True, slots=True)
class _PartitionPlan:
    symbol: str
    dataset_id: str
    month: str
    source_kind: str
    initial_month: bool
    coverage_start: datetime
    coverage_end: datetime
    expected_rows: int
    estimated_storage_bytes: int
    reason: str
    source_plans: tuple[_SourcePlan, ...]
    existing_partition: Mapping[str, object] | None


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256(value: object) -> str:
    data = value if isinstance(value, (bytes, bytearray)) else _canonical_json(value)
    return hashlib.sha256(data).hexdigest()


def _utc_midnight(day: date) -> datetime:
    return datetime.combine(day, dt_time.min, tzinfo=timezone.utc)


def _month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def _next_month(day: date) -> date:
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _month_label(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _month_end(day: date) -> date:
    return date(day.year, day.month, monthrange(day.year, day.month)[1])


def _decimal(value: object, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ProductionArchiveError(f"{field} is not a decimal") from exc
    if not number.is_finite():
        raise ProductionArchiveError(f"{field} is not finite")
    return number


def _canonical_decimal(value: Decimal) -> str:
    return format(value, ".18f")


def _timestamp(value: int, unit: str) -> datetime:
    divisor = 1_000_000 if unit == "microseconds" else 1_000
    seconds, remainder = divmod(value, divisor)
    microseconds = remainder if unit == "microseconds" else remainder * 1_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc) + timedelta(microseconds=microseconds)


def _schema_manifest() -> list[dict[str, object]]:
    return [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in _PARTITION_SCHEMA
    ]


def _dataset_id(symbol: str) -> str:
    return _sha256(
        {
            "schema_version": "gridlab.production-archive-dataset.v1",
            "provider": "binance",
            "market": "spot",
            "history_environment": "production",
            "quote_asset": QUOTE_ASSET,
            "interval": INTERVAL,
            "symbol": symbol,
        }
    )


def _serialize_coverage(coverage: ArchiveCoverage) -> dict[str, object]:
    return {
        "first_date": coverage.first_date.isoformat(),
        "last_date": coverage.last_date.isoformat(),
        "intervals": list(coverage.intervals),
        "known_gap_dates": [value.isoformat() for value in coverage.known_gap_dates],
        "evidence_urls": list(coverage.evidence_urls),
    }


def _index_path(root: Path) -> Path:
    return root / "index.json"


def _preview_dir(root: Path) -> Path:
    return root / "previews"


def _snapshots_dir(root: Path) -> Path:
    return root / "snapshots"


def _symbols_dir(root: Path) -> Path:
    return root / "symbols"


def _dataset_template(symbol: str, coverage: ArchiveCoverage, order: int) -> dict[str, object]:
    return {
        "symbol": symbol,
        "dataset_id": _dataset_id(symbol),
        "quote_asset": QUOTE_ASSET,
        "display_order": order,
        "coverage": _serialize_coverage(coverage),
        "verified_ranges": [],
        "total_rows": 0,
        "stored_bytes": 0,
        "partitions": [],
        "pending_partition_months": [],
    }


def _read_index(root: Path) -> dict[str, object] | None:
    path = _index_path(root)
    if not path.is_file():
        return None
    index = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    changed = False
    for dataset in cast(list[dict[str, object]], index.get("datasets", [])):
        for partition in cast(list[dict[str, object]], dataset.get("partitions", [])):
            if "manifest_identity" in partition:
                continue
            manifest_path = partition.get("manifest_path")
            if not isinstance(manifest_path, str):
                continue
            file_path = root / manifest_path
            if not file_path.is_file():
                continue
            manifest = cast(dict[str, object], json.loads(file_path.read_text(encoding="utf-8")))
            manifest_identity = manifest.get("manifest_sha256")
            if not isinstance(manifest_identity, str):
                continue
            partition["manifest_identity"] = manifest_identity
            changed = True
    if changed:
        _write_index(root, index)
    return index


def read_synchronized_production_archive(root: Path) -> dict[str, object]:
    index = _read_index(root)
    if index is None:
        raise ProductionArchiveError("synchronized production archive is not initialized")
    return index


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gridlab-archive-", dir=path.parent) as tmp:
        temp_path = Path(tmp) / path.name
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for attempt in range(5):
            try:
                temp_path.replace(path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.1 * (attempt + 1))


def _write_index(root: Path, payload: Mapping[str, object]) -> None:
    _write_json_atomic(_index_path(root), payload)


def _write_preview(root: Path, payload: Mapping[str, object]) -> None:
    preview = cast(Mapping[str, object], payload["preview"])
    preview_id = cast(str, preview["preview_id"])
    directory = _preview_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(directory / f"{preview_id}.json", payload)
    _write_json_atomic(root / "latest-preview.json", {"preview_id": preview_id})


def _read_latest_preview(root: Path) -> dict[str, object] | None:
    pointer = root / "latest-preview.json"
    if not pointer.is_file():
        return None
    payload = cast(dict[str, object], json.loads(pointer.read_text(encoding="utf-8")))
    preview_id = payload.get("preview_id")
    if not isinstance(preview_id, str) or not preview_id:
        return None
    path = _preview_dir(root) / f"{preview_id}.json"
    if not path.is_file():
        return None
    status = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    if status.get("archive_id") != ARCHIVE_ID:
        return None
    return status


def _monthly_archive_url(symbol: str, month: str) -> tuple[str, str]:
    url = (
        f"https://data.binance.vision/data/spot/monthly/klines/"
        f"{symbol}/{INTERVAL}/{symbol}-{INTERVAL}-{month}.zip"
    )
    return url, f"{url}.CHECKSUM"


def _daily_archive_url(symbol: str, day: date) -> tuple[str, str]:
    label = day.isoformat()
    url = (
        f"https://data.binance.vision/data/spot/daily/klines/"
        f"{symbol}/{INTERVAL}/{symbol}-{INTERVAL}-{label}.zip"
    )
    return url, f"{url}.CHECKSUM"


def _retry(operation, description: str):
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == DOWNLOAD_RETRIES:
                break
            time.sleep(0.2 * attempt)
    raise ProductionArchiveError(
        f"{description} failed after {DOWNLOAD_RETRIES} attempts: {last_error}"
    )


def _production_symbols(
    payload: Mapping[str, object], *, retrieved_at: datetime
) -> tuple[dict[str, Mapping[str, object]], dict[str, object]]:
    if payload.get("timezone") != "UTC":
        raise ProductionArchiveError("production exchangeInfo timezone is not UTC")
    try:
        server_time = datetime.fromtimestamp(
            int(cast(str | int | float, payload["serverTime"])) / 1000,
            tz=timezone.utc,
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise ProductionArchiveError("production exchangeInfo serverTime is invalid") from exc
    if abs(retrieved_at - server_time) > timedelta(minutes=15):
        raise ProductionArchiveError("production exchangeInfo evidence is stale")
    raw_symbols = payload.get("symbols")
    if not isinstance(raw_symbols, list):
        raise ProductionArchiveError("production exchangeInfo symbols are invalid")
    symbols: dict[str, Mapping[str, object]] = {}
    for raw in raw_symbols:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("symbol"), str):
            raise ProductionArchiveError("production exchangeInfo contains a malformed symbol")
        symbol = cast(str, raw["symbol"])
        if symbol in symbols:
            raise ProductionArchiveError(
                f"production exchangeInfo contains duplicate symbol {symbol}"
            )
        symbols[symbol] = raw
    source: dict[str, object] = {
        "kind": "production_exchange_info",
        "url": "https://data-api.binance.vision/api/v3/exchangeInfo",
        "observed_at": server_time.isoformat(),
        "identity": _sha256(dict(payload)),
    }
    return symbols, source


def _validate_symbol_metadata(symbol: str, raw: Mapping[str, object]) -> list[str]:
    problems: list[str] = []
    if raw.get("symbol") != symbol:
        problems.append("symbol_mismatch")
    if raw.get("quoteAsset") != QUOTE_ASSET:
        problems.append("quote_asset_not_eur")
    if raw.get("status") != "TRADING":
        problems.append("not_trading")
    if raw.get("isSpotTradingAllowed") is not True:
        problems.append("spot_trading_not_allowed")
    order_types = raw.get("orderTypes")
    if not isinstance(order_types, list) or "LIMIT_MAKER" not in order_types:
        problems.append("limit_maker_not_supported")
    return problems


def _path_exists(root: Path, relative_path: str) -> bool:
    return (root / relative_path).is_file()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_verified_partition_manifest(
    root: Path,
    partition: Mapping[str, object],
    *,
    expected_dataset_id: str | None = None,
    expected_symbol: str | None = None,
) -> dict[str, object]:
    parquet_path = partition.get("path")
    manifest_path = partition.get("manifest_path")
    if not isinstance(parquet_path, str) or not isinstance(manifest_path, str):
        raise ProductionArchiveError("partition evidence paths are malformed")
    parquet_file = root / parquet_path
    manifest_file = root / manifest_path
    if not parquet_file.is_file() or not manifest_file.is_file():
        raise ProductionArchiveError("partition evidence files are missing locally")
    manifest = cast(dict[str, object], json.loads(manifest_file.read_text(encoding="utf-8")))
    manifest_identity = manifest.pop("manifest_sha256", None)
    if not isinstance(manifest_identity, str):
        raise ProductionArchiveError("partition manifest identity is missing")
    if _sha256(_canonical_json(manifest)) != manifest_identity:
        raise ProductionArchiveError("partition manifest checksum mismatch")
    manifest["manifest_sha256"] = manifest_identity
    if manifest.get("manifest_path") != manifest_path or manifest.get("path") != parquet_path:
        raise ProductionArchiveError("partition manifest paths do not match the index")
    if manifest.get("verification_status") != "verified" or manifest.get("active") is not True:
        raise ProductionArchiveError("partition manifest is not verified and active")
    if partition.get("manifest_identity") != manifest_identity:
        raise ProductionArchiveError("partition manifest identity drifted from the index")
    for field in (
        "partition_id",
        "dataset_id",
        "symbol",
        "month",
        "coverage_start",
        "coverage_end",
        "source_kind",
        "row_count",
        "normalized_sha256",
    ):
        if field in partition and manifest.get(field) != partition.get(field):
            raise ProductionArchiveError(f"partition {field} drifted from the index")
    if expected_dataset_id is not None and manifest.get("dataset_id") != expected_dataset_id:
        raise ProductionArchiveError("partition dataset identity does not match the snapshot")
    if expected_symbol is not None and manifest.get("symbol") != expected_symbol:
        raise ProductionArchiveError("partition symbol does not match the snapshot")
    if _hash_file(parquet_file) != manifest.get("normalized_sha256"):
        raise ProductionArchiveError("partition parquet checksum mismatch")
    return manifest


def _partition_is_reusable(
    root: Path,
    partition: Mapping[str, object],
    expected: _PartitionPlan,
) -> bool:
    try:
        manifest = _read_verified_partition_manifest(root, partition)
    except ProductionArchiveError:
        return False
    if (
        manifest.get("dataset_id") != expected.dataset_id
        or manifest.get("symbol") != expected.symbol
    ):
        return False
    if (
        partition.get("month") != expected.month
        or partition.get("source_kind") != expected.source_kind
    ):
        return False
    partition_start = partition.get("coverage_start")
    if not isinstance(partition_start, str):
        return False
    if expected.initial_month:
        observed_start = datetime.fromisoformat(partition_start)
        if observed_start.date() != expected.coverage_start.date():
            return False
        if not expected.coverage_start <= observed_start < expected.coverage_end:
            return False
    elif partition_start != expected.coverage_start.isoformat():
        return False
    if partition.get("coverage_end") != expected.coverage_end.isoformat():
        return False
    return True


def _expected_months(
    coverage: ArchiveCoverage, retrieved_at: datetime
) -> list[tuple[str, datetime, datetime, str]]:
    first_month = _month_start(coverage.first_date)
    current_month = date(retrieved_at.year, retrieved_at.month, 1)
    months: list[tuple[str, datetime, datetime, str]] = []
    cursor = first_month
    while cursor <= _month_start(coverage.last_date):
        month_label = _month_label(cursor)
        month_start_dt = _utc_midnight(max(cursor, coverage.first_date))
        end_day = min(_month_end(cursor), coverage.last_date)
        month_end_dt = _utc_midnight(end_day + timedelta(days=1))
        source_kind = (
            "daily_archives_current_month" if cursor == current_month else "monthly_archive"
        )
        months.append((month_label, month_start_dt, month_end_dt, source_kind))
        cursor = _next_month(cursor)
    return months


def _source_plans(
    symbol: str,
    month: str,
    coverage_start: datetime,
    coverage_end: datetime,
    source_kind: str,
    archive_client: ProductionArchiveClient,
    existing_partition: Mapping[str, object] | None,
) -> tuple[_SourcePlan, ...]:
    plans: list[_SourcePlan] = []
    if source_kind == "monthly_archive":
        url, checksum_url = _monthly_archive_url(symbol, month)
        checksum = _retry(
            lambda: archive_client.checksum(checksum_url).strip().lower(),
            f"official checksum {symbol} {month}",
        )
        size = _retry(lambda: archive_client.content_length(url), f"official size {symbol} {month}")
        plans.append(
            _SourcePlan(
                source_kind=source_kind,
                label=month,
                url=url,
                checksum_url=checksum_url,
                expected_sha256=checksum,
                estimated_bytes=size,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
            )
        )
        return tuple(plans)

    download_start = coverage_start.date()
    if existing_partition is not None and existing_partition.get("source_kind") == source_kind:
        existing_end = datetime.fromisoformat(cast(str, existing_partition["coverage_end"]))
        if existing_end > coverage_start:
            download_start = existing_end.date()
    day = download_start
    final_day = (coverage_end - timedelta(days=1)).date()
    while day <= final_day:
        url, checksum_url = _daily_archive_url(symbol, day)
        checksum = _retry(
            lambda: archive_client.checksum(checksum_url).strip().lower(),
            f"official checksum {symbol} {day.isoformat()}",
        )
        size = _retry(
            lambda: archive_client.content_length(url),
            f"official size {symbol} {day.isoformat()}",
        )
        plans.append(
            _SourcePlan(
                source_kind=source_kind,
                label=day.isoformat(),
                url=url,
                checksum_url=checksum_url,
                expected_sha256=checksum,
                estimated_bytes=size,
                coverage_start=_utc_midnight(day),
                coverage_end=_utc_midnight(day + timedelta(days=1)),
            )
        )
        day += timedelta(days=1)
    return tuple(plans)


def _verified_ranges(partitions: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    ordered = sorted(
        (
            (
                datetime.fromisoformat(cast(str, item["coverage_start"])),
                datetime.fromisoformat(cast(str, item["coverage_end"])),
            )
            for item in partitions
            if item.get("active") is True and item.get("verification_status") == "verified"
        ),
        key=lambda item: item[0],
    )
    ranges: list[dict[str, str]] = []
    for start, end in ordered:
        if not ranges:
            ranges.append({"start": start.isoformat(), "end": end.isoformat()})
            continue
        last = ranges[-1]
        last_end = datetime.fromisoformat(last["end"])
        if start == last_end:
            last["end"] = end.isoformat()
        else:
            ranges.append({"start": start.isoformat(), "end": end.isoformat()})
    return ranges


def _build_status(
    *,
    datasets: list[dict[str, object]],
    sources: list[dict[str, object]],
    preview: dict[str, object],
    retrieved_at: datetime,
    blocking_reasons: list[str],
) -> dict[str, object]:
    for dataset in datasets:
        partitions = cast(list[dict[str, object]], dataset["partitions"])
        partitions.sort(key=lambda item: (item["month"], item["partition_id"]))
        dataset["verified_ranges"] = _verified_ranges(partitions)
        dataset["total_rows"] = int(
            sum(
                int(cast(int | str, item["row_count"]))
                for item in partitions
                if item.get("active") is True
            )
        )
        dataset["stored_bytes"] = int(
            sum(
                int(cast(int | str, item["byte_size"]))
                for item in partitions
                if item.get("active") is True
            )
        )
    pending_partitions = int(cast(int | str, preview["pending_partitions"]))
    status = "blocked" if blocking_reasons else "ready" if pending_partitions == 0 else "pending"
    return {
        "archive_id": ARCHIVE_ID,
        "status": status,
        "retrieved_at": retrieved_at.isoformat(),
        "quote_asset": QUOTE_ASSET,
        "interval": INTERVAL,
        "symbols": list(FROZEN_EUR_SYMBOLS),
        "sources": sources,
        "preview": preview,
        "datasets": datasets,
        "blocking_reasons": blocking_reasons,
    }


def preview_synchronized_production_archive(
    catalog_client: ProductionArchiveCatalogClient,
    archive_client: ProductionArchiveClient,
    root: Path,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
        raise ValueError("retrieved_at must be timezone-aware UTC")
    existing = _read_index(root) or {}
    existing_datasets = {
        cast(str, item["symbol"]): cast(dict[str, object], item)
        for item in cast(list[dict[str, object]], existing.get("datasets") or [])
    }
    production_symbols, production_source = _production_symbols(
        catalog_client.production_exchange_info(),
        retrieved_at=retrieved_at,
    )
    datasets: list[dict[str, object]] = []
    blocking_reasons: list[str] = []
    preview_symbols: list[dict[str, object]] = []
    pending_plans: list[_PartitionPlan] = []
    verified_partitions = 0

    for order, symbol in enumerate(FROZEN_EUR_SYMBOLS, start=1):
        raw = production_symbols.get(symbol)
        if raw is None:
            blocking_reasons.append(f"{symbol} is missing from production exchangeInfo")
            continue
        metadata_problems = _validate_symbol_metadata(symbol, raw)
        if metadata_problems:
            blocking_reasons.append(f"{symbol} metadata invalid: {', '.join(metadata_problems)}")
        coverage = catalog_client.archive_coverage(symbol, retrieved_at.date())
        dataset = existing_datasets.get(symbol, _dataset_template(symbol, coverage, order))
        dataset["display_order"] = order
        dataset["coverage"] = _serialize_coverage(coverage)
        dataset.setdefault("partitions", [])
        dataset["pending_partition_months"] = []
        datasets.append(dataset)

        existing_partitions = {
            cast(str, item["month"]): cast(dict[str, object], item)
            for item in cast(list[dict[str, object]], dataset["partitions"])
            if item.get("active") is True
        }
        symbol_pending: list[_PartitionPlan] = []
        gap_months = {_month_label(day) for day in coverage.known_gap_dates}
        for month, coverage_start, coverage_end, source_kind in _expected_months(
            coverage, retrieved_at
        ):
            expected_rows = int((coverage_end - coverage_start).total_seconds() // 60)
            estimated_storage_bytes = expected_rows * ROW_STORAGE_ESTIMATE_BYTES
            existing_partition = existing_partitions.get(month)
            if month in gap_months:
                cast(list[str], dataset["pending_partition_months"]).append(month)
                blocking_reasons.append(
                    f"{symbol} {month} has official gap coverage days and cannot be admitted"
                )
                continue
            plan = _PartitionPlan(
                symbol=symbol,
                dataset_id=cast(str, dataset["dataset_id"]),
                month=month,
                source_kind=source_kind,
                initial_month=month == _month_label(coverage.first_date),
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                expected_rows=expected_rows,
                estimated_storage_bytes=estimated_storage_bytes,
                reason="missing",
                source_plans=(),
                existing_partition=existing_partition,
            )
            if existing_partition is not None and _partition_is_reusable(
                root, existing_partition, plan
            ):
                verified_partitions += 1
                continue
            reason = "missing"
            if existing_partition is not None:
                if existing_partition.get("source_kind") != source_kind:
                    reason = "replace_with_completed_monthly_archive"
                elif source_kind == "daily_archives_current_month":
                    existing_end = datetime.fromisoformat(
                        cast(str, existing_partition["coverage_end"])
                    )
                    reason = (
                        "extend_current_month"
                        if existing_end < coverage_end
                        else "rebuild_invalid_partition"
                    )
                else:
                    reason = "rebuild_invalid_partition"
            source_plans = _source_plans(
                symbol,
                month,
                coverage_start,
                coverage_end,
                source_kind,
                archive_client,
                existing_partition,
            )
            planned = _PartitionPlan(
                symbol=symbol,
                dataset_id=cast(str, dataset["dataset_id"]),
                month=month,
                source_kind=source_kind,
                initial_month=month == _month_label(coverage.first_date),
                coverage_start=coverage_start,
                coverage_end=coverage_end,
                expected_rows=expected_rows,
                estimated_storage_bytes=estimated_storage_bytes,
                reason=reason,
                source_plans=source_plans,
                existing_partition=existing_partition,
            )
            symbol_pending.append(planned)
            pending_plans.append(planned)
            cast(list[str], dataset["pending_partition_months"]).append(month)

        preview_symbols.append(
            {
                "symbol": symbol,
                "dataset_id": dataset["dataset_id"],
                "first_available_date": coverage.first_date.isoformat(),
                "last_available_date": coverage.last_date.isoformat(),
                "pending_partitions": len(symbol_pending),
                "missing_source_objects": sum(len(item.source_plans) for item in symbol_pending),
                "estimated_download_bytes": sum(
                    sum(source.estimated_bytes for source in item.source_plans)
                    for item in symbol_pending
                ),
                "estimated_storage_bytes": sum(
                    item.estimated_storage_bytes for item in symbol_pending
                ),
                "plans": [
                    {
                        "month": item.month,
                        "source_kind": item.source_kind,
                        "reason": item.reason,
                        "coverage_start": item.coverage_start.isoformat(),
                        "coverage_end": item.coverage_end.isoformat(),
                        "expected_rows": item.expected_rows,
                        "estimated_download_bytes": sum(
                            source.estimated_bytes for source in item.source_plans
                        ),
                        "estimated_storage_bytes": item.estimated_storage_bytes,
                        "missing_source_objects": len(item.source_plans),
                        "source_labels": [source.label for source in item.source_plans],
                    }
                    for item in symbol_pending
                ],
            }
        )

    preview = {
        "preview_id": _sha256(
            {
                "schema_version": "gridlab.synchronized-production-preview.v1",
                "retrieved_at": retrieved_at.isoformat(),
                "plans": [
                    {
                        "symbol": plan.symbol,
                        "month": plan.month,
                        "source_kind": plan.source_kind,
                        "reason": plan.reason,
                        "coverage_start": plan.coverage_start.isoformat(),
                        "coverage_end": plan.coverage_end.isoformat(),
                        "sources": [asdict(source) for source in plan.source_plans],
                    }
                    for plan in pending_plans
                ],
            }
        ),
        "source_objects": sum(len(plan.source_plans) for plan in pending_plans),
        "estimated_download_bytes": sum(
            sum(source.estimated_bytes for source in plan.source_plans) for plan in pending_plans
        ),
        "estimated_storage_bytes": sum(plan.estimated_storage_bytes for plan in pending_plans),
        "pending_partitions": len(pending_plans),
        "verified_partitions": verified_partitions,
        "symbols": preview_symbols,
    }
    status = _build_status(
        datasets=datasets,
        sources=[production_source],
        preview=preview,
        retrieved_at=retrieved_at,
        blocking_reasons=sorted(set(blocking_reasons)),
    )
    _write_preview(root, status)
    return status


def _read_zip_rows(archive_bytes: bytes, expected_name: str, url: str) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            if names != [expected_name]:
                raise ProductionArchiveError(
                    f"archive must contain exactly {expected_name}; found {names}"
                )
            raw = archive.read(expected_name).decode("utf-8")
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError) as exc:
        raise ProductionArchiveError(f"corrupt source archive {url}") from exc
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        raise ProductionArchiveError(f"source archive is empty: {url}")
    return rows


def _read_source_records(
    source: _SourcePlan, archive_bytes: bytes
) -> tuple[list[dict[str, Any]], str, int, int]:
    expected_name = source.url.rsplit("/", 1)[-1].removesuffix(".zip") + ".csv"
    rows = _read_zip_rows(archive_bytes, expected_name, source.url)
    try:
        timestamps = [int(value) for row in rows for value in (row[0], row[6])]
    except (ValueError, IndexError) as exc:
        raise ProductionArchiveError(f"timestamp unit is invalid in {source.url}") from exc
    unit = validate_timestamp_unit(timestamps, source.coverage_start.date())
    records: list[dict[str, Any]] = []
    invalid = 0
    for source_row, row in enumerate(rows, start=1):
        try:
            if len(row) != 12:
                raise ProductionArchiveError("kline row must contain 12 fields")
            open_raw, close_raw = int(row[0]), int(row[6])
            resolution = 1_000_000 if unit == "microseconds" else 1_000
            if close_raw != open_raw + 60 * resolution - 1:
                raise ProductionArchiveError("close time does not match a complete 1m candle")
            opened = _timestamp(open_raw, unit)
            if not source.coverage_start <= opened < source.coverage_end:
                raise ProductionArchiveError("source row falls outside the partition boundary")
            open_, high, low, close = map(lambda value: _decimal(value, "price"), row[1:5])
            volume = _decimal(row[5], "volume")
            quote_volume = _decimal(row[7], "quote_volume")
            trade_count = int(row[8])
            taker_base = _decimal(row[9], "taker_buy_base_volume")
            taker_quote = _decimal(row[10], "taker_buy_quote_volume")
            if (
                min(open_, high, low, close) <= 0
                or high < max(open_, close)
                or low > min(open_, close)
                or min(volume, quote_volume, taker_base, taker_quote) < 0
                or trade_count < 0
            ):
                raise ProductionArchiveError("invalid OHLCV or trade values")
            records.append(
                {
                    "open_time": opened,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "close_time": _timestamp(close_raw, unit),
                    "quote_volume": quote_volume,
                    "trade_count": trade_count,
                    "taker_buy_base_volume": taker_base,
                    "taker_buy_quote_volume": taker_quote,
                    "source_sha256": source.expected_sha256,
                    "source_row": source_row,
                }
            )
        except (ProductionArchiveError, ValueError, IndexError):
            invalid += 1
    return records, unit, len(rows), invalid


def _sequence_identity(records: list[dict[str, Any]]) -> str:
    identity = [
        [
            record["open_time"].isoformat(),
            _canonical_decimal(record["open"]),
            _canonical_decimal(record["high"]),
            _canonical_decimal(record["low"]),
            _canonical_decimal(record["close"]),
            _canonical_decimal(record["volume"]),
        ]
        for record in records
    ]
    return _sha256(_canonical_json(identity))


def _partition_records_from_existing(
    root: Path, partition: Mapping[str, object]
) -> list[dict[str, Any]]:
    parquet_path = root / cast(str, partition["path"])
    return [cast(dict[str, Any], row) for row in pq.read_table(parquet_path).to_pylist()]


def _resolved_coverage_start(
    records: Sequence[Mapping[str, Any]], plan: _PartitionPlan
) -> datetime:
    if not records or not plan.initial_month:
        return plan.coverage_start
    first_observed = min(cast(datetime, record["open_time"]) for record in records)
    if (
        first_observed.date() == plan.coverage_start.date()
        and plan.coverage_start <= first_observed < plan.coverage_end
    ):
        return first_observed
    return plan.coverage_start


def _quality(records: list[dict[str, Any]], plan: _PartitionPlan, invalid: int) -> dict[str, int]:
    observed = [cast(datetime, record["open_time"]) for record in records]
    out_of_order = sum(left > right for left, right in zip(observed, observed[1:]))
    unique = set(observed)
    duplicates = len(observed) - len(unique)
    coverage_start = _resolved_coverage_start(records, plan)
    expected = {
        coverage_start + timedelta(minutes=index)
        for index in range(int((plan.coverage_end - coverage_start).total_seconds() // 60))
    }
    gaps = len(expected - unique)
    invalid += len(unique - expected)
    return {
        "rows": len(records),
        "gaps": gaps,
        "duplicates": duplicates,
        "out_of_order": out_of_order,
        "invalid_records": invalid,
    }


def _partition_target(root: Path, symbol: str, month: str, partition_id: str) -> Path:
    return _symbols_dir(root) / symbol / "partitions" / month / partition_id


def _write_partition(
    root: Path, plan: _PartitionPlan, payload: Mapping[str, Any]
) -> dict[str, object]:
    partition_id = cast(str, payload["partition_id"])
    target = _partition_target(root, plan.symbol, plan.month, partition_id)
    if target.exists():
        existing_partition = {
            "partition_id": partition_id,
            "dataset_id": payload["dataset_id"],
            "symbol": payload["symbol"],
            "month": payload["month"],
            "coverage_start": payload["coverage_start"],
            "coverage_end": payload["coverage_end"],
            "source_kind": payload["source_kind"],
            "row_count": payload["row_count"],
            "normalized_sha256": payload["normalized_sha256"],
            "path": str((target / "data.parquet").relative_to(root)),
            "manifest_path": str((target / "manifest.json").relative_to(root)),
            "verification_status": "verified",
            "active": True,
        }
        try:
            existing = _read_verified_partition_manifest(root, existing_partition)
            return existing | {"manifest_identity": cast(str, existing["manifest_sha256"])}
        except ProductionArchiveError:
            shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gridlab-partition-", dir=target.parent) as tmp:
        staging = Path(tmp) / partition_id
        staging.mkdir(parents=True, exist_ok=True)
        parquet_path = staging / "data.parquet"
        pq.write_table(
            pa.Table.from_pylist(
                cast(list[dict[str, Any]], payload["records"]),
                schema=_PARTITION_SCHEMA,
            ),
            parquet_path,
            compression="zstd",
            use_dictionary=False,
            version="2.6",
        )
        manifest = dict(payload)
        manifest["path"] = str((target / "data.parquet").relative_to(root))
        manifest["manifest_path"] = str((target / "manifest.json").relative_to(root))
        manifest["byte_size"] = parquet_path.stat().st_size
        manifest.pop("records", None)
        manifest["manifest_sha256"] = _sha256(_canonical_json(manifest))
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.replace(target)
    return cast(
        dict[str, object],
        json.loads((target / "manifest.json").read_text(encoding="utf-8")),
    )


def _acquire_partition(
    root: Path,
    plan: _PartitionPlan,
    archive_client: ProductionArchiveClient,
) -> dict[str, object]:
    records: list[dict[str, Any]] = []
    source_units: list[str] = []
    source_evidence: list[dict[str, object]] = []
    if plan.source_kind == "daily_archives_current_month" and plan.existing_partition is not None:
        existing_end = datetime.fromisoformat(cast(str, plan.existing_partition["coverage_end"]))
        if existing_end > plan.coverage_start:
            records.extend(_partition_records_from_existing(root, plan.existing_partition))
            source_units.extend(cast(list[str], plan.existing_partition.get("timestamp_units", [])))
            source_evidence.extend(
                cast(list[dict[str, object]], plan.existing_partition.get("source_evidence", []))
            )
    invalid = 0
    for source in plan.source_plans:
        current_checksum = _retry(
            lambda: archive_client.checksum(source.checksum_url).strip().lower(),
            f"official checksum {plan.symbol} {source.label}",
        )
        if current_checksum != source.expected_sha256:
            raise ProductionArchiveError(
                f"checksum drift for {plan.symbol} {source.label}: "
                f"expected {source.expected_sha256}, observed {current_checksum}"
            )
        archive_bytes = _retry(
            lambda: archive_client.download(source.url),
            f"download {plan.symbol} {source.label}",
        )
        observed_checksum = _sha256(archive_bytes)
        if observed_checksum != source.expected_sha256:
            raise ProductionArchiveError(
                f"checksum mismatch for {plan.symbol} {source.label}: "
                f"expected {source.expected_sha256}, observed {observed_checksum}"
            )
        source_records, unit, source_rows, source_invalid = _read_source_records(
            source,
            archive_bytes,
        )
        records.extend(source_records)
        source_units.append(unit)
        invalid += source_invalid
        source_evidence.append(
            {
                "label": source.label,
                "source_kind": source.source_kind,
                "url": source.url,
                "checksum_url": source.checksum_url,
                "expected_sha256": source.expected_sha256,
                "observed_sha256": observed_checksum,
                "estimated_bytes": source.estimated_bytes,
                "rows": source_rows,
                "coverage_start": source.coverage_start.isoformat(),
                "coverage_end": source.coverage_end.isoformat(),
                "timestamp_unit": unit,
            }
        )
    records.sort(
        key=lambda record: (
            record["open_time"],
            record["source_sha256"],
            record["source_row"],
        )
    )
    quality = _quality(records, plan, invalid)
    failures = {key: value for key, value in quality.items() if key != "rows" and value}
    if failures:
        detail = ", ".join(f"{key}={value}" for key, value in failures.items())
        raise ProductionArchiveError(f"partition continuity admission failed: {detail}")
    coverage_start = _resolved_coverage_start(records, plan)
    sequence_sha256 = _sequence_identity(records)
    with tempfile.TemporaryDirectory(prefix="gridlab-partition-hash-", dir=root) as tmp:
        temp_parquet = Path(tmp) / "data.parquet"
        pq.write_table(
            pa.Table.from_pylist(records, schema=_PARTITION_SCHEMA),
            temp_parquet,
            compression="zstd",
            use_dictionary=False,
            version="2.6",
        )
        normalized_sha256 = _sha256(temp_parquet.read_bytes())
    identity = {
        "schema_version": "gridlab.production-archive-partition-identity.v1",
        "dataset_id": plan.dataset_id,
        "symbol": plan.symbol,
        "month": plan.month,
        "coverage_start": coverage_start.isoformat(),
        "coverage_end": plan.coverage_end.isoformat(),
        "source_sha256": [source["observed_sha256"] for source in source_evidence],
        "normalized_sha256": normalized_sha256,
        "rows": len(records),
        "ordering": _PARTITION_ORDERING,
        "normalizer": _NORMALIZER,
        "sequence_sha256": sequence_sha256,
    }
    provisional_manifest: dict[str, Any] = {
        "schema_version": "gridlab.production-archive-partition.v1",
        "archive_id": ARCHIVE_ID,
        "dataset_id": plan.dataset_id,
        "symbol": plan.symbol,
        "quote_asset": QUOTE_ASSET,
        "interval": INTERVAL,
        "month": plan.month,
        "coverage_start": coverage_start.isoformat(),
        "coverage_end": plan.coverage_end.isoformat(),
        "source_kind": plan.source_kind,
        "row_count": len(records),
        "ordering": list(_PARTITION_ORDERING),
        "normalization_identity": _NORMALIZER,
        "normalized_sha256": normalized_sha256,
        "source_urls": [source["url"] for source in source_evidence],
        "source_checksums": [source["observed_sha256"] for source in source_evidence],
        "timestamp_units": sorted(set(source_units)),
        "source_evidence": source_evidence,
        "quality": quality,
        "schema": _schema_manifest(),
        "verification_status": "verified",
        "active": True,
        "correction_findings": [],
        "gap_findings": [],
        "sequence_sha256": sequence_sha256,
        "records": records,
        "partition_id": _sha256(_canonical_json(identity)),
    }
    manifest = _write_partition(root, plan, provisional_manifest)
    return {key: value for key, value in manifest.items() if key != "manifest_sha256"} | {
        "manifest_identity": cast(str, manifest["manifest_sha256"])
    }


def synchronize_synchronized_production_archive(
    catalog_client: ProductionArchiveCatalogClient,
    archive_client: ProductionArchiveClient,
    root: Path,
    *,
    retrieved_at: datetime,
    max_workers: int = MAX_SYNC_WORKERS,
) -> dict[str, object]:
    preview_status = _read_latest_preview(root)
    if _read_index(root) is not None or preview_status is None:
        preview_status = preview_synchronized_production_archive(
            catalog_client,
            archive_client,
            root,
            retrieved_at=retrieved_at,
        )
    datasets = cast(list[dict[str, object]], preview_status["datasets"])
    preview = cast(dict[str, object], preview_status["preview"])
    dataset_lookup = {cast(str, item["symbol"]): item for item in datasets}
    plans: list[_PartitionPlan] = []
    for symbol_preview in cast(list[dict[str, object]], preview["symbols"]):
        dataset = dataset_lookup[cast(str, symbol_preview["symbol"])]
        existing_partitions = {
            cast(str, item["month"]): cast(dict[str, object], item)
            for item in cast(list[dict[str, object]], dataset["partitions"])
            if item.get("active") is True
        }
        for raw_plan in cast(list[dict[str, object]], symbol_preview["plans"]):
            month = cast(str, raw_plan["month"])
            coverage_start = datetime.fromisoformat(cast(str, raw_plan["coverage_start"]))
            coverage_end = datetime.fromisoformat(cast(str, raw_plan["coverage_end"]))
            source_kind = cast(str, raw_plan["source_kind"])
            coverage = cast(dict[str, object], dataset["coverage"])
            plans.append(
                _PartitionPlan(
                    symbol=cast(str, dataset["symbol"]),
                    dataset_id=cast(str, dataset["dataset_id"]),
                    month=month,
                    source_kind=source_kind,
                    initial_month=month
                    == _month_label(date.fromisoformat(cast(str, coverage["first_date"]))),
                    coverage_start=coverage_start,
                    coverage_end=coverage_end,
                    expected_rows=int(cast(int | str, raw_plan["expected_rows"])),
                    estimated_storage_bytes=int(
                        cast(int | str, raw_plan["estimated_storage_bytes"])
                    ),
                    reason=cast(str, raw_plan["reason"]),
                    source_plans=_source_plans(
                        cast(str, dataset["symbol"]),
                        month,
                        coverage_start,
                        coverage_end,
                        source_kind,
                        archive_client,
                        existing_partitions.get(month),
                    ),
                    existing_partition=existing_partitions.get(month),
                )
            )
    blocking_reasons = list(cast(list[str], preview_status["blocking_reasons"]))
    if plans:
        workers = max(1, min(max_workers, len(plans)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                (executor.submit(_acquire_partition, root, plan, archive_client), plan)
                for plan in plans
            ]
            for future, plan in futures:
                try:
                    manifest = future.result()
                except Exception as exc:  # noqa: BLE001
                    blocking_reasons.append(f"{plan.symbol} {plan.month} blocked: {exc}")
                    continue
                dataset = dataset_lookup[plan.symbol]
                partitions = cast(list[dict[str, object]], dataset["partitions"])
                for item in partitions:
                    if item.get("month") == plan.month and item.get("active") is True:
                        item["active"] = False
                partitions.append(manifest)
                _write_index(
                    root,
                    _build_status(
                        datasets=datasets,
                        sources=cast(list[dict[str, object]], preview_status["sources"]),
                        preview=preview,
                        retrieved_at=retrieved_at,
                        blocking_reasons=sorted(set(blocking_reasons)),
                    ),
                )
    final_status = preview_synchronized_production_archive(
        catalog_client,
        archive_client,
        root,
        retrieved_at=retrieved_at,
    )
    final_status["blocking_reasons"] = sorted(
        set(cast(list[str], final_status["blocking_reasons"])) | set(blocking_reasons)
    )
    final_status["status"] = (
        "blocked" if final_status["blocking_reasons"] else final_status["status"]
    )
    _write_index(root, final_status)
    return final_status


def _dataset_by_id(index: Mapping[str, object], dataset_id: str) -> Mapping[str, object]:
    for dataset in cast(list[dict[str, object]], index["datasets"]):
        if dataset["dataset_id"] == dataset_id:
            return dataset
    raise ProductionArchiveError(
        f"dataset identity not found in synchronized archive: {dataset_id}"
    )


def _range_is_covered(ranges: Iterable[Mapping[str, str]], start: datetime, end: datetime) -> bool:
    covered_until = start
    for range_start, range_end in sorted(
        (
            (
                datetime.fromisoformat(cast(str, current["start"])),
                datetime.fromisoformat(cast(str, current["end"])),
            )
            for current in ranges
        ),
        key=lambda pair: pair[0],
    ):
        if range_end <= covered_until:
            continue
        if range_start > covered_until:
            return False
        covered_until = range_end
        if covered_until >= end:
            return True
    return covered_until >= end


def create_production_snapshot_manifest(
    root: Path,
    dataset_id: str,
    start: datetime,
    end: datetime,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    if start.tzinfo is None or start.utcoffset() != timedelta(0):
        raise ValueError("start must be timezone-aware UTC")
    if end.tzinfo is None or end.utcoffset() != timedelta(0):
        raise ValueError("end must be timezone-aware UTC")
    if end <= start:
        raise ValueError("end must be after start")
    index = _read_index(root)
    if index is None:
        raise ProductionArchiveError("synchronized production archive is not initialized")
    dataset = _dataset_by_id(index, dataset_id)
    verified_ranges = cast(list[dict[str, str]], dataset["verified_ranges"])
    if not _range_is_covered(verified_ranges, start, end):
        raise ProductionArchiveError(
            f"requested range {start.isoformat()} to {end.isoformat()} "
            "is not fully covered by verified local partitions"
        )
    partitions = [
        item
        for item in cast(list[dict[str, object]], dataset["partitions"])
        if item.get("active") is True
        and datetime.fromisoformat(cast(str, item["coverage_end"])) > start
        and datetime.fromisoformat(cast(str, item["coverage_start"])) < end
    ]
    if not partitions:
        raise ProductionArchiveError("requested range has no covering partitions")
    verified_partitions = [
        _read_verified_partition_manifest(
            root,
            item,
            expected_dataset_id=dataset_id,
            expected_symbol=cast(str, dataset["symbol"]),
        )
        for item in partitions
    ]
    partition_paths = [str(root / cast(str, item["path"])) for item in verified_partitions]
    table = ds.dataset(partition_paths, format="parquet").to_table(
        filter=(ds.field("open_time") >= pa.scalar(start, type=pa.timestamp("us", tz="UTC")))
        & (ds.field("open_time") < pa.scalar(end, type=pa.timestamp("us", tz="UTC")))
    )
    records = table.to_pylist()
    records.sort(key=lambda row: (row["open_time"], row["source_sha256"], row["source_row"]))
    expected_rows = int((end - start).total_seconds() // 60)
    if len(records) != expected_rows:
        raise ProductionArchiveError(
            f"requested range is not fully covered locally: expected {expected_rows} candles, "
            f"found {len(records)}"
        )
    candle_sequence_sha256 = _sequence_identity(records)
    normalized_sha256 = _sha256(
        {
            "schema_version": "gridlab.production-archive-snapshot-normalization.v1",
            "dataset_id": dataset_id,
            "requested_range": {
                "start_inclusive": start.isoformat(),
                "end_exclusive": end.isoformat(),
            },
            "partition_identities": [item["partition_id"] for item in verified_partitions],
            "candle_sequence_sha256": candle_sequence_sha256,
        }
    )
    snapshot = {
        "schema_version": "gridlab.production-archive-snapshot.v1",
        "archive_id": ARCHIVE_ID,
        "dataset_id": dataset_id,
        "symbol": dataset["symbol"],
        "quote_asset": QUOTE_ASSET,
        "interval": INTERVAL,
        "source_provider": "official Binance public archive",
        "history_environment": "production",
        "requested_range": {
            "start_inclusive": start.isoformat(),
            "end_exclusive": end.isoformat(),
        },
        "coverage": {
            "first_verified_open_time": records[0]["open_time"].isoformat(),
            "last_verified_open_time": records[-1]["open_time"].isoformat(),
        },
        "retrieved_at": retrieved_at.isoformat(),
        "candle_count": len(records),
        "normalized_sha256": normalized_sha256,
        "candle_sequence_sha256": candle_sequence_sha256,
        "partition_identities": [item["partition_id"] for item in verified_partitions],
        "partitions": [
            {
                "month": item["month"],
                "partition_id": item["partition_id"],
                "manifest_identity": item["manifest_sha256"],
                "path": item["path"],
                "manifest_path": item["manifest_path"],
                "normalized_sha256": item["normalized_sha256"],
                "row_count": item["row_count"],
                "coverage_start": item["coverage_start"],
                "coverage_end": item["coverage_end"],
                "source_kind": item["source_kind"],
                "source_urls": item["source_urls"],
            }
            for item in verified_partitions
        ],
    }
    snapshot["manifest_sha256"] = _sha256(_canonical_json(snapshot))
    directory = _snapshots_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot['manifest_sha256']}.json"
    if not path.exists():
        _write_json_atomic(path, snapshot)
    snapshot["manifest_path"] = str(path)
    return snapshot


def load_production_snapshot_candles(manifest_path: Path) -> list[Candle]:
    manifest = cast(dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8")))
    manifest_identity = cast(str, manifest.pop("manifest_sha256"))
    if _sha256(_canonical_json(manifest)) != manifest_identity:
        raise ProductionArchiveError("snapshot manifest checksum mismatch")
    manifest["manifest_sha256"] = manifest_identity
    start = datetime.fromisoformat(
        cast(dict[str, str], manifest["requested_range"])["start_inclusive"]
    )
    end = datetime.fromisoformat(cast(dict[str, str], manifest["requested_range"])["end_exclusive"])
    root = manifest_path.parent.parent
    verified_partitions = [
        _read_verified_partition_manifest(
            root,
            partition,
            expected_dataset_id=cast(str, manifest["dataset_id"]),
            expected_symbol=cast(str, manifest["symbol"]),
        )
        for partition in cast(list[dict[str, object]], manifest["partitions"])
    ]
    partition_paths = [
        str(root / cast(str, partition["path"])) for partition in verified_partitions
    ]
    table = ds.dataset(partition_paths, format="parquet").to_table(
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "source_sha256",
            "source_row",
        ],
        filter=(ds.field("open_time") >= pa.scalar(start, type=pa.timestamp("us", tz="UTC")))
        & (ds.field("open_time") < pa.scalar(end, type=pa.timestamp("us", tz="UTC"))),
    )
    rows = table.to_pylist()
    rows.sort(key=lambda row: (row["open_time"], row["source_sha256"], row["source_row"]))
    expected_rows = int((end - start).total_seconds() // 60)
    if len(rows) != expected_rows:
        raise ProductionArchiveError(
            f"snapshot requested {expected_rows} candles but found {len(rows)} locally"
        )
    if len(rows) != int(cast(int | str, manifest["candle_count"])):
        raise ProductionArchiveError("snapshot candle count drifted from the manifest")
    candle_sequence_sha256 = _sequence_identity(rows)
    if candle_sequence_sha256 != manifest.get("candle_sequence_sha256"):
        raise ProductionArchiveError("snapshot candle sequence checksum mismatch")
    normalized_sha256 = _sha256(
        {
            "schema_version": "gridlab.production-archive-snapshot-normalization.v1",
            "dataset_id": manifest["dataset_id"],
            "requested_range": cast(dict[str, str], manifest["requested_range"]),
            "partition_identities": [
                partition["partition_id"] for partition in verified_partitions
            ],
            "candle_sequence_sha256": candle_sequence_sha256,
        }
    )
    if normalized_sha256 != manifest.get("normalized_sha256"):
        raise ProductionArchiveError("snapshot normalization checksum mismatch")
    return [
        Candle(
            timestamp=row["open_time"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            index=index,
        )
        for index, row in enumerate(rows)
    ]

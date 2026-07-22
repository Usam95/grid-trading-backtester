"""Manifested acquisition of official Binance Spot candle archives.

The public functions in this module form the evidence boundary: callers preview
the exact source objects first, then admission verifies those immutable
expectations before a normalized dataset can exist.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol, TypedDict

import pyarrow as pa
import pyarrow.parquet as pq

from gridlab.core.models import Candle


BINANCE_ARCHIVE_ROOT = "https://data.binance.vision/data"
MAX_PREVIEW_DAYS = 7
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = re.compile(r"^[A-Z0-9]{5,20}$")
_MICROSECOND_ERA = date(2025, 1, 1)
_NORMALIZER = "gridlab.binance-spot-kline-parquet.v1"
_DECIMAL = pa.decimal128(38, 18)
_PARQUET_SCHEMA = pa.schema(
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


class DataAdmissionError(ValueError):
    """Source evidence failed a frozen admission rule."""


class _KlineRecord(TypedDict):
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: datetime
    quote_volume: Decimal
    trade_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal
    source_sha256: str
    source_row: int


class ArchiveClient(Protocol):
    """Network boundary used by previews and downloads."""

    def checksum(self, url: str) -> str: ...

    def content_length(self, url: str) -> int: ...

    def download(self, url: str) -> bytes: ...


class OfficialBinanceArchiveClient:
    """Bounded HTTP client for the fixed official public-archive host."""

    max_archive_bytes = 64 * 1024 * 1024

    @staticmethod
    def _request(url: str, *, method: str = "GET") -> urllib.request.Request:
        if not url.startswith(f"{BINANCE_ARCHIVE_ROOT}/spot/daily/klines/"):
            raise ValueError("archive URL is outside the official Binance Spot root")
        return urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": "gridlab-production-data/1.0"},
        )

    def checksum(self, url: str) -> str:
        try:
            with urllib.request.urlopen(self._request(url), timeout=20) as response:  # noqa: S310
                text = response.read(1024).decode("ascii").strip()
        except (OSError, UnicodeDecodeError, urllib.error.URLError) as exc:
            raise DataAdmissionError(f"missing official checksum evidence: {url}") from exc
        parts = text.split()
        if not parts or not _SHA256.fullmatch(parts[0].lower()):
            raise DataAdmissionError(f"corrupt official checksum evidence: {url}")
        return parts[0].lower()

    def content_length(self, url: str) -> int:
        try:
            with urllib.request.urlopen(  # noqa: S310
                self._request(url, method="HEAD"), timeout=20
            ) as response:
                length = int(response.headers["Content-Length"])
        except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError) as exc:
            raise DataAdmissionError(f"missing official archive metadata: {url}") from exc
        if length <= 0 or length > self.max_archive_bytes:
            raise DataAdmissionError(f"official archive size is outside the bounded limit: {url}")
        return length

    def download(self, url: str) -> bytes:
        try:
            with urllib.request.urlopen(self._request(url), timeout=30) as response:  # noqa: S310
                data = response.read(self.max_archive_bytes + 1)
        except (OSError, urllib.error.URLError) as exc:
            raise DataAdmissionError(f"missing official source archive: {url}") from exc
        if len(data) > self.max_archive_bytes:
            raise DataAdmissionError(f"official archive exceeded the bounded limit: {url}")
        return data


@dataclass(frozen=True, slots=True)
class ArchiveRequest:
    symbol: str
    interval: str
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        symbol = self.symbol.upper()
        object.__setattr__(self, "symbol", symbol)
        if not _SYMBOL.fullmatch(symbol):
            raise ValueError("symbol must be 5-20 uppercase ASCII letters or digits")
        if self.interval != "1m":
            raise ValueError("the production-data tracer accepts only Binance Spot 1m")
        for name, value in (("start", self.start), ("end", self.end)):
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError(f"{name} must be timezone-aware UTC")
            if value.time() != datetime.min.time():
                raise ValueError(f"{name} must be aligned to a UTC day boundary")
        days = (self.end - self.start).days
        if self.end <= self.start or days < 1 or days > MAX_PREVIEW_DAYS:
            raise ValueError(f"range must contain 1-{MAX_PREVIEW_DAYS} complete UTC days")


@dataclass(frozen=True, slots=True)
class ArchiveSource:
    date: str
    url: str
    checksum_url: str
    expected_sha256: str
    estimated_bytes: int


@dataclass(frozen=True, slots=True)
class ArchivePreview:
    preview_id: str
    venue: str
    market: str
    symbol: str
    interval: str
    start: datetime
    end: datetime
    estimated_bytes: int
    sources: tuple[ArchiveSource, ...]


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _preview_identity(
    venue: str,
    market: str,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    sources: list[ArchiveSource] | tuple[ArchiveSource, ...],
) -> str:
    identity = {
        "venue": venue,
        "market": market,
        "symbol": symbol,
        "interval": interval,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sources": [asdict(source) for source in sources],
    }
    return _sha256(_canonical_json(identity))


def preview_binance_archive(request: ArchiveRequest, client: ArchiveClient) -> ArchivePreview:
    """Resolve official checksum sidecars and sizes without downloading archives."""
    sources: list[ArchiveSource] = []
    day = request.start
    while day < request.end:
        date = day.date().isoformat()
        name = f"{request.symbol}-{request.interval}-{date}.zip"
        url = f"{BINANCE_ARCHIVE_ROOT}/spot/daily/klines/{request.symbol}/{request.interval}/{name}"
        checksum_url = f"{url}.CHECKSUM"
        checksum = client.checksum(checksum_url).strip().lower()
        if not _SHA256.fullmatch(checksum):
            raise ValueError(f"official checksum is invalid for {name}")
        size = client.content_length(url)
        if size <= 0:
            raise ValueError(f"official content length is invalid for {name}")
        sources.append(ArchiveSource(date, url, checksum_url, checksum, size))
        day += timedelta(days=1)

    return ArchivePreview(
        preview_id=_preview_identity(
            "binance",
            "spot-production-archive",
            request.symbol,
            request.interval,
            request.start,
            request.end,
            sources,
        ),
        venue="binance",
        market="spot-production-archive",
        symbol=request.symbol,
        interval=request.interval,
        start=request.start.astimezone(timezone.utc),
        end=request.end.astimezone(timezone.utc),
        estimated_bytes=sum(source.estimated_bytes for source in sources),
        sources=tuple(sources),
    )


def validate_timestamp_unit(values: list[int], archive_date: date) -> str:
    """Validate Binance's documented Spot millisecond/microsecond archive eras."""
    if not values:
        raise DataAdmissionError("timestamp unit cannot be established from no values")
    widths = {len(str(abs(value))) for value in values if isinstance(value, int)}
    if len(widths) != 1 or len(values) != sum(isinstance(value, int) for value in values):
        raise DataAdmissionError("timestamp unit is mixed or invalid")
    width = widths.pop()
    actual = {13: "milliseconds", 16: "microseconds"}.get(width)
    expected = "microseconds" if archive_date >= _MICROSECOND_ERA else "milliseconds"
    if actual != expected:
        raise DataAdmissionError(
            f"timestamp unit {actual or 'ambiguous'} conflicts with {expected} archive era"
        )
    return expected


def _timestamp(value: int, unit: str) -> datetime:
    divisor = 1_000_000 if unit == "microseconds" else 1_000
    seconds, remainder = divmod(value, divisor)
    microseconds = remainder if unit == "microseconds" else remainder * 1_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc) + timedelta(microseconds=microseconds)


def _decimal(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise DataAdmissionError(f"invalid decimal value {value!r}") from exc
    exponent = number.as_tuple().exponent
    if not number.is_finite() or not isinstance(exponent, int) or max(0, -exponent) > 18:
        raise DataAdmissionError(f"invalid decimal precision {value!r}")
    return number


def _canonical_decimal(value: Decimal) -> str:
    return format(value, ".18f")


def _schema_manifest() -> list[dict[str, object]]:
    return [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in _PARQUET_SCHEMA
    ]


def _read_source(
    source: ArchiveSource, archive_bytes: bytes
) -> tuple[list[_KlineRecord], str, int, int]:
    expected_name = source.url.rsplit("/", 1)[-1].removesuffix(".zip") + ".csv"
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            if names != [expected_name]:
                raise DataAdmissionError(
                    f"archive must contain exactly {expected_name}; found {names}"
                )
            raw = archive.read(expected_name).decode("utf-8")
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError) as exc:
        raise DataAdmissionError(f"corrupt source archive {source.url}") from exc

    import csv

    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        raise DataAdmissionError(f"source archive is empty: {source.url}")
    try:
        timestamps = [int(value) for row in rows for value in (row[0], row[6])]
    except (ValueError, IndexError) as exc:
        raise DataAdmissionError("timestamp unit is invalid in source rows") from exc
    unit = validate_timestamp_unit(timestamps, date.fromisoformat(source.date))
    records: list[_KlineRecord] = []
    invalid = 0
    for source_row, row in enumerate(rows, start=1):
        try:
            if len(row) != 12:
                raise DataAdmissionError("kline row must contain 12 fields")
            open_raw, close_raw = int(row[0]), int(row[6])
            resolution = 1_000_000 if unit == "microseconds" else 1_000
            if close_raw != open_raw + 60 * resolution - 1:
                raise DataAdmissionError("close time does not match a complete 1m candle")
            open_, high, low, close = map(_decimal, row[1:5])
            volume = _decimal(row[5])
            quote_volume = _decimal(row[7])
            trade_count = int(row[8])
            taker_base, taker_quote = map(_decimal, row[9:11])
            if (
                min(open_, high, low, close) <= 0
                or high < max(open_, close)
                or low > min(open_, close)
                or min(volume, quote_volume, taker_base, taker_quote) < 0
                or trade_count < 0
            ):
                raise DataAdmissionError("invalid OHLCV or trade values")
            records.append(
                {
                    "open_time": _timestamp(open_raw, unit),
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
        except (DataAdmissionError, ValueError, IndexError):
            invalid += 1
    return records, unit, len(rows), invalid


def _quality(records: list[_KlineRecord], preview: ArchivePreview, invalid: int) -> dict[str, int]:
    observed = [record["open_time"] for record in records]
    out_of_order = sum(left > right for left, right in zip(observed, observed[1:]))
    unique = set(observed)
    duplicates = len(observed) - len(unique)
    expected: set[datetime] = set()
    cursor = preview.start
    while cursor < preview.end:
        expected.add(cursor)
        cursor += timedelta(minutes=1)
    gaps = len(expected - unique)
    invalid += len(unique - expected)
    return {
        "rows": len(records),
        "gaps": gaps,
        "duplicates": duplicates,
        "out_of_order": out_of_order,
        "invalid_records": invalid,
    }


def acquire_binance_archive(
    preview: ArchivePreview,
    client: ArchiveClient,
    destination: Path,
    *,
    retrieved_at: datetime,
) -> dict[str, object]:
    """Verify, normalize, and atomically admit one bounded archive preview."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
        raise ValueError("retrieved_at must be timezone-aware UTC")
    expected_preview_id = _preview_identity(
        preview.venue,
        preview.market,
        preview.symbol,
        preview.interval,
        preview.start,
        preview.end,
        preview.sources,
    )
    if expected_preview_id != preview.preview_id:
        raise DataAdmissionError("download preview identity mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    records: list[_KlineRecord] = []
    source_units: list[str] = []
    source_evidence: list[dict[str, object]] = []
    verified_archives: list[tuple[str, bytes, str]] = []
    invalid = 0

    for source in preview.sources:
        current_checksum = client.checksum(source.checksum_url).strip().lower()
        if current_checksum != source.expected_sha256:
            raise DataAdmissionError(
                f"replaced source evidence: expected {source.expected_sha256}, "
                f"official sidecar now states {current_checksum}"
            )
        archive_bytes = client.download(source.url)
        observed_checksum = _sha256(archive_bytes)
        if observed_checksum != source.expected_sha256:
            raise DataAdmissionError(
                f"checksum mismatch for {source.url}: expected {source.expected_sha256}, "
                f"observed {observed_checksum}"
            )
        source_records, unit, source_rows, source_invalid = _read_source(source, archive_bytes)
        records.extend(source_records)
        source_units.append(unit)
        invalid += source_invalid
        name = source.url.rsplit("/", 1)[-1]
        verified_archives.append((name, archive_bytes, observed_checksum))
        source_evidence.append(
            {
                **asdict(source),
                "observed_sha256": observed_checksum,
                "retrieved_at": retrieved_at.isoformat(),
                "rows": source_rows,
                "archive_path": f"source/{name}",
                "checksum_path": f"source/{name}.CHECKSUM",
                "timestamp_unit": unit,
            }
        )

    quality = _quality(records, preview, invalid)
    failures = {key: value for key, value in quality.items() if key != "rows" and value}
    if failures:
        detail = ", ".join(f"{key}={value}" for key, value in failures.items())
        raise DataAdmissionError(f"dataset continuity admission failed: {detail}")
    records.sort(key=lambda record: record["open_time"])
    sequence_identity = [
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
    candle_sequence_sha256 = _sha256(_canonical_json(sequence_identity))

    with tempfile.TemporaryDirectory(prefix="gridlab-dataset-", dir=destination) as tmp:
        staging = Path(tmp)
        source_dir = staging / "source"
        source_dir.mkdir()
        for name, archive_bytes, checksum in verified_archives:
            (source_dir / name).write_bytes(archive_bytes)
            (source_dir / f"{name}.CHECKSUM").write_text(f"{checksum}  {name}\n", encoding="ascii")
        parquet_path = staging / "candles.parquet"
        table = pa.Table.from_pylist(records, schema=_PARQUET_SCHEMA)
        pq.write_table(
            table,
            parquet_path,
            compression="zstd",
            use_dictionary=False,
            version="2.6",
        )
        normalized_sha256 = _sha256(parquet_path.read_bytes())
        identity = {
            "schema_version": "gridlab.dataset-identity.v1",
            "venue": preview.venue,
            "market": preview.market,
            "symbol": preview.symbol,
            "interval": preview.interval,
            "start": preview.start.isoformat(),
            "end": preview.end.isoformat(),
            "source_sha256": [source.expected_sha256 for source in preview.sources],
            "normalized_sha256": normalized_sha256,
            "candle_sequence_sha256": candle_sequence_sha256,
            "normalizer": _NORMALIZER,
            "schema": _schema_manifest(),
        }
        dataset_id = _sha256(_canonical_json(identity))
        manifest: dict[str, object] = {
            "dataset_id": dataset_id,
            "schema_version": "gridlab.dataset-manifest.v1",
            "identity": identity,
            "venue": preview.venue,
            "market": "spot",
            "history_environment": "production",
            "source_provider": "official Binance public archive",
            "symbol": preview.symbol,
            "event_kind": "kline",
            "interval": preview.interval,
            "requested_range": {
                "start_inclusive": preview.start.isoformat(),
                "end_exclusive": preview.end.isoformat(),
            },
            "coverage": {
                "first_open_time": records[0]["open_time"].isoformat(),
                "last_open_time": records[-1]["open_time"].isoformat(),
            },
            "retrieved_at": retrieved_at.isoformat(),
            "sources": source_evidence,
            "timestamp": {
                "timezone": "UTC",
                "source_units": sorted(set(source_units)),
                "normalized_unit": "microseconds",
            },
            "quality": quality,
            "normalization": {
                "identity": _NORMALIZER,
                "format": "parquet",
                "path": "candles.parquet",
                "sha256": normalized_sha256,
                "rows": len(records),
                "schema": _schema_manifest(),
                "candle_sequence_sha256": candle_sequence_sha256,
                "ordering": ["open_time", "source_sha256", "source_row"],
                "parent_dataset_id": None,
                "resampling_rule": None,
            },
            "venue_rule_snapshot_id": None,
            "fee_snapshot_id": None,
        }
        manifest["manifest_sha256"] = _sha256(_canonical_json(manifest))
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        target = destination / dataset_id
        if target.exists():
            existing_manifest = target / "manifest.json"
            if not existing_manifest.is_file():
                raise DataAdmissionError(
                    f"existing content-identified dataset is incomplete: {dataset_id}"
                )
            load_manifested_candles(existing_manifest)
        else:
            staging.replace(target)
        manifest_path = target / "manifest.json"
        admitted = json.loads(manifest_path.read_text(encoding="utf-8"))
        admitted["manifest_path"] = str(manifest_path)
        return admitted


def load_manifested_candles(manifest_path: Path) -> list[Candle]:
    """Verify a manifested Parquet dataset and reproduce its ordered candles offline."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_identity = manifest.pop("manifest_sha256", None)
    if manifest_identity != _sha256(_canonical_json(manifest)):
        raise DataAdmissionError("dataset manifest checksum mismatch")
    manifest["manifest_sha256"] = manifest_identity
    expected_id = _sha256(_canonical_json(manifest["identity"]))
    if expected_id != manifest["dataset_id"]:
        raise DataAdmissionError("dataset manifest identity mismatch")
    for source in manifest["sources"]:
        source_path = manifest_path.parent / source["archive_path"]
        if not source_path.is_file():
            raise DataAdmissionError(f"source archive is missing: {source_path}")
        if _sha256(source_path.read_bytes()) != source["observed_sha256"]:
            raise DataAdmissionError(f"source archive checksum mismatch: {source_path}")
        checksum_path = manifest_path.parent / source["checksum_path"]
        if not checksum_path.is_file():
            raise DataAdmissionError(f"source checksum evidence is missing: {checksum_path}")
        checksum_text = checksum_path.read_text(encoding="ascii").split()
        if not checksum_text or checksum_text[0] != source["expected_sha256"]:
            raise DataAdmissionError(f"source checksum evidence mismatch: {checksum_path}")
    normalization = manifest["normalization"]
    parquet_path = manifest_path.parent / normalization["path"]
    if not parquet_path.is_file():
        raise DataAdmissionError("normalized Parquet is missing")
    if _sha256(parquet_path.read_bytes()) != normalization["sha256"]:
        raise DataAdmissionError("normalized Parquet checksum mismatch")
    table = pq.read_table(parquet_path)
    if _schema_manifest() != normalization["schema"] or table.schema != _PARQUET_SCHEMA:
        raise DataAdmissionError("normalized Parquet schema mismatch")
    rows = table.to_pylist()
    if len(rows) != normalization["rows"]:
        raise DataAdmissionError("normalized Parquet row count mismatch")
    sequence_identity = [
        [
            row["open_time"].isoformat(),
            _canonical_decimal(row["open"]),
            _canonical_decimal(row["high"]),
            _canonical_decimal(row["low"]),
            _canonical_decimal(row["close"]),
            _canonical_decimal(row["volume"]),
        ]
        for row in rows
    ]
    if _sha256(_canonical_json(sequence_identity)) != normalization["candle_sequence_sha256"]:
        raise DataAdmissionError("ordered candle sequence fingerprint mismatch")
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

"""Reproducible EUR research-catalog discovery across Binance environments."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol, Sequence, cast
from urllib.parse import urlencode


CATALOG_FILTERS = (
    "production_and_testnet",
    "TRADING",
    "spot_allowed",
    "LIMIT_MAKER",
    "quote_asset=EUR",
)
MAX_CATALOG_CLOCK_SKEW = timedelta(minutes=15)
MAX_CATALOG_SYMBOLS = 100
MAX_CATALOG_WORKERS = 8
MAX_ARCHIVE_LISTING_PAGES = 12
METRIC_QUANTUM = Decimal("0.00000001")


class CatalogAdmissionError(ValueError):
    """Official catalog or market-selection evidence is malformed or stale."""


@dataclass(frozen=True, slots=True)
class ArchiveCoverage:
    """Bounded official daily-archive availability for one symbol."""

    first_date: date
    last_date: date
    intervals: tuple[str, ...]
    known_gap_dates: tuple[date, ...]
    evidence_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.first_date > self.last_date:
            raise CatalogAdmissionError("archive coverage begins after it ends")
        if "1m" not in self.intervals:
            raise CatalogAdmissionError("archive coverage has no canonical 1m interval")
        if any(day < self.first_date or day > self.last_date for day in self.known_gap_dates):
            raise CatalogAdmissionError("archive gap falls outside discovered coverage")


@dataclass(frozen=True, slots=True)
class LiquidityEvidence:
    """Reproducible production-market context; never profitability evidence."""

    observed_days: int
    observed_start_date: date
    observed_end_date: date
    observed_at: datetime
    kline_source_url: str
    kline_payload_sha256: str
    ticker_source_url: str
    ticker_payload_sha256: str
    median_daily_quote_volume: Decimal
    median_daily_trade_count: Decimal
    annualized_realized_volatility: Decimal
    current_spread_bps: Decimal
    current_trade_count: int


@dataclass(frozen=True, slots=True)
class CatalogSource:
    environment: str
    url: str
    server_time: datetime


@dataclass(frozen=True, slots=True)
class EurCatalogSymbol:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    exchange_filters: Mapping[str, Mapping[str, object]]
    coverage: ArchiveCoverage
    liquidity: LiquidityEvidence
    liquidity_rank: int


@dataclass(frozen=True, slots=True)
class EurResearchCatalog:
    catalog_id: str
    retrieved_at: datetime
    quote_asset: str
    filters: tuple[str, ...]
    sources: tuple[CatalogSource, ...]
    symbols: tuple[EurCatalogSymbol, ...]


class BinanceCatalogClient(Protocol):
    """Specific official operations used by the catalog admission boundary."""

    production_url: str
    testnet_url: str
    archive_root: str
    market_root: str

    def production_exchange_info(self) -> Mapping[str, object]: ...

    def testnet_exchange_info(self) -> Mapping[str, object]: ...

    def daily_klines(self, symbol: str) -> Sequence[Sequence[object]]: ...

    def ticker(self, symbol: str) -> Mapping[str, object]: ...

    def archive_coverage(self, symbol: str, as_of: date) -> ArchiveCoverage: ...


class CatalogTransport(Protocol):
    """Bounded public HTTP transport, injectable at the network seam."""

    def get_json(self, url: str) -> object: ...

    def get_text(self, url: str) -> str: ...


class OfficialCatalogTransport:
    """Read only the official Binance public hosts with a fixed response cap."""

    allowed_roots = (
        "https://data-api.binance.vision/",
        "https://testnet.binance.vision/",
        "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision",
    )
    max_response_bytes = 32 * 1024 * 1024

    def _read(self, url: str) -> bytes:
        if not any(url.startswith(root) for root in self.allowed_roots):
            raise ValueError("catalog URL is outside the official Binance public roots")
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "gridlab-eur-catalog/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                data = response.read(self.max_response_bytes + 1)
        except (OSError, urllib.error.URLError) as exc:
            raise CatalogAdmissionError(f"official catalog evidence is unavailable: {url}") from exc
        if len(data) > self.max_response_bytes:
            raise CatalogAdmissionError(f"official catalog response exceeded its cap: {url}")
        return data

    def get_json(self, url: str) -> object:
        try:
            return json.loads(self._read(url))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CatalogAdmissionError(f"official JSON evidence is malformed: {url}") from exc

    def get_text(self, url: str) -> str:
        try:
            return self._read(url).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CatalogAdmissionError(f"official text evidence is malformed: {url}") from exc


class OfficialBinanceCatalogClient:
    """Specific bounded operations over Binance public catalog and archive APIs."""

    production_url = "https://data-api.binance.vision/api/v3/exchangeInfo"
    testnet_url = "https://testnet.binance.vision/api/v3/exchangeInfo"
    market_root = "https://data-api.binance.vision/api/v3"
    archive_root = "https://data.binance.vision/data"
    bucket_url = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"

    def __init__(self, transport: CatalogTransport | None = None) -> None:
        self.transport = transport or OfficialCatalogTransport()

    @staticmethod
    def _mapping(value: object, operation: str) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise CatalogAdmissionError(f"{operation} response is malformed")
        return cast(Mapping[str, object], value)

    def production_exchange_info(self) -> Mapping[str, object]:
        return self._mapping(
            self.transport.get_json(self.production_url),
            "production exchangeInfo",
        )

    def testnet_exchange_info(self) -> Mapping[str, object]:
        return self._mapping(
            self.transport.get_json(self.testnet_url),
            "Testnet exchangeInfo",
        )

    def daily_klines(self, symbol: str) -> Sequence[Sequence[object]]:
        query = urlencode({"symbol": symbol, "interval": "1d", "limit": 31})
        value = self.transport.get_json(f"{self.market_root}/klines?{query}")
        if not isinstance(value, list) or any(not isinstance(row, list) for row in value):
            raise CatalogAdmissionError(f"{symbol} daily kline response is malformed")
        return cast(list[list[object]], value)

    def ticker(self, symbol: str) -> Mapping[str, object]:
        query = urlencode({"symbol": symbol})
        return self._mapping(
            self.transport.get_json(f"{self.market_root}/ticker/24hr?{query}"),
            f"{symbol} ticker",
        )

    @staticmethod
    def _xml_values(text: str, name: str) -> list[str]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise CatalogAdmissionError("official archive listing is malformed") from exc
        values: list[str] = []
        nodes = root.findall(f".//{{*}}{name}")
        if not nodes:
            nodes = root.findall(f".//{name}")
        for node in nodes:
            if node.text:
                values.append(node.text)
        return values

    def _listing(self, **query: object) -> tuple[str, str]:
        url = f"{self.bucket_url}?{urlencode(query)}"
        return url, self.transport.get_text(url)

    @staticmethod
    def _archive_date(key: str, symbol: str) -> date | None:
        prefix = f"{symbol}-1m-"
        filename = key.rsplit("/", 1)[-1]
        if not filename.startswith(prefix) or not filename.endswith(".zip"):
            return None
        try:
            return date.fromisoformat(filename.removeprefix(prefix).removesuffix(".zip"))
        except ValueError:
            return None

    def archive_coverage(self, symbol: str, as_of: date) -> ArchiveCoverage:
        base_prefix = f"data/spot/daily/klines/{symbol}/"
        intervals_url, intervals_text = self._listing(
            **{"list-type": 2, "delimiter": "/", "prefix": base_prefix}
        )
        prefixes = self._xml_values(intervals_text, "Prefix")
        intervals = tuple(
            sorted(
                {
                    prefix.removesuffix("/").rsplit("/", 1)[-1]
                    for prefix in prefixes
                    if prefix.startswith(base_prefix)
                }
            )
        )
        minute_prefix = f"{base_prefix}1m/"
        dates: set[date] = set()
        evidence_urls = [intervals_url]
        continuation_token: str | None = None
        for _page in range(MAX_ARCHIVE_LISTING_PAGES):
            query: dict[str, object] = {
                "list-type": 2,
                "prefix": minute_prefix,
                "max-keys": 1000,
            }
            if continuation_token is not None:
                query["continuation-token"] = continuation_token
            page_url, page_text = self._listing(**query)
            evidence_urls.append(page_url)
            dates.update(
                day
                for key in self._xml_values(page_text, "Key")
                if (day := self._archive_date(key, symbol)) is not None and day < as_of
            )
            truncated = self._xml_values(page_text, "IsTruncated")
            if len(truncated) != 1 or truncated[0].lower() not in {"true", "false"}:
                raise CatalogAdmissionError(
                    f"{symbol} archive listing has invalid truncation evidence"
                )
            if truncated[0].lower() == "false":
                break
            tokens = self._xml_values(page_text, "NextContinuationToken")
            if not tokens or not tokens[-1]:
                raise CatalogAdmissionError(f"{symbol} archive listing has no continuation token")
            continuation_token = tokens[-1]
        else:
            raise CatalogAdmissionError(
                f"{symbol} archive listing exceeds {MAX_ARCHIVE_LISTING_PAGES} pages"
            )
        if not dates:
            raise CatalogAdmissionError(f"{symbol} has no complete daily 1m archive")
        first_date = min(dates)
        last_date = max(dates)
        expected = {
            first_date + timedelta(days=offset)
            for offset in range((last_date - first_date).days + 1)
        }
        return ArchiveCoverage(
            first_date=first_date,
            last_date=last_date,
            intervals=intervals,
            known_gap_dates=tuple(sorted(expected - dates)),
            evidence_urls=tuple(evidence_urls),
        )


def _decimal(value: object, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CatalogAdmissionError(f"{field} is not a decimal") from exc
    if not number.is_finite():
        raise CatalogAdmissionError(f"{field} is not finite")
    return number


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise CatalogAdmissionError(f"{field} is not an integer")
    try:
        return int(value)
    except ValueError as exc:
        raise CatalogAdmissionError(f"{field} is not an integer") from exc


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _exchange_symbols(
    payload: Mapping[str, object],
    *,
    environment: str,
    url: str,
    retrieved_at: datetime,
) -> tuple[dict[str, Mapping[str, object]], CatalogSource]:
    if payload.get("timezone") != "UTC":
        raise CatalogAdmissionError(f"{environment} exchangeInfo timezone is not UTC")
    try:
        server_time = datetime.fromtimestamp(
            _integer(payload["serverTime"], f"{environment} serverTime") / 1000,
            tz=retrieved_at.tzinfo,
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise CatalogAdmissionError(f"{environment} exchangeInfo serverTime is invalid") from exc
    if abs(retrieved_at - server_time) > MAX_CATALOG_CLOCK_SKEW:
        raise CatalogAdmissionError(f"{environment} exchangeInfo evidence is stale")
    raw_symbols = payload.get("symbols")
    if not isinstance(raw_symbols, list):
        raise CatalogAdmissionError(f"{environment} exchangeInfo symbols are invalid")
    symbols: dict[str, Mapping[str, object]] = {}
    for raw in raw_symbols:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("symbol"), str):
            raise CatalogAdmissionError(f"{environment} exchangeInfo contains a malformed symbol")
        symbol = raw["symbol"]
        if symbol in symbols:
            raise CatalogAdmissionError(
                f"{environment} exchangeInfo contains duplicate symbol {symbol}"
            )
        symbols[symbol] = raw
    return symbols, CatalogSource(environment, url, server_time)


def _eligible(raw: Mapping[str, object]) -> bool:
    order_types = raw.get("orderTypes")
    return (
        raw.get("quoteAsset") == "EUR"
        and raw.get("status") == "TRADING"
        and raw.get("isSpotTradingAllowed") is True
        and isinstance(order_types, list)
        and "LIMIT_MAKER" in order_types
    )


def _exchange_filters(raw: Mapping[str, object], symbol: str) -> dict[str, Mapping[str, object]]:
    filters = raw.get("filters")
    if not isinstance(filters, list):
        raise CatalogAdmissionError(f"{symbol} exchange filters are malformed")
    result: dict[str, Mapping[str, object]] = {}
    for item in filters:
        if not isinstance(item, Mapping) or not isinstance(item.get("filterType"), str):
            raise CatalogAdmissionError(f"{symbol} exchange filters are malformed")
        filter_type = item["filterType"]
        if filter_type in result:
            raise CatalogAdmissionError(f"{symbol} has duplicate {filter_type} filter")
        result[filter_type] = dict(item)
    for required in ("PRICE_FILTER", "LOT_SIZE", "NOTIONAL"):
        if required not in result:
            raise CatalogAdmissionError(f"{symbol} is missing required {required} filter")
    return result


def _liquidity(
    symbol: str,
    rows: Sequence[Sequence[object]],
    ticker: Mapping[str, object],
    retrieved_at: datetime,
    *,
    kline_source_url: str,
    ticker_source_url: str,
) -> LiquidityEvidence:
    complete: list[tuple[datetime, Decimal, Decimal, Decimal]] = []
    for row in rows:
        if len(row) != 12:
            raise CatalogAdmissionError(f"{symbol} daily kline must contain 12 fields")
        try:
            opened = datetime.fromtimestamp(
                _integer(row[0], f"{symbol} daily open time") / 1000,
                tz=retrieved_at.tzinfo,
            )
            closed = datetime.fromtimestamp(
                _integer(row[6], f"{symbol} daily close time") / 1000,
                tz=retrieved_at.tzinfo,
            )
        except (TypeError, ValueError, OSError) as exc:
            raise CatalogAdmissionError(f"{symbol} daily kline timestamp is invalid") from exc
        if closed >= retrieved_at:
            continue
        complete.append(
            (
                opened,
                _decimal(row[4], f"{symbol} daily close"),
                _decimal(row[7], f"{symbol} daily quote volume"),
                _decimal(row[8], f"{symbol} daily trade count"),
            )
        )
    complete = complete[-30:]
    if len(complete) != 30:
        raise CatalogAdmissionError(f"{symbol} requires 30 complete production days")
    if any(right[0] - left[0] != timedelta(days=1) for left, right in zip(complete, complete[1:])):
        raise CatalogAdmissionError(f"{symbol} daily liquidity evidence is discontinuous")
    quote_volumes = [row[2] for row in complete]
    trade_counts = [row[3] for row in complete]
    closes = [row[1] for row in complete]
    if min(quote_volumes) < 0 or min(trade_counts) < 0 or min(closes) <= 0:
        raise CatalogAdmissionError(f"{symbol} daily liquidity evidence is invalid")
    returns = [math.log(float(right / left)) for left, right in zip(closes, closes[1:])]
    volatility = statistics.pstdev(returns) * math.sqrt(365) if returns else 0.0
    bid = _decimal(ticker.get("bidPrice"), f"{symbol} bid price")
    ask = _decimal(ticker.get("askPrice"), f"{symbol} ask price")
    if bid <= 0 or ask < bid:
        raise CatalogAdmissionError(f"{symbol} ticker spread is invalid")
    midpoint = (bid + ask) / 2
    try:
        current_trade_count = _integer(ticker["count"], f"{symbol} ticker trade count")
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogAdmissionError(f"{symbol} ticker trade count is invalid") from exc
    if current_trade_count < 0:
        raise CatalogAdmissionError(f"{symbol} ticker trade count is invalid")
    return LiquidityEvidence(
        observed_days=30,
        observed_start_date=complete[0][0].date(),
        observed_end_date=complete[-1][0].date(),
        observed_at=retrieved_at,
        kline_source_url=kline_source_url,
        kline_payload_sha256=_sha256(rows),
        ticker_source_url=ticker_source_url,
        ticker_payload_sha256=_sha256(ticker),
        median_daily_quote_volume=Decimal(statistics.median(quote_volumes)),
        median_daily_trade_count=Decimal(statistics.median(trade_counts)),
        annualized_realized_volatility=Decimal(str(volatility)).quantize(METRIC_QUANTUM),
        current_spread_bps=((ask - bid) / midpoint * Decimal(10_000)).quantize(METRIC_QUANTUM),
        current_trade_count=current_trade_count,
    )


def discover_eur_catalog(
    client: BinanceCatalogClient,
    *,
    retrieved_at: datetime,
) -> EurResearchCatalog:
    """Admit a dated, fingerprinted EUR catalog from bounded official evidence."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() != timedelta(0):
        raise ValueError("retrieved_at must be timezone-aware UTC")
    production, production_source = _exchange_symbols(
        client.production_exchange_info(),
        environment="production",
        url=client.production_url,
        retrieved_at=retrieved_at,
    )
    testnet, testnet_source = _exchange_symbols(
        client.testnet_exchange_info(),
        environment="testnet",
        url=client.testnet_url,
        retrieved_at=retrieved_at,
    )
    candidates: list[str] = []
    for symbol in sorted(production.keys() & testnet.keys()):
        production_symbol = production[symbol]
        testnet_symbol = testnet[symbol]
        if not (_eligible(production_symbol) and _eligible(testnet_symbol)):
            continue
        if production_symbol.get("baseAsset") != testnet_symbol.get("baseAsset"):
            raise CatalogAdmissionError(f"{symbol} base asset differs between environments")
        candidates.append(symbol)
    if len(candidates) > MAX_CATALOG_SYMBOLS:
        raise CatalogAdmissionError(
            f"eligible EUR intersection exceeds the {MAX_CATALOG_SYMBOLS}-symbol cap"
        )

    def inspect_symbol(symbol: str) -> EurCatalogSymbol:
        production_symbol = production[symbol]
        coverage = client.archive_coverage(symbol, retrieved_at.date())
        kline_source_url = (
            f"{client.market_root}/klines?"
            f"{urlencode({'symbol': symbol, 'interval': '1d', 'limit': 31})}"
        )
        ticker_source_url = f"{client.market_root}/ticker/24hr?{urlencode({'symbol': symbol})}"
        rows = client.daily_klines(symbol)
        ticker = client.ticker(symbol)
        liquidity = _liquidity(
            symbol,
            rows,
            ticker,
            retrieved_at,
            kline_source_url=kline_source_url,
            ticker_source_url=ticker_source_url,
        )
        return EurCatalogSymbol(
            symbol=symbol,
            base_asset=str(production_symbol["baseAsset"]),
            quote_asset="EUR",
            status="TRADING",
            exchange_filters=_exchange_filters(production_symbol, symbol),
            coverage=replace(
                coverage,
                intervals=tuple(sorted(set(coverage.intervals))),
                known_gap_dates=tuple(sorted(set(coverage.known_gap_dates))),
                evidence_urls=tuple(sorted(set(coverage.evidence_urls))),
            ),
            liquidity=liquidity,
            liquidity_rank=0,
        )

    with ThreadPoolExecutor(
        max_workers=min(MAX_CATALOG_WORKERS, max(1, len(candidates))),
        thread_name_prefix="binance-catalog",
    ) as executor:
        admitted = list(executor.map(inspect_symbol, candidates))
    if not admitted:
        raise CatalogAdmissionError("no eligible EUR symbols have production archive evidence")
    ranks = {
        entry.symbol: rank
        for rank, entry in enumerate(
            sorted(
                admitted,
                key=lambda entry: (
                    -entry.liquidity.median_daily_quote_volume,
                    entry.symbol,
                ),
            ),
            start=1,
        )
    }
    symbols = tuple(replace(entry, liquidity_rank=ranks[entry.symbol]) for entry in admitted)
    sources = (production_source, testnet_source)
    catalog = EurResearchCatalog(
        catalog_id="",
        retrieved_at=retrieved_at,
        quote_asset="EUR",
        filters=CATALOG_FILTERS,
        sources=sources,
        symbols=symbols,
    )
    return replace(catalog, catalog_id=catalog_identity(catalog))


def catalog_identity(catalog: EurResearchCatalog) -> str:
    """Recompute the content identity of a persisted catalog snapshot."""
    identity = {
        "schema_version": "gridlab.binance-eur-catalog-identity.v2",
        "quote_asset": catalog.quote_asset,
        "filters": catalog.filters,
        "sources": [asdict(source) for source in catalog.sources],
        "symbols": [asdict(entry) for entry in catalog.symbols],
    }
    return _sha256(identity)

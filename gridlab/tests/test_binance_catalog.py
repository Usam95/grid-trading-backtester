from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from gridlab.data.binance_catalog import (
    ArchiveCoverage,
    CatalogAdmissionError,
    OfficialBinanceCatalogClient,
    discover_eur_catalog,
)


NOW = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)
EXPECTED_EUR_SNAPSHOT = (
    "ADAEUR",
    "APTEUR",
    "ATOMEUR",
    "AVAXEUR",
    "BCHEUR",
    "BNBEUR",
    "BTCEUR",
    "DOGEEUR",
    "DOTEUR",
    "EGLDEUR",
    "ETHEUR",
    "ICPEUR",
    "LINKEUR",
    "LTCEUR",
    "NEAREUR",
    "PEPEEUR",
    "POLEUR",
    "RENDEREUR",
    "SEUR",
    "SHIBEUR",
    "SOLEUR",
    "SUIEUR",
    "TRXEUR",
    "VETEUR",
    "WINEUR",
    "WLDEUR",
    "WLFIEUR",
    "XLMEUR",
    "XRPEUR",
)


def _symbol(symbol: str, *, status: str = "TRADING") -> dict[str, object]:
    return {
        "symbol": symbol,
        "status": status,
        "baseAsset": symbol.removesuffix("EUR"),
        "quoteAsset": "EUR",
        "isSpotTradingAllowed": True,
        "orderTypes": ["LIMIT", "LIMIT_MAKER", "MARKET"],
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
            {"filterType": "LOT_SIZE", "stepSize": "0.00010000"},
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
        ],
    }


def _daily_rows() -> list[list[object]]:
    rows: list[list[object]] = []
    start = NOW - timedelta(days=31)
    for index in range(30):
        opened = start + timedelta(days=index)
        close = Decimal("100") + index
        rows.append(
            [
                int(opened.timestamp() * 1000),
                str(close - 1),
                str(close + 1),
                str(close - 2),
                str(close),
                "10",
                int((opened + timedelta(days=1) - timedelta(milliseconds=1)).timestamp() * 1000),
                str(1_000_000 + index * 10_000),
                100 + index,
                "5",
                "500000",
                "0",
            ]
        )
    return rows


class FixtureCatalogClient:
    production_url = "https://data-api.binance.vision/api/v3/exchangeInfo"
    testnet_url = "https://testnet.binance.vision/api/v3/exchangeInfo"
    archive_root = "https://data.binance.vision/data"
    market_root = "https://data-api.binance.vision/api/v3"

    def __init__(self) -> None:
        server_time = int(NOW.timestamp() * 1000)
        self.production = {
            "timezone": "UTC",
            "serverTime": server_time,
            "symbols": [_symbol("BTCEUR"), _symbol("ETHEUR"), _symbol("BTCUSDT")],
        }
        self.testnet = {
            "timezone": "UTC",
            "serverTime": server_time,
            "symbols": [_symbol("ETHEUR"), _symbol("BTCEUR"), _symbol("SOLEUR")],
        }

    def production_exchange_info(self) -> dict[str, object]:
        return self.production

    def testnet_exchange_info(self) -> dict[str, object]:
        return self.testnet

    def daily_klines(self, _symbol: str) -> list[list[object]]:
        return _daily_rows()

    def ticker(self, symbol: str) -> dict[str, object]:
        return {
            "symbol": symbol,
            "bidPrice": "128.00",
            "askPrice": "128.25",
            "count": 3210,
        }

    def archive_coverage(self, symbol: str, _as_of: date) -> ArchiveCoverage:
        first = date(2020, 1, 1) if symbol == "BTCEUR" else date(2021, 6, 1)
        return ArchiveCoverage(
            first_date=first,
            last_date=date(2026, 7, 21),
            intervals=("1m", "5m", "1h", "1d"),
            known_gap_dates=(),
            evidence_urls=(f"https://data.binance.vision/data/spot/daily/klines/{symbol}/1m/",),
        )


def test_discovers_canonical_eur_intersection_with_reproducible_selection_evidence() -> None:
    catalog = discover_eur_catalog(FixtureCatalogClient(), retrieved_at=NOW)

    assert [entry.symbol for entry in catalog.symbols] == ["BTCEUR", "ETHEUR"]
    assert len(catalog.catalog_id) == 64
    assert catalog.quote_asset == "EUR"
    assert catalog.filters == (
        "production_and_testnet",
        "TRADING",
        "spot_allowed",
        "LIMIT_MAKER",
        "quote_asset=EUR",
    )

    btc = catalog.symbols[0]
    assert btc.base_asset == "BTC"
    assert btc.coverage.first_date == date(2020, 1, 1)
    assert btc.coverage.last_date == date(2026, 7, 21)
    assert btc.coverage.intervals == ("1d", "1h", "1m", "5m")
    assert btc.liquidity.observed_days == 30
    assert btc.liquidity.observed_start_date == date(2026, 6, 22)
    assert btc.liquidity.observed_end_date == date(2026, 7, 21)
    assert btc.liquidity.kline_source_url.endswith("/klines?symbol=BTCEUR&interval=1d&limit=31")
    assert len(btc.liquidity.kline_payload_sha256) == 64
    assert len(btc.liquidity.ticker_payload_sha256) == 64
    assert btc.liquidity.median_daily_quote_volume == Decimal("1145000")
    assert btc.liquidity.median_daily_trade_count == Decimal("114.5")
    assert btc.liquidity.current_spread_bps == Decimal("19.51219512")
    assert btc.exchange_filters["PRICE_FILTER"]["tickSize"] == "0.01000000"

    repeated = discover_eur_catalog(FixtureCatalogClient(), retrieved_at=NOW)
    assert repeated.catalog_id == catalog.catalog_id


def test_reproduces_the_operator_approved_29_symbol_discovery_fixture() -> None:
    client = FixtureCatalogClient()
    client.production["symbols"] = [_symbol(symbol) for symbol in reversed(EXPECTED_EUR_SNAPSHOT)]
    client.testnet["symbols"] = [_symbol(symbol) for symbol in EXPECTED_EUR_SNAPSHOT]

    catalog = discover_eur_catalog(client, retrieved_at=NOW)

    assert tuple(entry.symbol for entry in catalog.symbols) == EXPECTED_EUR_SNAPSHOT


def test_rejects_duplicate_catalog_evidence() -> None:
    client = FixtureCatalogClient()
    client.production["symbols"].append(client.production["symbols"][0])  # type: ignore[union-attr]

    with pytest.raises(CatalogAdmissionError, match="duplicate"):
        discover_eur_catalog(client, retrieved_at=NOW)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda client: client.production.update(
                serverTime=int((NOW - timedelta(hours=1)).timestamp() * 1000)
            ),
            "stale",
        ),
        (
            lambda client: client.production.update(timezone="Europe/Berlin"),
            "timezone",
        ),
        (
            lambda client: client.production.update(symbols="not-a-list"),
            "symbols are invalid",
        ),
    ],
)
def test_rejects_stale_or_malformed_catalog_evidence(mutation: object, message: str) -> None:
    client = FixtureCatalogClient()
    mutation(client)  # type: ignore[operator]

    with pytest.raises(CatalogAdmissionError, match=message):
        discover_eur_catalog(client, retrieved_at=NOW)


def test_rejects_an_unbounded_eligible_catalog_before_per_symbol_acquisition() -> None:
    client = FixtureCatalogClient()
    symbols = [_symbol(f"A{index:03d}EUR") for index in range(101)]
    client.production["symbols"] = symbols
    client.testnet["symbols"] = list(reversed(symbols))

    with pytest.raises(CatalogAdmissionError, match="exceeds the 100-symbol cap"):
        discover_eur_catalog(client, retrieved_at=NOW)


@pytest.mark.parametrize(
    ("source", "mutation", "expected"),
    [
        ("production", lambda symbol: symbol.update(status="BREAK"), ["ETHEUR"]),
        ("testnet", lambda symbol: symbol.update(isSpotTradingAllowed=False), ["BTCEUR"]),
        (
            "production",
            lambda symbol: symbol.update(orderTypes=["LIMIT", "MARKET"]),
            ["ETHEUR"],
        ),
    ],
)
def test_excludes_entries_that_fail_trading_eligibility(
    source: str,
    mutation: object,
    expected: list[str],
) -> None:
    client = FixtureCatalogClient()
    symbols = getattr(client, source)["symbols"]
    mutation(symbols[0])  # type: ignore[operator]

    catalog = discover_eur_catalog(client, retrieved_at=NOW)

    assert [entry.symbol for entry in catalog.symbols] == expected


class FixtureTransport:
    def __init__(self) -> None:
        self.text_urls: list[str] = []

    def get_json(self, url: str) -> object:
        if "exchangeInfo" in url:
            return {"timezone": "UTC", "serverTime": int(NOW.timestamp() * 1000), "symbols": []}
        if "/klines?" in url:
            return _daily_rows()
        if "/ticker/24hr?" in url:
            return {"symbol": "BTCEUR", "bidPrice": "100", "askPrice": "101", "count": 42}
        raise AssertionError(f"unexpected JSON URL {url}")

    def get_text(self, url: str) -> str:
        self.text_urls.append(url)
        query = parse_qs(urlparse(url).query)
        prefix = query["prefix"][0]
        if query.get("delimiter") == ["/"]:
            prefixes = [
                f"{prefix}1m/",
                f"{prefix}5m/",
                f"{prefix}1h/",
                f"{prefix}1d/",
            ]
            body = "".join(
                f"<CommonPrefixes><Prefix>{item}</Prefix></CommonPrefixes>" for item in prefixes
            )
            return f"<ListBucketResult>{body}<IsTruncated>false</IsTruncated></ListBucketResult>"
        if not prefix.endswith("/1m/"):
            raise AssertionError(f"unexpected listing prefix {prefix}")
        keys = [
            f"{prefix}BTCEUR-1m-2026-07-09.zip",
            f"{prefix}BTCEUR-1m-2026-07-11.zip",
        ]
        body = "".join(f"<Contents><Key>{key}</Key></Contents>" for key in keys)
        return f"<ListBucketResult>{body}<IsTruncated>false</IsTruncated></ListBucketResult>"


def test_official_client_discovers_exact_bounded_daily_archive_coverage() -> None:
    transport = FixtureTransport()
    client = OfficialBinanceCatalogClient(transport)

    assert client.production_exchange_info()["timezone"] == "UTC"
    assert client.testnet_exchange_info()["timezone"] == "UTC"
    assert len(client.daily_klines("BTCEUR")) == 30
    assert client.ticker("BTCEUR")["count"] == 42

    coverage = client.archive_coverage("BTCEUR", date(2026, 7, 23))

    assert coverage.first_date == date(2026, 7, 9)
    assert coverage.last_date == date(2026, 7, 11)
    assert coverage.intervals == ("1d", "1h", "1m", "5m")
    assert coverage.known_gap_dates == (date(2026, 7, 10),)
    assert len(transport.text_urls) == 2


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("", "truncation evidence"),
        ("<IsTruncated>true</IsTruncated>", "continuation token"),
    ],
)
def test_official_client_rejects_malformed_archive_pagination(
    replacement: str, message: str
) -> None:
    class MissingPaginationTransport(FixtureTransport):
        def get_text(self, url: str) -> str:
            text = super().get_text(url)
            return text.replace("<IsTruncated>false</IsTruncated>", replacement)

    client = OfficialBinanceCatalogClient(MissingPaginationTransport())

    with pytest.raises(CatalogAdmissionError, match=message):
        client.archive_coverage("BTCEUR", date(2026, 7, 23))

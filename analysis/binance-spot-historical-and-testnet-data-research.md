# Binance Spot Testnet symbols and production-history coverage

Status: primary-source research for a future capability ticket
Research snapshot: 2026-07-23 (Europe/Berlin)
Scope: Binance.com Spot Test Network and the official Binance Spot public-data archive

## Conclusion

Ticket 03 is deliberately a bounded tracer: its Studio workflow fixes `BTCUSDT`, native `1m`, and one complete UTC day. That is an implementation scope limit, not a Binance limit, and the successful 2022 screenshot is evidence that it is not restricted to January 2025.

The correct expansion is **not** a hard-coded list of symbols or dates. Binance Spot Testnet is reset approximately monthly and its symbol catalog changes. The application should:

1. discover the current Testnet Spot catalog from Testnet `GET /api/v3/exchangeInfo`;
2. retain only symbols that are `TRADING`, Spot-enabled, and support `LIMIT_MAKER`;
3. independently discover official production-archive coverage for each selected symbol and interval;
4. offer only the intersection for research backed by manifested production history; and
5. keep Testnet venue evidence and production market-history evidence explicitly separate.

The official public archive remains the right source for backtesting. Testnet klines are transient data from the current Testnet generation and are not a durable historical archive or profitability evidence.

## Live catalog snapshot

The official live endpoints were captured on 2026-07-23:

- Testnet: [`https://testnet.binance.vision/api/v3/exchangeInfo`](https://testnet.binance.vision/api/v3/exchangeInfo)
- Production: [`https://api.binance.com/api/v3/exchangeInfo`](https://api.binance.com/api/v3/exchangeInfo)

Applying the project-relevant predicate—`status == "TRADING"`, Spot trading allowed, and `LIMIT_MAKER` in `orderTypes`—produced:

| Catalog measurement | Count |
| --- | ---: |
| Current eligible Testnet symbols | 1,373 |
| Current eligible production symbols | 1,376 |
| Symbols in both catalogs | 1,308 |
| Testnet symbols absent from the current production catalog | 65 |

All 1,373 selected Testnet symbols reported `TRADING`. The complete symbol list should be treated as generated venue metadata, not copied into source code; the following command reproduces and exports it:

```powershell
$capturedAt = (Get-Date).ToUniversalTime().ToString("o")
$testnet = Invoke-RestMethod "https://testnet.binance.vision/api/v3/exchangeInfo"
$production = Invoke-RestMethod "https://api.binance.com/api/v3/exchangeInfo"

function Eligible-SpotSymbols($exchangeInfo) {
    @(
        $exchangeInfo.symbols |
            Where-Object {
                $_.status -eq "TRADING" -and
                $_.isSpotTradingAllowed -eq $true -and
                $_.orderTypes -contains "LIMIT_MAKER"
            } |
            Sort-Object symbol
    )
}

$testnetSymbols = Eligible-SpotSymbols $testnet
$productionSymbols = Eligible-SpotSymbols $production
$productionSet = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]$productionSymbols.symbol
)
$intersection = @($testnetSymbols | Where-Object {
    $productionSet.Contains($_.symbol)
})
$testnetOnly = @($testnetSymbols | Where-Object {
    -not $productionSet.Contains($_.symbol)
})

[ordered]@{
    captured_at_utc = $capturedAt
    testnet_server_time = $testnet.serverTime
    production_server_time = $production.serverTime
    testnet_eligible_count = $testnetSymbols.Count
    production_eligible_count = $productionSymbols.Count
    intersection_count = $intersection.Count
    testnet_only_count = $testnetOnly.Count
    testnet_symbols = @($testnetSymbols.symbol)
    production_intersection = @($intersection.symbol)
    testnet_only = @($testnetOnly.symbol)
} | ConvertTo-Json -Depth 5
```

The `exchangeInfo` response is the official contract for current symbol status, permissions, order types, precision, and filters. Binance instructs clients to query it rather than assume example filter values. See the [official exchange-information contract](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#exchange-information) and [official symbol-filter contract](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md).

## Kline intervals

The Spot REST kline endpoint defines these intervals:

`1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`.

The interval enum is an endpoint-level contract; `exchangeInfo` does not publish a per-symbol interval list. A symbol may nevertheless have no rows, a later listing date, gaps, or shorter archive coverage. Therefore “interval accepted by the API” and “complete downloadable history exists for this symbol” are different facts. See the [official Spot kline endpoint](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data).

Official S3 prefix discovery on 2026-07-23 found the archive interval directory names:

`1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1mo`.

`1mo` is the public-archive directory spelling corresponding to the REST API's `1M`. Those directories are not guaranteed for every symbol. For example, observed new `TONU*` and `TONUSD1*` archive prefixes lacked `3d`, `1w`, and `1mo`. The UI must therefore discover coverage per symbol, not present the global union as if every combination exists.

## Actual Testnet history duration

The official Testnet FAQ states that the environment is periodically reset, approximately once per month and without advance notice. Pending and executed orders are removed, balances are reset, and API keys are retained. See the [official Binance Spot Test Network FAQ](https://testnet.binance.vision/).

A complete bounded query of the current Testnet `1m` kline catalog found history for all 1,373 eligible symbols. Earliest rows were:

| Earliest current-generation `1m` candle | Symbols |
| --- | ---: |
| 2026-06-03 13:34 UTC | 603 |
| 2026-06-03 13:35 UTC | 767 |
| 2026-06-03 13:36 UTC | 2 |
| 2026-06-08 15:41 UTC (`TSLABUSDT`) | 1 |

The latest sampled candle was 2026-07-23 18:29 UTC, giving approximately 50.2 days for the oldest current-generation series. This is an observation of the current generation, **not a retention guarantee**. The next reset can erase it.

The following command reproduces the earliest and latest available `1m` row for every current eligible Testnet symbol. It should be run slowly enough to respect the rate-limit fields returned by `exchangeInfo`:

```powershell
$info = Invoke-RestMethod "https://testnet.binance.vision/api/v3/exchangeInfo"
$symbols = @(
    $info.symbols |
        Where-Object {
            $_.status -eq "TRADING" -and
            $_.isSpotTradingAllowed -eq $true -and
            $_.orderTypes -contains "LIMIT_MAKER"
        } |
        Sort-Object symbol
)

$coverage = foreach ($item in $symbols) {
    $symbol = [uri]::EscapeDataString($item.symbol)
    $first = Invoke-RestMethod `
        "https://testnet.binance.vision/api/v3/klines?symbol=$symbol&interval=1m&startTime=0&limit=1"
    Start-Sleep -Milliseconds 75
    $last = Invoke-RestMethod `
        "https://testnet.binance.vision/api/v3/klines?symbol=$symbol&interval=1m&limit=1"
    Start-Sleep -Milliseconds 75
    [ordered]@{
        symbol = $item.symbol
        first_open_time = if ($first.Count) {
            [DateTimeOffset]::FromUnixTimeMilliseconds([int64]$first[0][0]).
                UtcDateTime.ToString("o")
        } else { $null }
        last_open_time = if ($last.Count) {
            [DateTimeOffset]::FromUnixTimeMilliseconds([int64]$last[0][0]).
                UtcDateTime.ToString("o")
        } else { $null }
    }
}

$coverage | ConvertTo-Json -Depth 4
```

Testnet's REST endpoint is appropriate for short-lived adapter and order-lifecycle testing. It is not a durable bulk-download service: requests return at most 1,000 klines, history disappears on resets, and no checksum-backed Testnet archive is documented.

## Testnet klines versus the production archive

These sources answer different questions:

| Evidence | Authority and purpose |
| --- | --- |
| Testnet `/api/v3/klines` | Transient market data in the current virtual Testnet generation; useful for exercising protocol integration. |
| Production `data.binance.vision` | Official, checksum-backed historical Binance Spot market evidence for deterministic research and backtesting. |

The official public-data project publishes daily and monthly production Spot `klines`, `trades`, and `aggTrades`, with SHA-256 companion files. It says all symbols are supported, but individual symbols begin at their listing/history boundary and files can be absent. It also notes that Spot archive timestamps switch from milliseconds to microseconds from 2025-01-01 onward. See the [official Binance public-data repository](https://github.com/binance/binance-public-data) and [official data portal](https://data.binance.vision/).

The archive is production history even when the symbol is also tradable on Testnet. A backtest over that archive must continue to say “production history”; it must not imply that the candles originated on Testnet.

## Production archive discovery for the Testnet intersection

The 1,308-symbol intersection is immediately eligible for per-symbol archive probing. The additional 65 Testnet-only-current symbols must not be discarded without checking historical production evidence: official S3 discovery found historical production monthly archives for 64 of those 65. Only `这是测试币456` had no production archive. This shows why “absent from current production `exchangeInfo`” is not equivalent to “never had production history.”

For the anchor pair, official monthly `BTCUSDT` `1m` archive files ran from 2017-08 through 2026-06 in the 2026-07-23 snapshot. Coverage for other symbols and intervals differs.

The official public-data bucket supports unauthenticated S3 `ListObjectsV2`. This PowerShell probe lists available monthly interval prefixes and files for one symbol:

```powershell
$symbol = "BTCUSDT"
$bucket = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
$symbolPrefix = "data/spot/monthly/klines/$symbol/"
$prefixUri = "$bucket/?list-type=2&delimiter=/&prefix=$(
    [uri]::EscapeDataString($symbolPrefix)
)"
[xml]$prefixes = (Invoke-WebRequest $prefixUri).Content
$intervalPrefixes = @($prefixes.ListBucketResult.CommonPrefixes.Prefix)

$result = foreach ($intervalPrefix in $intervalPrefixes) {
    $fileUri = "$bucket/?list-type=2&prefix=$(
        [uri]::EscapeDataString([string]$intervalPrefix)
    )"
    [xml]$files = (Invoke-WebRequest $fileUri).Content
    $zipKeys = @(
        $files.ListBucketResult.Contents.Key |
            Where-Object { $_ -like "*.zip" } |
            Sort-Object
    )
    [ordered]@{
        symbol = $symbol
        archive_interval = ([string]$intervalPrefix).TrimEnd("/").Split("/")[-1]
        first_file = $zipKeys | Select-Object -First 1
        last_file = $zipKeys | Select-Object -Last 1
        file_count = $zipKeys.Count
    }
}
$result | ConvertTo-Json -Depth 4
```

A production implementation must also follow `NextContinuationToken` for prefixes with more than 1,000 objects, verify each `.CHECKSUM`, and distinguish a missing object from a network failure. A bounded preview should report before download:

- Testnet catalog snapshot identity and capture time;
- symbol and current Testnet status/filter eligibility;
- whether it is in current production `exchangeInfo`;
- archive dataset and interval;
- first and last discovered files;
- complete-day/month coverage and gaps;
- estimated bytes;
- checksum availability; and
- timestamp-unit era.

## Recommended project capability

Add a separate, bounded capability ticket after the current Ticket 03 baseline:

1. **Dynamic Testnet catalog:** refresh and cache signed evidence from official Testnet `exchangeInfo`; never hard-code 1,373 symbols.
2. **Per-symbol production coverage index:** probe the official archive for each Testnet symbol, interval, and available date range; refresh it independently from Testnet.
3. **Cascading Studio selection:** choose a current eligible Testnet symbol, then show only production intervals and complete dates actually discovered for it.
4. **Bounded acquisition:** retain preview-before-download, explicit maximum files/bytes/candles, checksums, timestamp-era validation, typed Parquet, and manifest identity.
5. **Explicit provenance:** label backtests as production history and Testnet sessions as transient integration evidence.
6. **Generation awareness:** capture Testnet catalog/server time and detect resets; do not promise a fixed Testnet history duration.
7. **Operational defaults:** default to the current production/Testnet intersection and a durable archive interval such as `1m`; expose historical-only exceptions deliberately.

Do not automatically download every interval for all 1,373 symbols. That would be unbounded, duplicate coarser data, and confuse integration coverage with a research universe. Discovery can cover the full catalog cheaply; bytes should be downloaded only for the operator's bounded selection or a separately approved frozen research panel.

## Provisional 50-symbol selectable universe

Snapshot date: 2026-07-23. This is a reproducible **discovery snapshot**, not
a permanent allowlist or an investment recommendation.

For a useful default list, raw volatility is a poor ranking by itself: a thin
market can move sharply without being a viable backtest or execution candidate.
The provisional screen therefore used the following order:

1. intersect the current Testnet and production `exchangeInfo` catalogs;
2. require `TRADING`, Spot trading enabled, and `LIMIT_MAKER`;
3. require a `USDT` quote;
4. exclude stablecoin/fiat bases and obvious synthetic/special-case Testnet
   entries (`TSLABUSDT` and `币安人生USDT`);
5. require at least 5,000 production trades in the trailing 24-hour ticker
   window and a high-to-low range of at least 1%; and
6. rank the survivors by production 24-hour quote volume.

This makes liquidity the primary ordering and volatility a minimum admission
condition. It avoids the common failure mode in which a pure percentage-move
ranking is dominated by illiquid pairs. The production ticker contract defines
`quoteVolume`, `count`, `highPrice`, and `lowPrice`; the live snapshot came from
the [official market-data-only ticker endpoint](https://data-api.binance.vision/api/v3/ticker/24hr).

| Rank | Symbol | Monthly `1m` archive range | Rank | Symbol | Monthly `1m` archive range |
| ---: | --- | --- | ---: | --- | --- |
| 1 | `BTCUSDT` | 2017-08–2026-06 | 26 | `SYNUSDT` | 2023-02–2026-06 |
| 2 | `ETHUSDT` | 2017-08–2026-06 | 27 | `KAITOUSDT` | 2025-02–2026-06 |
| 3 | `KITEUSDT` | 2025-11–2026-06 | 28 | `XLMUSDT` | 2018-05–2026-06 |
| 4 | `SOLUSDT` | 2020-08–2026-06 | 29 | `PEPEUSDT` | 2023-05–2026-06 |
| 5 | `BANKUSDT` | 2025-11–2026-06 | 30 | `UNIUSDT` | 2020-09–2026-06 |
| 6 | `DOGEUSDT` | 2019-07–2026-06 | 31 | `AVAXUSDT` | 2020-09–2026-06 |
| 7 | `XRPUSDT` | 2018-05–2026-06 | 32 | `AAVEUSDT` | 2020-10–2026-06 |
| 8 | `ZECUSDT` | 2019-03–2026-06 | 33 | `ERAUSDT` | 2025-07–2026-06 |
| 9 | `DEXEUSDT` | 2021-07–2026-06 | 34 | `LINKUSDT` | 2019-01–2026-06 |
| 10 | `BNBUSDT` | 2017-11–2026-06 | 35 | `HBARUSDT` | 2019-09–2026-06 |
| 11 | `WLFIUSDT` | 2025-09–2026-06 | 36 | `TRUMPUSDT` | 2025-01–2026-06 |
| 12 | `ZAMAUSDT` | 2026-02–2026-06 | 37 | `TAOUSDT` | 2024-04–2026-06 |
| 13 | `OPNUSDT` | 2026-03–2026-06 | 38 | `LAUSDT` | 2025-07–2026-06 |
| 14 | `TRXUSDT` | 2018-06–2026-06 | 39 | `PUMPUSDT` | 2025-09–2026-06 |
| 15 | `ENAUSDT` | 2024-04–2026-06 | 40 | `BARDUSDT` | 2025-09–2026-06 |
| 16 | `XAUTUSDT` | 2026-03–2026-06 | 41 | `FILUSDT` | 2020-10–2026-06 |
| 17 | `RIFUSDT` | 2021-01–2026-06 | 42 | `ASTERUSDT` | 2025-10–2026-06 |
| 18 | `WLDUSDT` | 2023-07–2026-06 | 43 | `ALLOUSDT` | 2025-11–2026-06 |
| 19 | `VANAUSDT` | 2024-12–2026-06 | 44 | `BCHUSDT` | 2019-11–2026-06 |
| 20 | `SUIUSDT` | 2023-05–2026-06 | 45 | `JTOUSDT` | 2023-12–2026-06 |
| 21 | `LTCUSDT` | 2017-12–2026-06 | 46 | `ZKCUSDT` | 2025-09–2026-06 |
| 22 | `ONDOUSDT` | 2025-04–2026-06 | 47 | `ARBUSDT` | 2023-03–2026-06 |
| 23 | `ADAUSDT` | 2018-04–2026-06 | 48 | `DODOUSDT` | 2021-02–2026-06 |
| 24 | `NEARUSDT` | 2020-10–2026-06 | 49 | `MIRAUSDT` | 2025-09–2026-06 |
| 25 | `PAXGUSDT` | 2020-08–2026-06 | 50 | `VIRTUALUSDT` | 2025-04–2026-06 |

Official monthly `1m` archive discovery found production history for every
candidate. In this snapshot, each series had a last complete monthly file of
`2026-06`; first monthly files varied from `2017-08` for the oldest markets to
`2026-03` for the newest. That shared end is not proof that every day is
gap-free, and a monthly start alone is not the exact first candle. The Studio
must query and show the exact discovered first/last complete object, missing
objects, total bytes, and checksum availability **after symbol and interval
selection**, before allowing download.

The list deliberately mixes long-lived benchmark markets with newer,
high-turnover markets. A user should be able to sort and filter it using at
least:

- current Testnet eligibility and symbol filters;
- production 24-hour quote volume, trade count, and high/low range;
- production-history first/last date and history length;
- available archive intervals;
- quote/base assets and current status; and
- a freshness timestamp for both catalog and market metrics.

For implementation, replace the provisional 24-hour movement gate with a
bounded, reproducible 30-day production calculation: median daily quote volume,
median daily trade count, annualized close-to-close realized volatility, number
of observed days, and maximum detected gap. A defensible default score is a
weighted percentile score such as 60% liquidity and 40% realized volatility,
with hard minimum liquidity, history-length, and completeness gates. Preserve
the component values in the catalog snapshot so the ranking can be explained
and reproduced; never persist only an opaque score.

Because Testnet resets and live turnover changes, the 50 should be refreshed as
a versioned snapshot. A symbol leaving the top 50 must not invalidate an
existing dataset manifest or experiment. Conversely, appearing in the current
top 50 does not authorize an unbounded download: the operator must still choose
the symbol, interval, and bounded date range and approve the preview.

## Primary sources

- [Official Spot Test Network and reset FAQ](https://testnet.binance.vision/)
- [Official live Testnet exchange information](https://testnet.binance.vision/api/v3/exchangeInfo)
- [Official live production exchange information](https://api.binance.com/api/v3/exchangeInfo)
- [Official Spot REST API: exchange information and klines](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [Official Spot symbol filters](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md)
- [Official Binance public-data repository](https://github.com/binance/binance-public-data)
- [Official Binance public-data portal](https://data.binance.vision/)
- [Official Binance public-data S3 bucket](https://s3-ap-northeast-1.amazonaws.com/data.binance.vision)

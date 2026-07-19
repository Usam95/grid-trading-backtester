# Binance Spot contract for the first MVP

Status: official-contract research completed 2026-07-14  
Scope: Binance.com Spot REST API, WebSocket API, market streams, user-data events, and Spot Test Network  
Primary sources: Binance Developer Documentation, Binance's official `binance-spot-api-docs` repository, and the Binance Spot Test Network FAQ

## Purpose and evidence boundary

This document establishes the venue behavior that the first MVP must design against. It deliberately separates:

- **Official facts**: behavior expressly documented by Binance, with a direct official source beside every material claim.
- **MVP recommendations and inferences**: safety or architecture conclusions drawn for this project. These are not claims that Binance prescribes our design.

The companion [Binance adapter code-gap audit](binance-adapter-code-gap-audit.md) compares this contract with the current canonical and legacy implementations. Existing code is not authority for venue behavior.

Binance changes its contract. The implementation must treat the live exchange-information and limit responses as operational authority and must monitor the official [Spot changelog](https://developers.binance.com/en/docs/products/spot/changelog).

## Official facts

### Interfaces, endpoints, and time representation

- Production Spot REST is available through `https://api.binance.com`, `https://api-gcp.binance.com`, and `api1` through `api4.binance.com`. Binance says `api1` through `api4` may perform better but have less stability. Public-only market data can use `https://data-api.binance.vision`. JSON responses default to milliseconds, with microsecond output available through `X-MBX-TIME-UNIT`; HMAC, RSA, and Ed25519 keys are supported. [Official REST general information](https://developers.binance.com/en/docs/products/spot/rest-api)
- Production market streams use `wss://stream.binance.com:9443` or port `443`; raw streams use `/ws/<streamName>` and combined streams use `/stream?streams=<streamName1>/<streamName2>`. Stream symbols are lowercase. [Official WebSocket streams specification](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)
- The request/response WebSocket API uses `wss://ws-api.binance.com:443/ws-api/v3`, with port `9443` as an alternative. A WebSocket API connection lasts 24 hours, and Binance sends ping frames every 20 seconds; lack of a matching pong within one minute causes disconnect. [Official WebSocket API specification](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-api.md)

### Authentication, permissions, and timing

- Public endpoints have security type `NONE`. Secure endpoint types include `TRADE`, `USER_DATA`, and `USER_STREAM`; all non-`NONE` endpoint types are signed. Binance permits separate keys for trading and account monitoring, and API keys do not have trading permission by default until it is enabled in API Management. [Official REST request-security contract](https://developers.binance.com/en/docs/products/spot/rest-api#request-security)
- Signed requests require an API key, a signature, and a current `timestamp`. HMAC, RSA, and Ed25519 signatures have different encoding/case rules documented by Binance. [Official signed-endpoint contract](https://developers.binance.com/en/docs/products/spot/rest-api#signed-endpoint-security)
- `recvWindow` defaults to 5,000 ms and cannot exceed 60,000 ms. Binance recommends 5,000 ms or less. The server validates the timestamp/window when accepting the request and checks the elapsed window again before forwarding it to the matching engine. [Official timing-security contract](https://developers.binance.com/en/docs/products/spot/rest-api#timing-security)

### Order entry and post-only behavior

- `POST /api/v3/order` is a signed `TRADE` endpoint. A successful new-order request adds one order to both the symbol `MAX_NUM_ORDERS` and exchange `EXCHANGE_MAX_NUM_ORDERS` filters. [Official Spot trade endpoint](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#new-order-trade)
- Spot order types include `LIMIT`, `MARKET`, stop-loss/take-profit variants, and `LIMIT_MAKER`. `LIMIT_MAKER` requires `quantity` and `price`; it is a post-only limit order and is rejected if it would immediately match and trade as taker. [Official new-order parameters](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#new-order-trade)
- `newClientOrderId` is unique among open orders. If an open order already has the same ID, the new order is rejected; Binance documents reuse as acceptable once the earlier order is filled. Binance assigns `orderId`, and order responses also carry `clientOrderId`. [Official new-order identity fields](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#new-order-trade)
- New-order response modes are `ACK`, `RESULT`, and `FULL`. `MARKET` and `LIMIT` default to `FULL`; other order types default to `ACK`. A `FULL` response can contain fills with `tradeId`, price, quantity, commission quantity, and commission asset. [Official new-order response contract](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#new-order-trade)
- `DELETE /api/v3/order` accepts `orderId` or `origClientOrderId`. If both are supplied, Binance first locates the `orderId` and then verifies the client ID. Binance documents `orderId`-only cancellation as faster. Optional cancel restrictions can limit cancellation to `ONLY_NEW` or `ONLY_PARTIALLY_FILLED`. [Official cancel-order contract](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#cancel-order-trade)
- Cancel-replace evaluates filters and order count before cancellation and replacement. A replacement reported as `NOT_ATTEMPTED` can still increase unfilled-order count, and HTTP `409` represents a partially successful cancel-replace request. [Official cancel-replace contract](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#cancel-an-existing-order-and-send-a-new-order-trade), [official HTTP status semantics](https://developers.binance.com/en/docs/products/spot/rest-api#http-return-codes)

### Order and execution lifecycle

- Documented order statuses are `NEW`, `PENDING_NEW`, `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `PENDING_CANCEL` (currently unused), `REJECTED`, `EXPIRED`, and `EXPIRED_IN_MATCH`. `EXPIRED_IN_MATCH` denotes expiry caused by self-trade prevention. [Official Spot enums](https://developers.binance.com/en/docs/products/spot/enums#order-status-status)
- User-data execution types are `NEW`, `CANCELED`, `REPLACED`, `REJECTED`, `TRADE`, `EXPIRED`, and `TRADE_PREVENTION`. Thus execution type and current order status are separate fields with different vocabularies. [Official execution-type enums](https://developers.binance.com/en/docs/products/spot/enums#execution-types)
- `GTC` remains active until canceled, `IOC` fills as much as immediately possible and expires the remainder, and `FOK` expires unless the full quantity can execute. [Official time-in-force enums](https://developers.binance.com/en/docs/products/spot/enums#time-in-force-timeinforce)
- Self-trade-prevention modes include `NONE`, `EXPIRE_MAKER`, `EXPIRE_TAKER`, `EXPIRE_BOTH`, `DECREMENT`, and `TRANSFER`; the modes allowed on a new order depend on symbol configuration. [Official STP enums](https://developers.binance.com/en/docs/products/spot/enums#stp-modes), [official new-order parameters](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade#new-order-trade)

### Private event stream and execution evidence

- A user-data stream is subscribed through the WebSocket API with an API key. JSON and SBE are supported, and Binance describes account events as real-time pushes. [Official user-data stream](https://developers.binance.com/en/docs/products/spot/user-data-stream)
- Order updates are emitted as `executionReport`. Account balance changes emit `outboundAccountPosition`; deposits, withdrawals, and transfers can emit `balanceUpdate`. [Official user-data events](https://developers.binance.com/en/docs/products/spot/user-data-stream#user-data-stream-events)
- The documented execution report contains current and last execution information, cumulative executed quantity, cumulative quote quantity, commission quantity and asset, order/client identities, and conditional STP/allocation/working-order fields. Binance specifies average execution price as cumulative quote quantity `Z` divided by cumulative executed quantity `z`. [Official execution-report contract](https://developers.binance.com/en/docs/products/spot/user-data-stream#order-update)

### Ambiguous outcomes and authoritative queries

- REST requests time out after ten seconds of matching-engine processing. Error `-1007 TIMEOUT` explicitly means send/execution status is unknown and does not mean the matching engine failed the request. Binance instructs clients to check the user-data stream and query request status if no status appeared. [Official REST general information](https://developers.binance.com/en/docs/products/spot/rest-api)
- Binance says a `5XX` response must not be treated as a failed operation because execution status is unknown and the operation could have succeeded. `4XX` generally describes a client-side error, while individual endpoints can return documented Binance error payloads. [Official HTTP return-code contract](https://developers.binance.com/en/docs/products/spot/rest-api#http-return-codes)
- Account REST exposes query-order, current-open-orders, all-orders, account-trades, account information, commission rates, prevented matches, and unfilled-order-count operations. Their declared data source varies between matching engine, memory, and database, so observation latency can differ. [Official Spot account endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/account), [official data-source semantics](https://developers.binance.com/en/docs/products/spot/rest-api#data-sources)

### Filters and live trading rules

- Binance defines symbol, exchange, and asset filter categories. [Official filter contract](https://developers.binance.com/en/docs/products/spot/filters)
- `PRICE_FILTER` enforces enabled minimum price, maximum price, and tick-size divisibility. `LOT_SIZE` separately enforces minimum quantity, maximum quantity, and step-size divisibility. [Official price and lot-size filters](https://developers.binance.com/en/docs/products/spot/filters#symbol-filters)
- `MIN_NOTIONAL` and `NOTIONAL` enforce notional bounds. Their market-order application is configured by filter fields; where a market order has no price, evaluation uses the documented reference-price or volume-weighted-average fallback. [Official notional filters](https://developers.binance.com/en/docs/products/spot/filters#min_notional)
- `PERCENT_PRICE` and `PERCENT_PRICE_BY_SIDE` constrain valid prices using the reference price when available and a documented weighted-average fallback otherwise. `MARKET_LOT_SIZE` applies distinct quantity constraints to market orders. [Official dynamic-price and market-lot filters](https://developers.binance.com/en/docs/products/spot/filters)
- Symbol and exchange filters can cap open normal, algorithmic, iceberg, amended, and order-list activity. The concrete values shown in documentation are examples; current rules are returned through exchange information. [Official order-count filters](https://developers.binance.com/en/docs/products/spot/filters#max_num_orders), [official limit discovery](https://developers.binance.com/en/docs/products/spot/rest-api#limits)

### REST rate limits and failure handling

- `/api/v3/exchangeInfo` publishes active `RAW_REQUESTS`, `REQUEST_WEIGHT`, and `ORDERS` limits. Endpoint weights vary; responses expose IP usage in `X-MBX-USED-WEIGHT-*` headers. Limits apply by IP, while unfilled-order count applies by account. [Official REST limits](https://developers.binance.com/en/docs/products/spot/rest-api#limits)
- Successful order responses expose `X-MBX-ORDER-COUNT-*`; rejected orders are not guaranteed to include it. Limit exhaustion returns HTTP `429` with `Retry-After`. Continuing after `429` can produce HTTP `418`; documented repeat-ban duration ranges from two minutes to three days. [Official rate-limit and ban behavior](https://developers.binance.com/en/docs/products/spot/rest-api#ip-limits)
- The WebSocket market-stream contract limits incoming messages to five per second, counting ping, pong, and JSON control messages. A connection can carry at most 1,024 streams, and Binance limits connection attempts to 300 per five minutes per IP. [Official WebSocket stream limits](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#websocket-limits)

### Public market data and stream recovery

- REST provides order-book snapshots, recent and historical trades, aggregate trades, and klines. `/api/v3/depth` returns `lastUpdateId`, up to 5,000 price levels per side, with request weight increasing by depth. `/api/v3/klines` supports `1s`, `1m`, and larger intervals, returns at most 1,000 bars, and identifies bars by open time. [Official Spot market endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)
- The raw trade stream emits one event per trade with a trade ID. The aggregate-trade stream groups fills belonging to one taker order at the same price. `bookTicker` pushes best bid/ask changes, partial-depth streams publish 5, 10, or 20 levels at 1,000 ms or 100 ms, and diff-depth streams publish first/final update IDs. [Official WebSocket market streams](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#detailed-stream-information)
- Binance's local-order-book procedure is: subscribe and buffer diff-depth events; obtain a REST snapshot; discard events whose final update ID is not newer than the snapshot; require the first retained event to bridge the snapshot ID; then apply absolute quantities, removing a level when quantity is zero. If an event's first update ID is greater than the local update ID plus one, events were missed and the book must be discarded and rebuilt. A 5,000-level snapshot cannot establish unchanged quantities beyond its boundary. [Official local-order-book procedure](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#how-to-manage-a-local-order-book-correctly)

### Spot Test Network

- Spot Testnet uses virtual assets that cannot be transferred into or out of the environment. It exposes `/api` endpoints but not `/sapi`. Binance says its IP limits, order limits, exchange filters, and symbol filters are generally the same as production while directing clients to query current values. [Official Spot Test Network FAQ](https://testnet.binance.vision/)
- Testnet is reset to a blank state approximately monthly without advance notice. Pending and executed orders are deleted and asset allowances are replenished; API keys are preserved. [Official Spot Test Network FAQ](https://testnet.binance.vision/)
- The official Testnet interfaces are `https://testnet.binance.vision/api`, `wss://ws-api.testnet.binance.vision/ws-api/v3`, and `wss://stream.testnet.binance.vision` variants listed by Binance. [Official Spot Test Network FAQ](https://testnet.binance.vision/), [official Testnet REST specification](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/rest-api.md)

## MVP recommendations and inferences

Everything in this section is a project decision or an inference from the official facts above, not a Binance requirement.

### Command identity and uncertain outcomes

- Persist the complete order intent and a stable, generation-specific client order ID before network submission. Persist both `clientOrderId` and Binance `orderId` when known.
- Classify timeout, transport loss after send, and `5XX` as `SUBMISSION_UNKNOWN`, not rejected. While an intent is unknown, do not create a replacement for the same rung.
- Resolve uncertainty by correlating the user-data stream with REST query-order, open/all orders, and account trades. Only a positive terminal observation or a bounded, evidence-preserving reconciliation decision may clear the unknown state.
- Avoid cancel-replace in the first MVP. Its independently variable cancellation and placement outcomes add state-machine complexity without being necessary for a static one-order-per-rung grid.

### Execution and accounting

- Treat trade-level execution reports and account-trade queries as canonical fill evidence. Deduplicate by venue identity and retain cumulative quantities so duplicate, reordered, and late reports are harmless.
- Record commission quantity and commission asset exactly as Binance reports them; do not derive fees from a configured percentage.
- Model order status and execution type separately. Partial fills are postings when observed, not merely intermediate display state.

### Rule validation

- Fetch exchange information before activation, retain the exact observation used, and refresh it periodically and after filter-related rejection or symbol-status change.
- Use exact decimal arithmetic. Quantize quantity downward to step size; apply side-aware price quantization for post-only economics, then validate every applicable filter again immediately before submission.
- Fail closed on an unknown filter, unsupported symbol status/permission, stale exchange information, or a value that cannot be represented exactly under the venue rule.

### Streams and reconciliation

- Rotate WebSocket connections before their 24-hour expiry and overlap old/new public streams when practical. A reconnect alone does not prove continuity.
- Any user-stream disconnect, queue overflow, missing sequence, or unknown order outcome enters a reconciliation state in which new order placement is disabled.
- Rebuild diff-depth state from a fresh snapshot after a detected sequence gap. Do not synthesize missing depth updates.
- Reconcile managed orders, terminal histories/trades, balances, commissions, and allocation coverage before resuming. Foreign account activity must be surfaced rather than silently assigned to the grid.

### Test-environment boundary

- Use Spot Testnet for protocol, signing, filter, order-state, reconnect, and failure-path integration tests.
- Do not use Testnet results as evidence of production liquidity, queue position, fill probability, slippage, fee economics, long-duration persistence, or outage behavior. This conclusion is an inference from Testnet's virtual assets and periodic resets.
- Keep live-data paper trading distinct from Testnet: paper mode consumes production public data through a simulator and sends no venue orders; venue-integration-test mode may send executable Testnet orders.

### MVP contract tests implied by the research

1. A marketable `LIMIT_MAKER` rejection never falls back to ordinary `LIMIT` or `MARKET`.
2. Submit timeout/`5XX` leaves the intent unknown and blocks its replacement until reconciled.
3. Duplicate and late execution reports do not duplicate fills or fees.
4. Commission assets different from base and quote are retained as native-asset postings.
5. Every supported filter is evaluated with exact decimals; unknown filters fail closed.
6. `429` obeys `Retry-After`; the adapter stops before repeated violations can produce `418`.
7. WebSocket rotation, disconnect, and depth-sequence gaps force recovery before decisions resume.
8. A Testnet reset is handled as an environment reset, not interpreted as production-style order cancellation.

## Open items that official documentation alone does not settle

- The exact first-MVP quantitative risk limits, capital allocation, drawdown threshold, and stale-data threshold are product decisions.
- Production fill realism, queue position, and slippage require recorded production market evidence and live-data paper validation; the API schema does not establish them.
- Availability and retention of historical order/trade evidence must be tested against the chosen account, symbol, and operating horizon, then backed by the append-only local journal.
- Regional eligibility, account configuration, fee tier, BNB fee usage, symbol-specific STP configuration, and permissions must be checked on the actual production account before promotion.


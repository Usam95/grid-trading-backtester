# Binance adapter code-gap audit

Status: local evidence for [Research the current Binance Spot contract](../.scratch/comprehensive-grid-trading-system/issues/05-research-binance-spot-contract.md)  
Scope: existing canonical and legacy code; official venue facts are established separately in `binance-spot-contract.md`

## Purpose

This audit identifies assumptions and omissions in the current repositories that the Binance Spot contract and future adapter must explicitly accept, replace, or reject. Existing code is evidence about reuse opportunities and failure scenarios, not authority for current Binance behavior.

## Canonical `gridlab` findings

### No online exchange adapter

`gridlab` currently has historical Binance kline loading and generic exchange-rule simulation, but no production REST command adapter, user-data consumer, public live event feed, order-state reconciliation, or account reconciliation. The legacy runtime cannot be promoted in place without crossing the accepted deterministic-event, exact-accounting, and allocation-isolation boundaries.

### Approximate static symbol rules

`gridlab/src/gridlab/execution/exchange_rules.py` hard-codes approximate filters for a few symbols and a generic USDT fallback. The file itself labels them research defaults rather than a live source of truth.

Gaps against the accepted accounting and grid semantics:

- binary floats are used for price, quantity, and filter values;
- price is rounded to the nearest tick without order-side-aware economics;
- only tick size, step size, minimum quantity, and minimum notional are modeled;
- maximum quantity/notional, market-specific quantity rules, percent-price constraints, order-count limits, symbol status and permissions, and other current exchange filters are absent;
- rules have no source timestamp, venue-rule version, or refresh/revalidation behavior;
- a generic fallback could authorize an order for a symbol whose actual rules differ.

The future adapter must parse current source-exact exchange metadata into a time-versioned venue-rule observation, reject unknown or unsupported filters fail-closed, quantize at the submission boundary, and retain the exact rule version used.

### Historical loader is research-only

`gridlab/src/gridlab/data/loaders.py` downloads Spot klines and caches CSV files, but:

- parses venue decimal strings into floats;
- stores no dataset manifest, response provenance, checksums, completeness report, or gap report;
- retries alternate hosts without recording which source supplied each page;
- supports only its hard-coded interval table and no trade, best-bid/offer, depth, or user/account evidence;
- uses a `1000` page limit and endpoint assumptions that require verification against current documentation;
- deduplicates timestamps but does not prove that the expected interval sequence is complete.

It remains a useful seed for broad candle acquisition after provenance, validation, exact source preservation, and archive formats are redesigned.

## Legacy live-runtime findings

### Paper trading is conflated with Spot Testnet

`backtester_old/infra/exchange/binance_spot.py` maps `PAPER` to Binance Spot Testnet and sends real testnet API commands. The accepted vocabulary defines paper trading as live-data simulation without executable venue orders; testnet belongs to the separate venue-integration-test mode. This mode boundary must be replaced rather than retained.

### Normal grid orders are not post-only

The legacy `place_limit_order` submits ordinary `LIMIT` orders with `GTC`. It can therefore execute immediately as taker and does not implement the canonical post-only maker contract. The future adapter must use the venue's documented post-only mechanism for normal grid orders and treat a marketable rejection as an explicit venue outcome—never silently fall back to an ordinary limit or market order.

### Quantization conflicts with selected semantics

Legacy limit prices are rounded downward for both buys and sells. Canonical behavior rounds post-only buys downward and sells upward to preserve no-worse-than-rung economics. Quantity rounds downward, which is directionally reusable, but filter values pass through floats and only a subset of rules is validated.

### Incomplete filter model

The legacy `SymbolFilters` captures only tick size, step size, minimum quantity, and optional `MIN_NOTIONAL`. It omits maximum bounds and other symbol, exchange, asset, account, and dynamic price constraints. It also treats absence of a supported filter as permission rather than an unsupported-rule safety condition.

### Submission outcome is not ambiguity-safe

Order placement returns or raises directly through the client library. There is no durable command-before-send record, timeout/5xx ambiguity classification, query-by-stable-identity recovery loop, or prohibition on duplicate replacement while acceptance remains unknown.

### Client identities are not sufficient journal identities

`backtester_old/core/live/order_manager.py` has useful restart-readable client identities, but the grid format uses a four-character hash and deterministic order parameters represented through floats. Repeating the same rung, side, price, and quantity can reproduce an identity across later cycles, making lifetime provenance and idempotency ambiguous. A future identity must include stable run/configuration/rung/side/generation or intent sequence while obeying the venue's current character and length constraints.

### Reconciliation only observes open orders

Startup and periodic reconciliation call `get_open_orders` and merge those results into in-memory order state. They do not prove:

- terminal order histories;
- every trade and partial fill since the durable checkpoint;
- actual commission quantity and asset;
- balances and allocation coverage at the same reconciliation boundary;
- whether an apparently absent local order filled, expired, was rejected, or was cancelled;
- stream continuity and missing-event recovery.

Whole-account balances are also used to seed local equity and PnL, which violates the accepted per-grid allocation boundary.

### Execution evidence is discarded

The legacy execution-report path uses last and cumulative fill quantities and prices but the strategy fill event is float-based and omits venue trade identity, actual commission quantity and asset, detailed reject/cancel cause, and other evidence needed for exact deduplication and accounting. A parallel PnL ledger derives fees from a configured percentage instead of the venue report.

### Stream reconnect is not recovery

The user-data stream reconnects after a fixed delay and the kline stream reconnects similarly, but neither performs an authoritative gap audit and backfill before allowing decisions to continue. User-stream keepalive failure only logs a warning. The market-data queue drops its oldest candle when full, without creating a gap event or blocking strategy decisions. Reconnection must therefore enter a known degraded/reconciliation state, recover missing facts through authoritative queries, and resume only after continuity requirements pass.

### Failure handling hides evidence

Several event, persistence, strategy, PnL, and shutdown paths catch broad exceptions and continue. This is useful as a catalog of failure surfaces but conflicts with fail-closed invariant and observability requirements. The future runtime must classify failures, retain structured evidence, and make the safety consequence explicit.

## Reusable concepts

The following legacy concepts are useful inputs for redesign:

- an exchange adapter outside the strategy boundary;
- explicit mainnet/testnet endpoint selection;
- stable client identity carried through submit, query, cancellation, and execution events;
- order lookup by venue or client identity;
- public market and private user streams combined with REST observations;
- managed-order discrimination before cancellation;
- startup and periodic reconciliation triggers;
- processing asynchronous fills sequentially on the strategy thread.

They must be reimplemented through the canonical event journal, exact native-asset accounting, full evidence model, fail-closed safety states, and current official Binance contract.

## Requirements the official research must settle

1. Supported Spot order types and the exact post-only mechanism and rejection behavior.
2. Complete order, execution, list, and cancellation status vocabularies and terminal-state semantics.
3. Stable identity fields, uniqueness/reuse constraints, character/length rules, and recovery queries.
4. Trade-level execution and commission evidence required for exact accounting and deduplication.
5. Every applicable symbol, exchange, asset, and account filter and how market/reference prices affect validation.
6. REST authentication, timestamps, receive windows, clock synchronization, permissions, and regional endpoint constraints.
7. Rate-limit dimensions, response headers/body counters, retry and ban behavior, and safe backoff.
8. Timeout, disconnect, 4xx, 5xx, and ambiguous-execution semantics.
9. Public and private stream lifetime, ping/pong, subscription limits, event ordering, reconnection, and gap recovery.
10. Authoritative order, trade, account, balance, and rule queries and their retention windows.
11. Spot Testnet capabilities, differences, resets, data realism, and what it cannot validate.
12. Kline, aggregate-trade, raw-trade, best-bid/offer, and depth availability and granularity for research, replay, and paper trading.


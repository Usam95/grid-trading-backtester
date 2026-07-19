# Grid Trading Resources

## Knowledge

- [Canonical grid semantics decision record](analysis/domain-grid-semantics.md)
  Project authority for selected behavior, rejected alternatives, and downstream questions.
- [Trading engine glossary](docs/domain/trading-engine/CONTEXT.md)
  Canonical project vocabulary; use whenever a term in a lesson is unclear.
- [Binance Spot REST API](https://developers.binance.com/en/docs/products/spot/rest-api)
  First-party source for request security, unknown execution status, rate limits, and trading API behavior.
- [Binance Developer Documentation](https://developers.binance.com/en/docs/introduction)
  First-party index for current Spot interfaces, environments, change information, and production guidance.
- [Binance Spot trading endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade)
  First-party order placement, cancellation, response, and post-only order documentation.
- [Binance Spot user data stream](https://developers.binance.com/en/docs/products/spot/user-data-stream)
  First-party execution reports, order updates, fill quantities, and commission asset fields.
- [Gridlab strategy implementation](gridlab/src/gridlab/strategy/grid.py)
  Current primary source for fill-driven rung pairing and the behavior being superseded by the canonical specification.
- [Gridlab accounting ledger](gridlab/src/gridlab/accounting/ledger.py)
  Current primary source for fill-derived inventory, cash, equity, and closed-trade accounting.
- [Azure Storage redundancy](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy)
  First-party explanation of LRS, ZRS, geographic redundancy, durability, and availability-zone failure behavior.

## Wisdom (Communities)

- [Binance Developer Community](https://developers.binance.com/en)
  Use for exchange-integration questions after checking the official API documentation and changelog.

## Gaps

- Exact risk thresholds, Binance order-state rules, and accounting tolerances remain open wayfinder investigations.

"""Built-in presets, metric metadata, and the grid-trading knowledge base.

This module is the single source of truth for the "informative" parts of the
studio: the curated strategy presets a user can start from, human-readable
metadata for every metric the engine emits, and the grid-trading guide content
surfaced in the Learn tab. Keeping it in the backend means the frontend stays a
thin renderer and the same knowledge can be reused by an API consumer.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Strategy presets — each is a complete, runnable BacktestSpec dict.
# ---------------------------------------------------------------------------

PRESETS: list[dict] = [
    {
        "id": "spot-neutral-range",
        "name": "Spot Neutral — Ranging",
        "tagline": "Classic neutral grid for a sideways market",
        "badge": "Starter",
        "best_for": "Choppy, range-bound markets with no clear trend.",
        "spec": {
            "symbol": "BTCUSDT",
            "market_type": "spot",
            "initial_cash": 10000.0,
            "grid": {"levels": 12, "lower": 92.0, "upper": 108.0,
                     "spacing": "arithmetic", "direction": "neutral"},
            "sizing": {"mode": "fixed_quote", "value": 80.0},
            "fees": {"maker": 0.001, "taker": 0.001},
            "slippage": {"spread_frac": 0.0, "impact_frac": 0.0002},
            "bootstrap": {"base_fraction": 0.5, "side": "LONG"},
            "data": {"kind": "synthetic", "n": 2000, "start_price": 100.0,
                     "seed": 7, "sigma": 0.012, "regime": "range"},
        },
    },
    {
        "id": "binance-btc-live",
        "name": "Binance BTC — Live Data",
        "tagline": "Adaptive long grid on real Binance BTCUSDT history",
        "badge": "Live data",
        "best_for": "An honest, money-relevant run on real market data with real "
                    "Binance fees and lot/tick/min-notional filters.",
        "spec": {
            "symbol": "BTCUSDT",
            "market_type": "spot",
            "venue": "binance",
            "initial_cash": 10000.0,
            "grid": {"levels": 20, "spacing": "geometric", "direction": "long",
                     "adaptive": True, "lookback": 200, "recenter_drift_frac": 0.2},
            "sizing": {"mode": "fixed_quote", "value": 50.0},
            "fees": {"maker": 0.001, "taker": 0.001},
            "slippage": {"spread_frac": 0.0001, "impact_frac": 0.0002},
            "bootstrap": {"base_fraction": 0.0, "side": "LONG"},
            "data": {"kind": "binance", "symbol": "BTCUSDT",
                     "interval": "1h", "max_candles": 1500},
        },
    },
    {
        "id": "spot-long-accumulate",
        "name": "Spot Long — Accumulation",
        "tagline": "Long-only ladder that buys dips and scales out",
        "badge": "Popular",
        "best_for": "Assets you are happy to hold; mild uptrend or recovery.",
        "spec": {
            "symbol": "ETHUSDT",
            "market_type": "spot",
            "initial_cash": 10000.0,
            "grid": {"levels": 16, "lower": 80.0, "upper": 120.0,
                     "spacing": "geometric", "direction": "long"},
            "sizing": {"mode": "fixed_quote", "value": 60.0},
            "fees": {"maker": 0.001, "taker": 0.001},
            "slippage": {"spread_frac": 0.0, "impact_frac": 0.0003},
            "bootstrap": {"base_fraction": 0.0, "side": "LONG"},
            "data": {"kind": "synthetic", "n": 2000, "start_price": 100.0,
                     "seed": 11, "sigma": 0.014, "regime": "range"},
        },
    },
    {
        "id": "adaptive-atr",
        "name": "Adaptive ATR Grid",
        "tagline": "Volatility-aware grid that re-derives its range",
        "badge": "Advanced",
        "best_for": "Markets whose volatility shifts; avoids a stale fixed range.",
        "spec": {
            "symbol": "SOLUSDT",
            "market_type": "spot",
            "initial_cash": 10000.0,
            "grid": {"levels": 14, "spacing": "atr", "direction": "neutral",
                     "adaptive": True, "lookback": 120, "atr_period": 14,
                     "atr_mult": 2.5, "recenter_drift_frac": 0.15},
            "sizing": {"mode": "percent_equity", "value": 0.01},
            "fees": {"maker": 0.001, "taker": 0.001},
            "slippage": {"spread_frac": 0.0, "impact_frac": 0.0003},
            "bootstrap": {"base_fraction": 0.5, "side": "LONG"},
            "data": {"kind": "synthetic", "n": 2500, "start_price": 100.0,
                     "seed": 21, "sigma": 0.02, "regime": "range"},
        },
    },
    {
        "id": "rsi-mean-reversion",
        "name": "RSI Mean-Reversion",
        "tagline": "Only buys dips when RSI says oversold",
        "badge": "Filtered",
        "best_for": "Stops the grid buying into momentum blow-offs; calmer entries.",
        "spec": {
            "symbol": "BTCUSDT",
            "market_type": "spot",
            "initial_cash": 10000.0,
            "grid": {"levels": 16, "lower": 82.0, "upper": 118.0,
                     "spacing": "geometric", "direction": "long"},
            "sizing": {"mode": "fixed_quote", "value": 70.0},
            "filter": {"kind": "rsi", "oversold": 35.0, "overbought": 65.0},
            "fees": {"maker": 0.001, "taker": 0.001},
            "slippage": {"spread_frac": 0.0, "impact_frac": 0.0003},
            "bootstrap": {"base_fraction": 0.0, "side": "LONG"},
            "data": {"kind": "synthetic", "n": 2200, "start_price": 100.0,
                     "seed": 17, "sigma": 0.015, "regime": "range"},
        },
    },
    {
        "id": "trend-filtered",
        "name": "Trend-Filtered Grid",
        "tagline": "Only trades the grid when an EMA filter agrees",
        "badge": "Robust",
        "best_for": "Reducing bleed when a range breaks into a trend.",
        "spec": {
            "symbol": "BTCUSDT",
            "market_type": "spot",
            "initial_cash": 10000.0,
            "grid": {"levels": 14, "lower": 85.0, "upper": 115.0,
                     "spacing": "arithmetic", "direction": "long",
                     "adaptive": False},
            "sizing": {"mode": "fixed_quote", "value": 70.0},
            "filter": {"kind": "trend"},
            "fees": {"maker": 0.001, "taker": 0.001},
            "slippage": {"spread_frac": 0.0, "impact_frac": 0.0003},
            "bootstrap": {"base_fraction": 0.0, "side": "LONG"},
            "data": {"kind": "synthetic", "n": 2200, "start_price": 100.0,
                     "seed": 33, "sigma": 0.015, "regime": "trend"},
        },
    },
]

PRESET_INDEX = {p["id"]: p for p in PRESETS}


# ---------------------------------------------------------------------------
# Venue presets — exchange cost + filter shortcuts for the spot configurator.
# Selecting a venue sets ``spec.venue`` (the engine resolves real tick/lot/
# min-notional filters) plus sensible fee defaults.
# ---------------------------------------------------------------------------

VENUES: list[dict] = [
    {
        "id": "binance",
        "name": "Binance (spot)",
        "market": "Crypto",
        "fees": {"maker": 0.001, "taker": 0.001},
        "note": "0.10% spot fee (0.075% paying with BNB). Applies real tick size, "
                "lot step and min-notional filters per symbol.",
    },
    {
        "id": "ibkr",
        "name": "Interactive Brokers (stocks)",
        "market": "Stocks",
        "fees": {"maker": 0.0005, "taker": 0.0005},
        "note": "Approximate IBKR Pro tiered commission (~0.05%, $0.35 min). Real "
                "commissions are per-share — treat this as an estimate.",
    },
    {
        "id": "",
        "name": "Custom / none",
        "market": "Any",
        "fees": {"maker": 0.001, "taker": 0.001},
        "note": "No venue filters. Set fees and slippage manually.",
    },
]


# ---------------------------------------------------------------------------
# Metric metadata — label, plain-English help, format, and "good direction".
# fmt: pct | num | int | money | ratio | duration
# good: "high" | "low" | "neutral"
# ---------------------------------------------------------------------------

METRIC_META: dict[str, dict] = {
    "total_return": {"label": "Total Return", "fmt": "pct", "good": "high",
                     "help": "Net percentage change of equity over the whole backtest, after fees."},
    "cagr": {"label": "CAGR", "fmt": "pct", "good": "high",
             "help": "Compound annual growth rate — return normalised to a yearly rate."},
    "volatility_annual": {"label": "Volatility (ann.)", "fmt": "pct", "good": "low",
                          "help": "Annualised standard deviation of returns. Lower is steadier."},
    "sharpe": {"label": "Sharpe", "fmt": "ratio", "good": "high",
               "help": "Risk-adjusted return: mean return divided by volatility, annualised."},
    "sortino": {"label": "Sortino", "fmt": "ratio", "good": "high",
                "help": "Like Sharpe but only penalises downside volatility."},
    "max_drawdown": {"label": "Max Drawdown", "fmt": "pct", "good": "low",
                     "help": "Largest peak-to-trough equity decline. The pain you must survive."},
    "max_drawdown_duration": {"label": "Max DD Duration", "fmt": "int", "good": "low",
                              "help": "Longest stretch (in bars) spent below a previous equity peak."},
    "calmar": {"label": "Calmar", "fmt": "ratio", "good": "high",
               "help": "CAGR divided by max drawdown. Reward per unit of worst-case pain."},
    "fee_drag": {"label": "Fee Drag", "fmt": "pct", "good": "low",
                 "help": "Total fees paid as a fraction of starting capital. Grids trade a lot — watch this."},
    "n_trades": {"label": "Closed Trades", "fmt": "int", "good": "neutral",
                 "help": "Number of round-trip trades the grid completed."},
    "win_rate": {"label": "Win Rate", "fmt": "pct", "good": "high",
                 "help": "Share of closed trades that were profitable. Grids usually win often, small."},
    "avg_trade_pnl": {"label": "Avg Trade PnL", "fmt": "money", "good": "high",
                      "help": "Mean profit/loss per closed trade, in quote currency."},
    "avg_win": {"label": "Avg Win", "fmt": "money", "good": "high",
                "help": "Mean profit of winning trades."},
    "avg_loss": {"label": "Avg Loss", "fmt": "money", "good": "high",
                 "help": "Mean loss of losing trades (negative)."},
    "profit_factor": {"label": "Profit Factor", "fmt": "ratio", "good": "high",
                      "help": "Gross profit divided by gross loss. >1 is profitable; >1.5 is healthy."},
    "expectancy": {"label": "Expectancy", "fmt": "money", "good": "high",
                   "help": "Expected profit per trade = win_rate*avg_win + loss_rate*avg_loss."},
    "largest_win": {"label": "Largest Win", "fmt": "money", "good": "high",
                    "help": "Biggest single winning trade."},
    "largest_loss": {"label": "Largest Loss", "fmt": "money", "good": "high",
                     "help": "Biggest single losing trade — often the unbounded-inventory tail."},
    "avg_bars_held": {"label": "Avg Hold (bars)", "fmt": "num", "good": "neutral",
                      "help": "Average number of bars a position is held before closing."},
    "psr": {"label": "Prob. Sharpe Ratio", "fmt": "pct", "good": "high",
            "help": "Probability the true Sharpe exceeds zero given sample length and shape."},
    "deflated_sharpe": {"label": "Deflated Sharpe", "fmt": "pct", "good": "high",
                        "help": "Sharpe discounted for the number of configurations tried — your best "
                                "guard against an over-fit backtest. Low after a big sweep is a red flag."},
    # --- grid economics (v1.1 money-relevance metrics) ---
    "return_over_buy_hold": {"label": "Return vs Buy & Hold", "fmt": "pct", "good": "high",
                             "help": "Grid return minus simply holding over the same period. The bottom "
                                     "line: did the bot actually beat doing nothing?"},
    "fee_to_profit_ratio": {"label": "Fee-to-Profit", "fmt": "ratio", "good": "low",
                            "help": "Fees paid divided by net profit. Below ~0.3 is healthy; 1.0 means "
                                    "fees ate the entire edge — you traded for the exchange."},
    "avg_capital_utilization": {"label": "Capital Used", "fmt": "pct", "good": "neutral",
                                "help": "Average share of capital actually deployed as inventory. Low = "
                                        "idle cash dragging returns; high = little dry powder for dips."},
    "trades_per_day": {"label": "Trades / Day", "fmt": "num", "good": "neutral",
                       "help": "Average round-trips per day. More trades means more fee exposure and "
                               "more dependence on your cost assumptions being right."},
    "avg_round_trip_bps": {"label": "Avg Round-trip", "fmt": "num", "good": "high",
                           "help": "Average net profit per completed round-trip in basis points, after "
                                   "fees. Must clear your spacing's cost to compound."},
    "time_in_market_frac": {"label": "Time in Market", "fmt": "pct", "good": "neutral",
                            "help": "Fraction of bars the grid held any inventory — its exposure footprint."},
    "realized_grid_pnl": {"label": "Realised Grid PnL", "fmt": "money", "good": "high",
                          "help": "Net realised profit booked by completed grid round-trips, after fees."},
}

# The KPIs shown in the headline strip, in display order.
HEADLINE_METRICS = [
    "total_return", "return_over_buy_hold", "max_drawdown", "sharpe",
    "profit_factor", "fee_to_profit_ratio", "win_rate", "deflated_sharpe",
]

# Grid-economics metrics surfaced in the dedicated Economics tab.
ECONOMICS_METRICS = [
    "return_over_buy_hold", "fee_to_profit_ratio", "avg_capital_utilization",
    "trades_per_day", "avg_round_trip_bps", "time_in_market_frac",
    "realized_grid_pnl", "fee_drag",
]


# ---------------------------------------------------------------------------
# Grid-trading knowledge base (Learn tab). Distilled from the analysis report.
# ---------------------------------------------------------------------------

GUIDE: dict = {
    "intro": (
        "A grid bot places a ladder of buy and sell limit orders at fixed price "
        "intervals. Each filled buy arms a sell one rung higher (and vice-versa), "
        "so the strategy mechanically 'buys low, sells high' inside a range and "
        "harvests volatility. It needs no directional forecast — only that price "
        "keeps oscillating through the rungs."
    ),
    "sections": [
        {
            "title": "When grid trading works",
            "tone": "good",
            "points": [
                "Range-bound / sideways markets where price oscillates within a band.",
                "High realised volatility relative to the fee + spacing cost per rung.",
                "Liquid pairs with tight spreads so maker fills are cheap.",
                "When spacing comfortably exceeds round-trip fees, so each cycle nets a profit.",
            ],
        },
        {
            "title": "When grid trading fails",
            "tone": "bad",
            "points": [
                "Strong trends: a long grid keeps buying into a falling market, accumulating "
                "an underwater bag (the classic 'death by a thousand buys').",
                "Breakouts beyond the grid bounds leave the bot idle or over-exposed.",
                "Thin spacing that does not cover fees turns activity into pure fee bleed.",
                "Leverage + inventory build-up can hit liquidation before mean-reversion arrives.",
            ],
        },
        {
            "title": "Major risks",
            "tone": "warn",
            "points": [
                "Unbounded inventory: without caps, a trending market grows exposure without limit.",
                "Drawdown tail risk: many small wins can be erased by one large adverse move.",
                "Fee drag: hundreds of round-trips make taker fees and slippage material.",
                "Over-fitting: a grid tuned to one window often dies out-of-sample — always "
                "check the deflated Sharpe and walk-forward results.",
            ],
        },
        {
            "title": "Robustness levers",
            "tone": "info",
            "points": [
                "Trend / regime filters pause buying when an EMA or ADX says 'trending'.",
                "Inventory & gross-exposure caps bound the worst-case bag.",
                "Stop-loss / take-profit on the whole grid bound the tail.",
                "ATR-based adaptive spacing keeps the grid sized to current volatility.",
                "Walk-forward + Monte Carlo expose fragility a single backtest hides.",
            ],
        },
    ],
    "regimes": [
        {"key": "range", "label": "Ranging", "verdict": "good",
         "note": "The home turf of grid trading — oscillation pays the ladder."},
        {"key": "trend", "label": "Trending", "verdict": "bad",
         "note": "Hostile. Use a trend filter, tight inventory caps, or step aside."},
        {"key": "random", "label": "Random walk", "verdict": "warn",
         "note": "Coin-flip. Edge is thin; fees decide whether you bleed."},
    ],
    "sources": [
        {"label": "Investopedia — Grid Trading", "url": "https://www.investopedia.com/terms/g/grid-trading.asp"},
        {"label": "Pionex — Grid Trading Bot guide", "url": "https://www.pionex.com/blog/grid-trading-bot/"},
        {"label": "Binance Academy — What Is Grid Trading", "url": "https://academy.binance.com/en/articles/what-is-grid-trading"},
        {"label": "Binance — Spot Trading Fee Schedule", "url": "https://www.binance.com/en/fee/schedule"},
        {"label": "Interactive Brokers — US Stock Commissions", "url": "https://www.interactivebrokers.com/en/pricing/commissions-stocks.php"},
        {"label": "Bailey & López de Prado — Deflated Sharpe Ratio", "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551"},
    ],
}

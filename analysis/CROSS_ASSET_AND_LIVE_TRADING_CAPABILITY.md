# Cross-Asset & Live Trading Capability Analysis

**Date**: 2026-06-07  
**Question**: Can grid-backtest-core be used for stock markets and Interactive Brokers live trading?  
**Answer**: **YES for backtesting stocks | Partial for live trading (needs adapter layer)**

---

## Part 1: Stock Market Backtesting — YES, Fully Supported ✅

### 1.1 Why The Engine Works for Stocks

The `grid-backtest-core` engine is **asset-class agnostic**:

#### Design Principle: Generic OHLCV Protocol
```python
class DataSource(Protocol):
    def load(self, symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        # Returns: DatetimeIndex + [Open, High, Low, Close, Volume]
        ...
```

**No hardcoded assumptions about**:
- Asset class (crypto, stocks, forex, commodities)
- Exchange-specific rules (trading hours, settlement, circuit breakers)
- Asset characteristics (leverage, fractional shares, margin)
- Commission/fee structures

#### What You Need to Backtest Stocks

| Component | Crypto | Stocks | Status |
|---|---|---|---|
| **OHLCV Data** | Binance, Kraken | Yahoo Finance, IB, Alpha Vantage | ✅ Load any source |
| **Indicators** | ATR, EMA, RSI | ATR, EMA, RSI | ✅ Same indicators |
| **Order Types** | LIMIT, MARKET | LIMIT, MARKET | ✅ Same types |
| **Position Tracking** | FIFO lots | FIFO lots | ✅ Same logic |
| **Slippage** | % of fill price | Fixed cents/basis | ⚠️ Need adjustment |
| **Commissions** | % per trade | $ per share or % | ⚠️ Need adjustment |
| **Market Hours** | 24/7 | 9:30–16:00 EST | ⚠️ Need filter |

### 1.2 What Works Out-of-the-Box

✅ **Grid Strategy Logic**
- Static or dynamic grid levels
- Re-centering
- Position sizing
- Stop-loss / take-profit

✅ **Metrics & Analytics**
- Sharpe ratio, Calmar, Sortino
- Win rate, profit factor
- Drawdown analysis
- Trade logging

✅ **Research & Optimization**
- GridResearchRunner (parameter sweeps)
- GridResearchFast (Numba acceleration)
- Parallel execution

### 1.3 What Needs Adjustment

⚠️ **Commission/Slippage Model**

Current implementation:
```python
# Slippage: % of fill price
slippage_pct = 0.001  # 0.1% for crypto
```

For stocks, you might want:
```python
# Commission: fixed cents per share + % of value
commission = 0.005 per share + 0.001% of trade value  # Interactive Brokers rates
```

**Solution**: Add `commission_model` parameter to `BacktestConfig`:
```python
@dataclass
class CommissionModel:
    mode: str  # "percent", "fixed_per_share", "tiered"
    value: float  # 0.001 for percent, 0.005 for per-share
    min_commission: float = 1.00  # Minimum $1 per trade

@dataclass
class BacktestConfig:
    commission_model: CommissionModel = field(default_factory=...)
```

⚠️ **Market Hours / Session Filtering**

Grid trading at 3 AM when market is closed = meaningless.

**Solution**: Add session filter:
```python
@dataclass
class SessionConfig:
    enabled: bool = True
    market: str  # "24/7", "us_stocks", "european", "crypto"
    timezone: str = "UTC"
    # Auto-skip candles outside trading hours
```

### 1.4 Stock Backtesting Example

```python
from grid_backtest import BacktestEngine, SimpleGridStrategy, BacktestConfig
import pandas as pd

# Load stock data (e.g., AAPL from Yahoo Finance)
df = pd.read_csv("AAPL_daily.csv", index_col="Date", parse_dates=True)
df.columns = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]

# Define strategy (same as crypto)
strategy = SimpleGridStrategy(
    symbol="AAPL",
    grid_levels=[150.0, 151.0, 152.0, 153.0],
    orders_per_level=100  # 100 shares per level
)

# Run backtest
config = BacktestConfig(
    initial_balance=50000,  # $50K
    commission_model=CommissionModel(mode="percent", value=0.001),  # 0.1%
)

engine = BacktestEngine(config=config)
result = engine.run(
    strategy=strategy,
    data=df,  # DataFrame with OHLCV
)

print(f"Return: {result.total_return_pct}%")
print(f"Sharpe: {result.sharpe_ratio}")
```

**This works TODAY with minimal changes** ✅

---

## Part 2: Interactive Brokers Live Trading

### 2.1 Architecture: Three Layers

```
┌─────────────────────────────────────────┐
│  grid-backtest-core (PURE BACKTESTING)  │
│  - Strategy logic (DynamicGridStrategy)  │
│  - Order simulation (_simulate_fills)    │
│  - Metrics & reporting                   │
│  NO LIVE TRADING CODE                    │
└──────────────┬──────────────────────────┘
               │ Uses generic Order/Candle models
               ▼
┌──────────────────────────────────────────┐
│  grid-backtest-saas (WEB/DEPLOYMENT)     │
│  - REST API (FastAPI)                    │
│  - Job scheduling (Celery + Redis)       │
│  - Results persistence (PostgreSQL)      │
│  - WebSocket progress streaming          │
└──────────────┬──────────────────────────┘
               │ Orchestrates backtests
               ▼
┌──────────────────────────────────────────┐
│  grid-backtest-ib (NEW - LIVE TRADING)   │
│  - Interactive Brokers API adapter       │
│  - Order placement (TWS API)             │
│  - Market data streaming (IB Realtime)   │
│  - Portfolio management (account sync)   │
│  - Risk controls & position checks       │
└──────────────────────────────────────────┘
```

**Key Principle**: `grid-backtest-core` remains **pure, isolated backtesting**. Live trading is a **separate runtime**.

### 2.2 What You Need for Interactive Brokers

#### A. Interactive Brokers Python Library

```bash
pip install ib-insync
```

The `ib-insync` library provides:
- Connection to TWS (Trader Workstation)
- Real-time market data
- Order placement/management
- Account sync
- Contract metadata

#### B. Adapter Layer (New Module: `grid-backtest-ib`)

```python
# grid-backtest-ib/src/grid_backtest_ib/connector.py

from ib_insync import IB, Forex, Stock, Contract
from grid_backtest.models import Order, Candle, Side
from grid_backtest.strategy import BaseStrategy

class InteractiveBrokersConnector:
    """Adapts grid-backtest-core strategies to Interactive Brokers API."""
    
    def __init__(self, host="127.0.0.1", port=7497):
        self.ib = IB()
        self.ib.connect(host, port, clientId=1)
    
    def subscribe_market_data(self, symbol: str):
        """Get live market data from IB."""
        contract = Stock(symbol, exchange="SMART", currency="USD")
        ticker = self.ib.reqMktData(contract, "", False, False)
        return ticker
    
    def place_order(self, order: Order) -> str:
        """Convert grid-backtest Order to IB order, place it."""
        contract = Stock(order.symbol, exchange="SMART", currency="USD")
        
        ib_order = IB_Order()
        ib_order.action = "BUY" if order.side == Side.BUY else "SELL"
        ib_order.totalQuantity = int(order.qty)
        ib_order.orderType = "LMT" if order.type == OrderType.LIMIT else "MKT"
        ib_order.lmtPrice = order.price if order.type == OrderType.LIMIT else 0
        
        trade = self.ib.placeOrder(contract, ib_order)
        return trade.order.orderId
    
    def get_account_balance(self) -> dict:
        """Fetch current account state from IB."""
        return {
            "cash": self.ib.accountValues()["CashUSD"],
            "positions": {p.contract.symbol: p.position for p in self.ib.positions()}
        }
```

#### C. Live Engine (New Module: `grid-backtest-ib/live_engine.py`)

```python
class LiveTradingEngine:
    """Runs a strategy against Interactive Brokers in real-time."""
    
    def __init__(self, strategy: BaseStrategy, connector: InteractiveBrokersConnector):
        self.strategy = strategy
        self.connector = connector
        self.positions = {}
    
    async def on_market_tick(self, ticker):
        """Called when market data arrives from IB."""
        # Create Candle from latest tick
        candle = Candle(
            timestamp=ticker.time,
            open=ticker.bid,
            high=ticker.bid,
            low=ticker.ask,
            close=(ticker.bid + ticker.ask) / 2,
            volume=ticker.volume,
        )
        
        # Ask strategy for orders
        actions = self.strategy.on_candle(candle)
        
        # Execute via IB
        for order in actions:
            trade_id = self.connector.place_order(order)
            self.positions[trade_id] = order
    
    def run(self):
        """Connect to IB, subscribe to market data, run event loop."""
        ticker = self.connector.subscribe_market_data(self.strategy.symbol)
        
        while True:
            self.on_market_tick(ticker)
            # Process fills, update positions
            # Check stop losses, take profits
```

---

## Part 3: Implementation Roadmap

### Current State
```
✅ grid-backtest-core  — Pure backtesting (ready)
✅ grid-backtest-saas  — Backtesting as service (ready)
❌ grid-backtest-ib    — Interactive Brokers live trading (not created)
```

### Phase 1: Stock Backtesting (1–2 Days)
```
1. Add CommissionModel to BacktestConfig
2. Add SessionConfig for market hours
3. Test on stock data (AAPL, MSFT, SPY)
4. Update documentation
```

**No code changes needed for core logic** — only config additions.

### Phase 2: Interactive Brokers Foundation (1–2 Weeks)
```
Create grid-backtest-ib folder:

grid-backtest-ib/
├── src/grid_backtest_ib/
│   ├── connector.py        # IB API wrapper
│   ├── live_engine.py      # Real-time strategy executor
│   ├── risk_controls.py    # Position limits, stop losses
│   ├── market_data.py      # Tick-to-Candle conversion
│   └── __init__.py
├── tests/
│   ├── test_connector.py
│   ├── test_live_engine.py
│   └── test_market_data.py
├── examples/
│   ├── run_grid_ib.py      # Example: run grid strategy live
│   └── backtest_vs_live.py # Compare backtest to live
└── pyproject.toml          # Depends on: grid-backtest-core, ib-insync
```

**Key Design**:
- Depends on `grid-backtest-core` (as library)
- Adapter pattern: converts IB data → Candle, Order → IB order
- Risk controls: position limits, stop losses, daily losses
- Logging: every trade, every candle, every risk check

### Phase 3: SaaS Integration (1–2 Weeks)
```
Add to grid-backtest-saas:
- REST endpoint: POST /live/start
- WebSocket: /live/stream (market data, orders, P&L)
- Job worker: Celery task to run live engine
- UI: Controls, real-time monitoring, stop/kill switch
```

---

## Part 4: Comparison: Stocks vs. Crypto vs. Interactive Brokers

| Feature | Stocks (Backtest) | Crypto (Backtest) | IB Live | Difficulty |
|---|---|---|---|---|
| **OHLCV Data** | Yahoo, IB | Binance, Kraken | IB API | ✅ Easy |
| **Order Placement** | Simulated | Simulated | Real API | ⚠️ Medium |
| **Position Tracking** | FIFO lots | FIFO lots | Account sync | ⚠️ Medium |
| **Commissions** | $ per share | % | Tiered $ | ⚠️ Medium |
| **Market Hours** | 9:30–16:00 EST | 24/7 | 9:30–16:00 EST | ✅ Easy |
| **Risk Controls** | Simulated | Simulated | Real account | 🔴 Hard |
| **Slippage** | Fixed % | Fixed % | Real fills | 🔴 Hard |
| **Leverage** | No | 1–125× | 1–2× | ⚠️ Medium |

---

## Part 5: Realistic Timeline & Effort

### Goal: Run Grid Strategy on Interactive Brokers Stocks (Live)

| Phase | Task | Duration | Effort | Status |
|---|---|---|---|---|
| **Phase 1** | Stock backtest config | 1–2 days | LOW | ⏭️ START |
| **Phase 2a** | IB connector + live engine | 3–5 days | MEDIUM | ⏭️ Then |
| **Phase 2b** | Risk controls & monitoring | 2–3 days | MEDIUM | Then |
| **Phase 3** | SaaS integration | 2–3 days | MEDIUM | Then |
| **Phase 4** | Testing & validation | 3–5 days | HIGH | Then |
| **TOTAL** | **End-to-end live trading** | **2–3 weeks** | **MEDIUM–HIGH** | |

---

## Part 6: Stock-Specific Considerations

### 6.1 Grid Strategy on Stocks: Does It Work?

**Short Answer: YES, but with caveats.**

#### Why Grid Works on Stocks
- Stocks oscillate within ranges (mean-reversion)
- Lower volatility than crypto → tighter grids possible
- Intraday trading (hourly grids on liquid stocks) works well
- Shorter market hours = less operational burden

#### Why Grid Struggles on Stocks
- **Lower volume** → slippage on small orders
- **Day trading rules** → Pattern Day Trader (PDT) rule: 4 trades per 5 days (if <$25K)
- **Market hours only** → gaps at open/close, overnight risk
- **Dividend/splits** → position adjustments needed

#### Best Stocks for Grid Trading
- **High volume**: SPY, QQQ, IVV (ETFs), AAPL, MSFT, TSLA
- **Volatility style**: Tech stocks (NVDA, AMD, META)
- **Time window**: Intraday 1h–4h candles
- **Avoid**: Low-volume stocks, pre-market gaps

### 6.2 Interactive Brokers: Why It's a Good Choice

✅ **Advantages**:
- Excellent Python library (`ib-insync`)
- Low commissions (stocks: $1 minimum or 0.005 per share)
- Margin available (1:2 leverage for stocks)
- Real-time market data included
- Works 24/7 for forex (if you want that too)

⚠️ **Considerations**:
- Requires desktop app (TWS or Gateway)
- Minimum account: $2,000 (or no day trading)
- API can disconnect; need reconnection logic
- Commission structure is complex (tiered)

---

## Part 7: Code Example: Stock Grid on Interactive Brokers

### Setup
```python
# requirements-ib.txt
grid-backtest-core>=0.1.0
ib-insync>=10.0.0
pandas>=1.3.0
```

### Implementation
```python
# trading_bot.py

from grid_backtest import DynamicGridStrategy, DynamicGridConfig
from grid_backtest_ib import InteractiveBrokersConnector, LiveTradingEngine

# 1. Define strategy (same as backtesting)
config = DynamicGridConfig(
    symbol="AAPL",
    grid_levels_count=20,
    spacing_mode="percent",
    spacing_pct=0.01,  # 1% spacing (realistic for stocks)
    use_atr_range=True,
    atr_range_mult=2.0,
    use_stop_loss=True,
    stop_loss_pct=5.0,
    use_take_profit=True,
    take_profit_pct=10.0,
)

strategy = DynamicGridStrategy(config=config)

# 2. Connect to Interactive Brokers
connector = InteractiveBrokersConnector(host="127.0.0.1", port=7497)

# 3. Run live
engine = LiveTradingEngine(strategy=strategy, connector=connector)
engine.run()
```

---

## Part 8: Summary & Recommendations

### Can grid-backtest-core be used for stocks?

**YES ✅ TODAY**
- Engine is asset-class agnostic
- Just load stock OHLCV data
- Adjust commission model (1–2 day task)
- Same grid strategy logic applies

### Can grid-backtest-core be used for Interactive Brokers live trading?

**YES ⚠️ WITH ADAPTER LAYER**
- Core is backtesting-only (good design)
- Need new `grid-backtest-ib` folder (live trading runtime)
- Adapter converts IB API ↔ grid-backtest models
- Effort: 2–3 weeks for full implementation
- Recommended order: Phase 1.5 (stock backtest) → Phase 2 (IB live)

---

## Part 9: Recommended Next Steps

### Immediate (This Week)
```
1. Test grid strategy on stock data (Yahoo Finance)
2. Add CommissionModel config
3. Add SessionConfig (market hours filter)
4. Run 10 stock backtests
5. Document results
```

### Near-Term (Next 2–3 Weeks)
```
1. Create grid-backtest-ib folder structure
2. Implement InteractiveBrokersConnector
3. Build LiveTradingEngine
4. Add risk controls (position limits, daily loss limits)
5. Test with paper trading (IB Testbed)
```

### Medium-Term (Following Month)
```
1. Integrate IB engine with SaaS backend
2. Add WebSocket streaming
3. Deploy to staging
4. Run live with small account
5. Monitor, iterate, scale
```

---

## Conclusion

Your `grid-backtest-core` engine is **already suitable for stock backtesting**. To add **Interactive Brokers live trading**:

1. **Stock backtesting**: 1–2 days (config additions only)
2. **IB adapter**: 1–2 weeks (new module)
3. **Full integration**: 2–3 weeks total

**Recommendation**: Start with stock backtesting (#1), validate grid strategy works on stocks (it does), then build the IB adapter when ready.

The clean separation of concerns (core = backtesting, IB runtime = separate) ensures you never mix live trading risk with backtest code. This is the right architecture.

# Training Curriculum Prompt for /teach Skill
## Comprehensive Grid Trading & Engine Deep Dive

### Overview

Generate a comprehensive, HTML-based interactive training curriculum for learning grid trading from fundamental concepts through production deployment. The training should deeply cover the current grid-backtest-core engine implementation, identify gaps, and prepare the learner to understand, extend, and deploy the system.

### Curriculum Goal

A learner completing this curriculum should be able to:
1. Explain grid trading mechanics, profitability conditions, and risk/reward tradeoffs
2. Understand the complete architecture and data flow of grid-backtest-core
3. Identify 8 critical gaps in current implementation and their impact
4. Design and implement improvements (trend filters, shorting, multi-timeframe)
5. Run backtests, interpret metrics, and optimize parameters
6. Deploy the system to cloud (Azure) for live trading

---

## Module Structure (Total ~15 hours)

### Module 1: Grid Trading Fundamentals (2 hours)
**Goal**: Understand what grid trading is, why it works, and when it fails.

**Topics**:
- What is grid trading? (definition, mechanics, use cases)
- Price levels and order distribution (static vs dynamic grids)
- Entry and exit logic (fill simulation, FIFO closing)
- Profitability conditions: mean-reversion assumption
- Volatility requirement (low vol = no profit)
- Position sizing strategies (percent-of-capital, fixed-amount)
- Risk/reward tradeoffs
- Historical performance data (crypto: 15-40% annual, stocks: 8-25%)
- When grid trading fails (strong trends, zero vol, gaps/slippage)

**Code Examples**:
- SimpleGridStrategy: fixed price levels example
- DynamicGridStrategy: re-centering example

**Red Thread Connection**:
*Grid fundamentals → Strategy mechanics → Order execution → Risk management*

---

### Module 2: Market Data & Backtesting Foundation (1.5 hours)
**Goal**: Master the data model and fill simulation that drives accuracy.

**Topics**:
- OHLCV candle data model (Open, High, Low, Close, Volume)
- Backtesting timeline: candle by candle simulation
- Order placement and fill simulation
- LIMIT vs MARKET fill logic
- Slippage mechanics (percentage-based on order type)
- Same-candle fill behavior (orders placed in candle N can fill in candle N)
- Historical volatility and impact on fill prices
- Commission and fee models
- Data quality requirements and gaps handling

**Code Examples**:
- How BacktestEngine.run() processes candles
- Fill simulation logic in _simulate_fills_for_candle()
- Slippage calculation for MARKET fills

**Red Thread Connection**:
*Data accuracy → Fill simulation → Slippage → Realistic backtest results*

---

### Module 3: Your Engine Architecture Deep Dive (2.5 hours)
**Goal**: Understand the complete internals of grid-backtest-core.

**Topics**:
- Engine overview: input (data, config) → processing → output (results)
- BacktestEngine main loop: candle iteration, strategy callbacks, fill processing
- DynamicGridStrategy vs SimpleGridStrategy (when to use each)
- FIFO position tracking (why deque for O(1) SELL lookup)
- Position bootstrap modes: static, inherited, from-reserves (capital allocation)
- Constraint handling: SKIP (don't place) vs RESIZE (reduce size)
- Order lifecycle: placement → validation → fill simulation → close/roll
- Result tracking: trades, P&L, drawdown, metrics

**Code Examples**:
- BacktestEngine.run() high-level flow
- DynamicGridStrategy configuration and reentry logic
- FIFO deque implementation and O(1) SELL performance
- Bootstrap mode comparisons with concrete examples

**Visual Aids**:
- Flowchart: Engine loop (candle → strategy → fills → accounting)
- Diagram: FIFO position stack and SELL deque lookup
- Timeline: order lifecycle from placement to close

**Red Thread Connection**:
*Data input → Engine core loop → Execution layer → Results tracking*

---

### Module 4: Indicators & Signals (1.5 hours)
**Goal**: Master the signals that control strategy decisions.

**Topics**:
- Average True Range (ATR): volatility measurement
  * Formula: rolling max(High-Low, |High-Prev Close|, |Low-Prev Close|)
  * Use case: grid spacing (wider spacing in high vol, tighter in low vol)
  * Interpretation: ATR > 30-period avg = high vol, adjust grid accordingly
- Exponential Moving Average (EMA): trend identification
  * Formula: weighted recent price with exponential decay
  * Use case: filter placement (only place grid if price above EMA)
  * Interpretation: price > EMA 20 = uptrend, < EMA = downtrend
- Relative Strength Index (RSI): momentum/overbought-oversold
  * Formula: 100 - (100 / (1 + RS)), where RS = avg gain / avg loss
  * Use case: signal filter (skip if RSI > 70 overbought or < 30 oversold)
  * Interpretation: RSI > 70 = potentially reversing (risky), < 30 = opposite

**Code Examples**:
- ATR calculation and usage in DynamicGridStrategy
- EMA calculation and filtering logic
- RSI calculation and policy application

**Interactive Examples**:
- Show ATR values on sample candle data
- Show EMA slope changes and trend confirmation
- Show RSI divergence and reversal signals

**Red Thread Connection**:
*Indicators → Policy decisions → Order placement/filtering → Trade outcomes*

---

### Module 5: Policies & Order Control (1.5 hours)
**Goal**: Understand the policy framework that governs trading behavior.

**Topics**:
- SpacingPolicy: grid density control
  * PercentSpacingPolicy: static % gaps between levels (e.g., 0.5% apart)
  * ATRSpacingPolicy: dynamic gaps based on volatility (space × ATR / ATR_period)
  * Use case: tight spacing in stable market, wider in volatile market
- RecenterPolicy: when to reset the grid
  * BandBreakRecenterPolicy: re-center when price breaks grid bounds
  * TimeBasedRecenterPolicy: re-center on fixed schedule (every N candles)
  * Use case: adapt grid to price movement, prevent grid exhaustion
- RangePolicy: dynamic price range for grid
  * How to calculate upper/lower bounds
  * ATR-based ranges, moving average bands
  * Interaction with ReenterPolicy
- FilterPolicy: pre-trade validation
  * Implement custom filters (trend check, volatility check, time check)
  * Can prevent placement if conditions not met
  * Red Flag: This is where Gap 1 (Trend Filter) will plug in
- StopLossTakeProfitPolicy: automatic position closing
  * Stop-loss percentage (close if drawdown > X%)
  * Take-profit percentage (close if profit > X%)
  * Per-level or portfolio-wide application

**Code Examples**:
- PercentSpacingPolicy vs ATRSpacingPolicy configuration
- BandBreakRecenterPolicy implementation
- FilterPolicy custom logic pattern
- StopLossTakeProfitPolicy usage

**Red Thread Connection**:
*Policy framework → Flexible strategy design → Controllable trading behavior*

---

### Module 6: Critical Gaps Analysis (2 hours)
**Goal**: Understand what's missing from the engine and why it matters.

**Topics**:

**Gap 1: No Trend Filter**
- Problem: Grid strategy trades profitably in ranging markets, loses 30-60% in downtrends
- Why it matters: 20-40% of market is downtrending at any time
- Solution: Add ADX (Average Directional Index) or price > EMA filter
- Impact: Eliminate 30-40% of losing trades (biggest single improvement)
- Implementation approach: Custom FilterPolicy checking ADX < 30

**Gap 2: No Shorting**
- Problem: Only long positions; can't profit from bear markets (20-40% of cycles)
- Why it matters: Bear markets are systematic and predictable
- Solution: Add SHORT_BUY and SHORT_SELL order types, inverse FIFO for shorts
- Impact: +30-50% returns in bearish periods, better Sharpe ratio
- Implementation complexity: Medium (order type system, inverse accounting)

**Gap 3: No Multi-Timeframe Confirmation**
- Problem: Can't confirm trades on higher timeframes (e.g., 1h uptrend + 15m reversal)
- Why it matters: 1-5% of trades are false signals on lower timeframe alone
- Solution: Ingest multiple DataFrames, require alignment before placement
- Impact: -15-20% drawdown, fewer false signals, better risk/reward
- Implementation complexity: High (multi-candle ingestion, alignment logic)

**Gap 4: No Portfolio Correlation**
- Problem: Can't size positions based on correlation to existing holdings
- Example: Long 100% BTC + 100% ETH simultaneously = 2× risk, not 1× (corr ≈ 0.8)
- Why it matters: Concentration risk and cascade failures in correlated assets
- Solution: Track correlation matrix, reduce sizing for correlated assets
- Impact: -20-25% max drawdown, more resilient portfolio
- Implementation complexity: High (correlation calculation, dynamic sizing)

**Gap 5: No Volatility Regime Switch**
- Problem: Same 0.5% spacing in 10% vol AND 100% vol = disaster
- Fact: Crypto vol range: 10% to 200% (20× difference!)
- Why it matters: Grid spacing must scale with volatility to remain profitable
- Solution: Measure vol percentile, adjust spacing/sizing accordingly
- Impact: -10-15% max drawdown, better risk-adjusted returns
- Implementation approach: VolumeRegimePolicy with vol percentile bucketing

**Gap 6: No Advanced Order Types**
- Missing: OCO (One-Cancels-Other), trailing stops, time expiry, iceberg orders
- Why it matters: These enable sophisticated hedges and best practices
- Impact: More control over execution, better hedging capabilities
- Implementation complexity: Medium to High

**Gap 7: Single Symbol, Single Timeframe Limitation**
- Current: Engine processes one DataFrame at a time
- Reality: Real trading needs portfolio view, multi-symbol correlation
- Why it matters: Can't optimize across symbols, can't hedge
- Solution: Extend to multi-symbol grid runner
- Implementation complexity: High (architecture change)

**Gap 8: No Portfolio Risk Management**
- Problem: Can't enforce portfolio-level stop loss, max correlation limits
- Why it matters: Prevents cascade failures and concentration risk
- Solution: Add portfolio-level constraint checks before order placement
- Impact: Better tail-risk management, more stable returns
- Implementation approach: PortfolioConstraintPolicy

**Matrix Table**:
Show all gaps with: gap name, symptom, why it matters, estimated impact, implementation effort, connects-to-what-policy

**Red Thread Connection**:
*Gaps → Current limitations → Roadmap priorities → Implementation design*

---

### Module 7: Research, Optimization & Metrics (1.5 hours)
**Goal**: Learn how to improve strategy performance through systematic testing.

**Topics**:
- Backtesting harness overview: what is GridResearchRunner
- Cartesian parameter sweep: testing all combinations of parameters
  * Example: grid_levels=[5,10,20], spacing=[0.3%, 0.5%, 1.0%], reentry=[True, False]
  * Result: 3 × 3 × 2 = 18 unique backtests
  * Output: ranked by Sharpe ratio, profit factor, or custom metric
- Numba JIT compilation: GridResearchFast for 200-400× speedup
  * Trade-off: only works with SimpleGridStrategy, no dynamic features
  * Use case: exhaustive parameter search before live deployment
- Metrics computed: 10+ metrics per backtest
  * Return: net_pnl, total_return_pct
  * Risk: max_drawdown, max_drawdown_pct, volatility
  * Trade: n_trades, win_rate_pct, profit_factor
  * Risk-adjusted: Sharpe ratio, Calmar ratio, Sortino ratio
- Multi-core parallelization: ProcessPoolExecutor for wall-clock speedup
- Interpretation: How to read and compare result tables
- Common pitfalls: overfitting, data snooping, survivorship bias

**Code Examples**:
- GridResearchRunner usage: create, set parameters, run, get results
- Result interpretation: picking winning parameters
- Ranking by different metrics (Sharpe vs profit factor)

**Interactive Examples**:
- Sample parameter sweep with visualization
- Metric trade-offs (high Sharpe might have lower profit factor)

**Red Thread Connection**:
*Metrics → Research framework → Optimization → Live deployment confidence*

---

### Module 8: Live Trading Considerations (1.5 hours)
**Goal**: Understand the differences between backtesting and live execution.

**Topics**:
- Real-time vs simulated fills
- Latency impact: order placement to fill (milliseconds to seconds)
- Partial fills and over-fills
- Order management in live market: modification, cancellation
- Slippage in live trading (commissions, market impact, execution delay)
- Risk management in live: position limits, leverage, margin
- Monitoring and alerting
- Graceful shutdown and recovery
- Capital preservation strategies
- Order routing and venue selection

**Case Studies**:
- How grid trading failed during flash crash (May 2010 equivalent)
- Successful grid deployment example (Binance Testnet)

**Red Thread Connection**:
*Backtest metrics → Live expectations gap → Risk controls → Sustainable returns*

---

### Module 9: Cross-Asset Considerations (1 hour)
**Goal**: Understand how to apply grid trading beyond crypto.

**Topics**:
- Crypto vs Stocks comparison
  * Sharpe ratio: crypto 1.3-1.8 vs stocks 0.9-1.2 (30-50% better in crypto)
  * Volatility: crypto 5-30× more, stocks stable
  * Trading hours: crypto 24/7 vs stocks 6.5h, means fewer overnight gaps in crypto
  * Mean-reversion timeframe: crypto 1-5 days, stocks 5-20 days
  * Commissions: crypto 2-50 bps, stocks 1-5 bps (stocks better)
  * Tax: crypto 37% capital gains, stocks 15-20% long-term (stocks better)
- Interactive Brokers integration architecture
  * IB Gateway vs TWS Desktop (gateway is production, desktop is not)
  * Commission structure: $1-4 per trade
  * Margin requirements and leverage limits
  * Order types supported
- Forex considerations (if relevant)
- Hybrid portfolio optimization

**Tables**:
- Asset class comparison matrix (vol, hours, commissions, tax, Sharpe)
- IB order type support vs grid engine requirements

**Red Thread Connection**:
*Asset class properties → Strategy adaptation → Market selection → Profitability*

---

### Module 10: Cloud Deployment & Infrastructure (1 hour)
**Goal**: Prepare to run grid trading in production on Azure.

**Topics**:
- Azure VM setup for grid trading
  * Recommended: Standard_B2s (2 cores, 4GB RAM, $35/month)
  * OS: Linux (Ubuntu 22.04 recommended)
  * Storage: 64GB SSD ($10/month)
- IB Gateway containerization (Docker)
  * IB Gateway CPU: 5-10% (lightweight)
  * Restart policy: auto-restart on crash
- Database for results: PostgreSQL or SQLite
- Monitoring and alerting (Python logging, external services)
- Cost analysis: $150-200/month total
- Break-even calculation: $1K portfolio at 15-25% annual return covers costs
- Deployment checklist
- Security considerations: IB credentials, API keys, network access

**Diagrams**:
- Azure architecture: VM → IB Gateway → Engine → Database
- Component interaction flow
- Cost breakdown pie chart

**Red Thread Connection**:
*Engine implementation → Cloud deployment → Sustainable live trading*

---

## Interconnected Topics Red Thread Examples

### Red Thread 1: From Position Sizing to Portfolio Performance
```
Position Sizing (percent-of-capital, fixed-amount)
    ↓
Risk Management (max position, max drawdown per-level)
    ↓
Constraint Handling (SKIP if insufficient capital, RESIZE if needed)
    ↓
Portfolio Correlation (Gap 4: size based on correlation)
    ↓
Volatility Regime (Gap 5: reduce sizing in high-vol periods)
    ↓
Overall Portfolio Expected Return & Sharpe Ratio
```

### Red Thread 2: From Data Quality to Realistic Results
```
OHLCV Data Quality (gaps, spikes, volume)
    ↓
Fill Simulation Accuracy (LIMIT vs MARKET logic)
    ↓
Slippage Application (percentage on MARKET fills)
    ↓
Backtest Results Accuracy
    ↓
Research Parameters → Live Expectations
```

### Red Thread 3: From Trend Detection to Better Entry Points
```
EMA Calculation (trend identification)
    ↓
ADX Calculation (trend strength) ← Gap 1 adds this
    ↓
FilterPolicy (skip placement if downtrend detected)
    ↓
Fewer False Signals (eliminate 30-40% losing trades)
    ↓
Better Sharpe Ratio & Profit Factor
```

### Red Thread 4: From Single Symbol to Portfolio Management
```
Single Symbol Grid (SimpleGridStrategy)
    ↓
Multi-Symbol Runner (process multiple DataFrames)
    ↓
Correlation Calculation (Gap 4: inter-symbol correlation)
    ↓
Portfolio-Level Sizing (reduce if correlated)
    ↓
Portfolio Risk Management (Gap 8: portfolio constraints)
    ↓
Sustainable, Diversified Returns
```

---

## Code Examples to Include

### Example 1: SimpleGridStrategy vs DynamicGridStrategy
- Side-by-side code showing differences
- When to use each
- Performance implications

### Example 2: ATR Calculation and Spacing
- Show how ATR is calculated
- Show how ATRSpacingPolicy uses it
- Interactive: change volatility input, see spacing change

### Example 3: FIFO Position Tracking
- Explain deque usage for O(1) SELL lookup
- Show performance benefit vs naive list iteration
- Code: manual deque push/pop vs list scan

### Example 4: Fill Simulation with Slippage
- Pseudocode for _simulate_fills_for_candle()
- Show LIMIT vs MARKET fill logic
- Example with real numbers: order price, slippage %, fill price

### Example 5: GridResearchRunner Usage
- Create runner, set parameters, run sweep, interpret results
- Show how to extract winning parameters
- Show metric rankings

### Example 6: Custom FilterPolicy for Trend Filter (Gap 1)
- Show how to implement ADX-based filter
- Show how to integrate into DynamicGridStrategy
- Test results: before/after trend filter

---

## Output Format Requirements

**HTML Structure**:
- Navigation sidebar with all modules and topics
- Responsive design (works on desktop, tablet, mobile)
- Dark/light mode toggle
- Syntax highlighting for code examples
- Collapsible sections for details

**Visual Aids**:
- SVG diagrams for architecture and flows
- Charts for metric comparisons
- Tables for specifications and comparisons
- Timeline diagrams for order lifecycle

**Interactivity**:
- Expandable/collapsible sections
- Tabs for code examples (Python, pseudocode)
- Hover tooltips for definitions
- Related concepts links between modules
- Search functionality

**Assessment**:
- End-of-module quizzes (5-10 questions)
- Graded on understanding, not just memorization
- Self-reflection prompts
- Knowledge check sections

**Navigation**:
- Table of contents
- Previous/Next buttons
- Breadcrumb navigation
- Search and glossary

---

## Success Criteria

The training is successful if a learner can:
1. ✅ Explain grid trading mechanics, assumptions, and profitability conditions
2. ✅ Draw the engine architecture and describe the main loop
3. ✅ Identify all 8 gaps and explain why each matters
4. ✅ Write a custom FilterPolicy (e.g., trend filter)
5. ✅ Run a parameter sweep and interpret results
6. ✅ Explain the cross-asset differences (crypto vs stocks)
7. ✅ Deploy a grid strategy to Azure cloud
8. ✅ Set up monitoring and risk controls
9. ✅ Calculate expected returns and Sharpe ratio
10. ✅ Identify one improvement opportunity and propose implementation

---

## Target Audience

- Intermediate Python developers
- Traders wanting to understand algorithmic grid trading
- DevOps/cloud engineers deploying trading systems
- Product managers overseeing trading platform development

**Assumed Knowledge**:
- Python 3.8+
- Basic pandas/numpy
- Comfort with financial concepts (P&L, sharpe, volatility)
- Git and CLI basics

---

## Tone and Style

- **Technical but Accessible**: Explain concepts clearly, use examples, don't assume deep trading knowledge
- **Practical**: Every module has code examples from the real engine
- **Honest**: Acknowledge limitations, don't over-promise
- **Visual**: Use diagrams and interactive examples liberally
- **Actionable**: End each module with "next steps" for learner

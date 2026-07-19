# Backtester Repository Context

> **Purpose of this file:** Persistent context for AI coding sessions. Read this before making any changes.
> Last updated: 2026-06-07.

---

## 1. Purpose of this Repository

This is a monorepo containing a modular algorithmic trading backtesting platform centered on **grid trading strategies**. The project is being split from a legacy monolith (`backtester_old`) into separate, cleanly bounded components:

1. A **pure Python library** for backtesting grid strategies (`grid-backtest-core`)
2. A **SaaS web application** that wraps the library with a multi-user API and frontend (`grid-backtest-saas`)
3. A **future Binance live/paper trading runtime** (not yet created)

The core design principle is a **strict separation** between backtesting logic, SaaS infrastructure, and exchange execution. The backtesting engine must never know about web frameworks, databases, or exchange SDKs.

---

## 2. Current Folder Structure

### `backtester_old/`
- **Current role:** Original monolith baseline. All functionality in one place. Active reference.
- **Intended target role:** Read-only reference and migration source. Should not be evolved further.
- **What belongs here:** Nothing new. It exists as a migration source only.
- **What should NOT belong here:** Any new feature development.

### `grid-backtest-core/`
- **Current role:** Clean, pip-installable Python library for grid backtesting. Under active development.
- **Intended target role:** The canonical backtesting engine. Zero I/O, zero exchange knowledge, zero web framework dependencies. Importable by any consumer.
- **What belongs here:**
  - Domain models (Candle, Order, Position, AccountState, Trade, etc.)
  - Backtest engine loop and simulation
  - Strategy interface and implementations (SimpleGrid, DynamicGrid)
  - Strategy policies (filter, range, recenter, SL/TP, space)
  - Indicator computation (ATR, EMA, RSI, ADX)
  - Execution layer (bootstrap, constraints, reservations)
  - Order lifecycle policies (expiry / TTL)
  - Explicit warmup handling
  - Result models, metrics, benchmarks
  - Research / parameter grid search
  - DataSource protocol (not implementations)
  - Config dataclasses (typed, no Pydantic, no YAML)
- **What should NOT belong here:**
  - YAML/JSON config loading (belongs in app layer or SaaS)
  - File I/O (results persistence, data loading) — expose protocols only
  - Exchange adapters or Binance SDK
  - Web framework code (FastAPI, etc.)
  - Database access
  - Live/paper trading runtime

### `grid-backtest-saas/`
- **Current role:** FastAPI backend + skeleton Next.js frontend for a multi-user SaaS backtesting tool.
- **Intended target role:** The SaaS/cloud-facing application layer that wraps `grid-backtest-core`.
- **What belongs here:**
  - FastAPI REST API and WebSocket endpoints
  - JWT authentication
  - Celery async workers for running backtests
  - PostgreSQL models and Alembic migrations
  - Pydantic request/response schemas
  - YAML/JSON config parsing and validation (app layer)
  - Results persistence (DB + file artifacts)
  - Next.js frontend (grid configurator, results dashboard)
  - Docker/cloud deployment config
- **What should NOT belong here:**
  - Core backtest logic (must come from `grid-backtest-core` as a dependency)
  - Binance execution runtime

### Future: `grid-backtest-binance/` (not yet created)
- **Intended role:** Standalone Binance live and paper trading runtime.
- **What will belong here:**
  - Binance exchange adapter (`SpotExchange` implementation)
  - Binance kline websocket stream
  - Binance user data stream
  - Live order manager, equity tracker, PnL ledger
  - Paper trading mode (Binance Testnet)
  - Risk controls and kill switch
  - CLI entrypoints for live/paper runs
  - Docker + Azure Container Instance deployment
- **What should NOT belong here:**
  - Backtesting engine logic (imports `grid-backtest-core` instead)
  - Frontend or SaaS infrastructure
- **When to create it:** When live/paper trading is the active priority. Do not create prematurely.

---

## 3. Original Baseline: `backtester_old`

### Module map

| Module | Path | Description |
|---|---|---|
| Domain models | `core/models.py` | Candle, Order, Position, AccountState, OrderFilledEvent, enums |
| Engine actions | `core/engine_actions.py` | EngineAction, PLACE_ORDER / GRID_EXIT / CANCEL_OPEN_ORDERS |
| Strategy base | `core/strategy/base.py` | IStrategy, BaseStrategy |
| Simple grid | `core/strategy/grid_strategy_simple.py` | GridConfig, SimpleGridStrategy |
| Dynamic grid | `core/strategy/grid_strategy_dynamic.py` | DynamicGridConfig, DynamicGridStrategy |
| Policies | `core/strategy/policies/` | filter, range, recenter, sltp, space |
| Execution | `core/execution/` | bootstrap, constraints, reservations |
| Live runtime | `core/live/` | order_manager, equity_tracker, pnl_ledger |
| Result models | `core/results/models.py` | BacktestResult, Trade, EquityPoint |
| Metrics | `core/results/metrics.py` | MetricRegistry, standard metric functions |
| Benchmarks | `core/results/benchmarks.py` | Buy & Hold benchmark |
| Trade builder | `core/results/trade_builder.py` | Fill → logical trade conversion |
| Repository | `core/results/repository.py` | `save_backtest_result()` → writes CSV/JSON artifacts |
| Summary | `core/results/summary.py` | `print_result_summary()`, `result_to_dataframes()` |
| Live repository | `core/results/live_repository.py` | Live run artifact persistence |
| Research | `core/research/grid_search.py` | Parameter grid search |
| Backtest engine | `backtest/engine.py` | Main simulation loop |
| Data source | `infra/data_source.py` | LocalFileDataSource (parquet/CSV loader) |
| Config | `infra/config_loader.py` | YAML/JSON → Pydantic RunConfig |
| Indicators | `infra/indicators.py` | ATR, EMA, RSI (pandas) |
| Logging | `infra/logging_setup.py` | Structured logging setup |
| Exchange base | `infra/exchange/base.py` | SpotExchange Protocol, AssetBalance, SymbolFilters |
| Binance adapter | `infra/exchange/binance_spot.py` | BinanceSpot SpotExchange implementation |
| Kline stream | `infra/marketdata/binance_kline_stream.py` | WebSocket candle streaming |
| User stream | `infra/marketdata/binance_user_stream.py` | Order/fill event streaming |
| Downloader | `infra/binance_downloader.py` | Historical data download from Binance |
| Secrets | `infra/secrets.py` | Env-var credential loading |
| App entrypoints | `app/` | main.py, backtest runner, research runner |

### Key features
- Full grid backtesting (simple and dynamic strategies)
- Configurable indicators: ATR, EMA, RSI
- Portfolio bootstrap modes: long_only, neutral_split, neutral_topup
- Order constraints and fund reservations
- Floating/recentering grid with band_break and time modes
- Strategy policies: RSI filter, trend filter, SL/TP, range management
- Parallel parameter grid search with ProcessPoolExecutor
- Train/forward split (ratio or date)
- Results: summary.json, trades.csv, equity_curve.csv, extra.json
- Buy & Hold benchmark comparison
- Full Binance integration: REST + WebSocket streams
- Live order manager with client_order_id tagging
- Equity tracking and PnL ledger
- YAML-based config with Pydantic v1 validation
- Structured logging with per-run log files

### Parts that should be migrated cleanly
- Strategy logic and policies (mostly migrated to core)
- Metrics registry and metric functions (migrated)
- Benchmarks (migrated)
- Trade builder (migrated)
- Execution layer: bootstrap, constraints, reservations (migrated)
- `results/repository.py` and `results/summary.py` → add to core as optional utilities
- `core/live/order_manager.py` → encode/decode client_order_id scheme useful for future Binance runtime

### Legacy/unclean parts — do not copy directly
- `infra/config_loader.py` uses Pydantic v1 (`.parse_obj()`); core uses pure dataclasses
- Pydantic v1 `<2.0` is pinned; incompatible with modern Python/Pydantic v2
- Hard-coded `HIST_DATA_ROOT` path in `infra/data_source.py`
- Mixed responsibilities in `backtest/engine.py` (file I/O + data loading + config loading inside engine)
- `infra/logging_setup.py` uses a custom logger factory that should be stdlib-only in core
- Live runtime components are mixed into `core/` instead of being in a separate deployment module

---

## 4. Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      grid-backtest-core                          │
│  Pure Python library. No I/O. No exchange. No web framework.    │
│                                                                  │
│  models · engine · strategies · indicators · execution           │
│  results models · metrics · benchmarks · research               │
│  DataSource protocol (consumer implements)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ pip dependency (both consumers import)
          ┌──────────────┴───────────────┐
          │                              │
┌─────────▼──────────┐        ┌──────────▼──────────┐
│  grid-backtest-saas │        │ grid-backtest-binance│
│                     │        │  (future)            │
│  FastAPI + Celery   │        │                      │
│  PostgreSQL         │        │  Binance adapters    │
│  JWT auth           │        │  WebSocket streams   │
│  Next.js frontend   │        │  Live order manager  │
│  Docker/cloud       │        │  Paper/live runtime  │
│                     │        │  Azure CI deploy     │
│  Implements:        │        │                      │
│  - DataSource       │        │  Implements:         │
│  - Results I/O      │        │  - DataSource        │
│  - Config loading   │        │  - SpotExchange      │
└─────────────────────┘        └─────────────────────┘
```

### Dependency rules
- `grid-backtest-core` has **no dependencies** on SaaS or Binance runtime.
- `grid-backtest-saas` depends on `grid-backtest-core` (pip install).
- `grid-backtest-binance` will depend on `grid-backtest-core` (pip install).
- SaaS and Binance runtime are **independent** of each other.
- Shared domain types (Candle, Order, etc.) live in `grid-backtest-core` only — never duplicated.

### Boundary responsibilities
| Concern | grid-backtest-core | grid-backtest-saas | grid-backtest-binance |
|---|---|---|---|
| Domain models | ✅ owns | imports | imports |
| Backtest engine | ✅ owns | calls | not used |
| Strategies | ✅ owns | configures | instantiates |
| Config dataclasses | ✅ owns | wraps | wraps |
| Config loading (YAML) | ❌ protocol only | ✅ owns | ✅ owns |
| Results persistence | ❌ protocol only | ✅ owns (DB+files) | ✅ owns (files) |
| Exchange adapter | ❌ protocol only | ❌ not needed | ✅ owns |
| Auth / users | ❌ | ✅ owns | ❌ |
| Live order tracking | ❌ | ❌ | ✅ owns |

---

## 5. `grid-backtest-core` Analysis

### Current structure
```
src/grid_backtest/
├── __init__.py          # Public API exports
├── engine.py            # BacktestEngine (main loop)
├── engine_fast.py       # Numba-accelerated engine variant
├── _numba_engine.py     # Low-level Numba kernel
├── config.py            # Frozen dataclass configs (BacktestConfig etc.)
├── models.py            # Candle, Order, Position, AccountState, OrderFilledEvent
├── engine_actions.py    # EngineAction, EngineActionType
├── indicators.py        # enrich_indicators (ATR, EMA, RSI, ADX via pandas)
├── strategy/
│   ├── base.py          # IStrategy, BaseStrategy
│   ├── grid_simple.py   # GridConfig, SimpleGridStrategy
│   ├── grid_dynamic.py  # DynamicGridConfig, DynamicGridStrategy
│   └── policies/        # filter, range, recenter, sltp, space
├── execution/
│   ├── bootstrap.py     # Portfolio bootstrap (long_only, neutral_split, neutral_topup)
│   ├── constraints.py   # Order feasibility checks
│   └── reservations.py  # Quote/base fund reservation book
├── results/
│   ├── models.py        # BacktestResult, Trade, EquityPoint
│   ├── metrics.py       # MetricRegistry + standard metrics (incl. Sharpe, Calmar, Sortino)
│   ├── benchmarks.py    # Buy & Hold benchmark
│   ├── trade_builder.py # Fill → logical trade conversion
│   └── repository.py    # save_backtest_result(), print_result_summary(), result_to_dataframes()
├── research/
│   ├── grid_search.py       # Parallel parameter search (ProcessPoolExecutor)
│   └── grid_search_fast.py  # Faster variant
└── data/
    ├── __init__.py
    └── protocols.py     # DataSource protocol only (no implementation)
```

### Implemented features
- BacktestEngine with full simulation loop; **slippage_pct applied** to MARKET fills
- **FIFO position scan fixed** — O(1) lookup via `_position_fifo` deque (was O(n))
- Numba-accelerated fast engine (`engine_fast.py`, `_numba_engine.py`); relationship documented in public API
- All domain models (aligned with backtester_old)
- EngineAction protocol (PLACE_ORDER, GRID_EXIT, CANCEL_OPEN_ORDERS)
- Indicators: ATR (multiple periods), EMA (multiple periods), RSI (multiple periods), ADX (multiple periods)
- Strategies: SimpleGridStrategy, DynamicGridStrategy
  - `GridConfig.grid_prices` — explicit price list overrides arithmetic/geometric calculation
  - `DynamicGridConfig.spacing_mode` — `"range"` (default, evenly spaced), `"percent"` (step = close × pct), `"atr"` (step = ATR × mult)
  - `DynamicGridConfig.use_atr_range` — `True` (ATR range, default), `False` (honours `range_mode` field)
  - `DynamicGridConfig.allow_reentry` — `False` (permanent stop, default), `True` (resets and rebuilds grid after SL/TP)
  - `DynamicGridConfig.use_adx_filter` — blocks new grid orders when ADX exceeds `max_adx`
  - `DynamicGridStrategy._log_config()` — logs all active strategy parameters on init, including filters
- All policies from old: filter, range, recenter, sltp, space; **SpacingPolicy now wired into DynamicGridStrategy**
- Execution layer: bootstrap modes, constraint checks, reservation book
- Order expiry / TTL via `OrderExpiryConfig` with strategy cancellation notifications
- Explicit warmup handling via `WarmupConfig` (`drop_indicator_na`, fixed `bars` skip)
- Result models: BacktestResult, Trade, EquityPoint
- Metrics: net_pnl, total_return_pct, max_drawdown, max_drawdown_pct, n_trades, win_rate_pct, avg_trade_pnl, profit_factor, **sharpe_ratio, calmar_ratio, sortino_ratio**
- Buy & Hold benchmark
- Trade builder (fill → logical trade)
- Research: parallel grid search with ProcessPoolExecutor; **GridResearchRunner exported from `__init__.py`**
- **Results persistence: `results/repository.py`** — `save_backtest_result()`, `print_result_summary()`, `result_to_dataframes()`
- DataSource protocol
- Same-candle fill behavior documented (orders placed in `on_candle` can fill in same candle's OHLC range)

### Missing features compared to `backtester_old`

| Feature | Old location | Status in core |
|---|---|---|
| Results persistence (save_backtest_result) | `core/results/repository.py` | ✅ Added: `results/repository.py` |
| Results summary printing | `core/results/summary.py` | ✅ Added: `print_result_summary()` in repository.py |
| result_to_dataframes() | `core/results/summary.py` | ✅ Added: `result_to_dataframes()` in repository.py |
| Sharpe / Calmar / Sortino metrics | not in old | ✅ Added to MetricRegistry |
| Slippage model applied in engine | config only | ✅ Fixed: MARKET fills now apply slippage_pct |
| SpacingPolicy wired in DynamicGridStrategy | existed as policy | ✅ Fixed: spacing_mode="percent"/"atr" now works |
| range_mode honoured when use_atr_range=False | ignored in old | ✅ Fixed: new use_atr_range flag |
| SL/TP re-entry | not in old | ✅ Added: allow_reentry flag |
| Strategy init logging | partial in old | ✅ Added: _log_config() with full filter/SL/TP detail |
| Local file data source (parquet/CSV) | `infra/data_source.py` | ❌ By design (protocol only) — no reference impl |
| YAML/JSON config loading | `infra/config_loader.py` | ❌ By design (app layer responsibility) |
| Timeframe resampling | `infra/data_source.py` | ❌ Missing from core (lives in old's data source) |
| Binance data downloader | `infra/binance_downloader.py` | ❌ By design (belongs in Binance runtime) |
| Config hash / immutable snapshot | REQ-0025 | ❌ Not implemented anywhere |
| Order expiry / TTL | backtester_old config | ✅ Added: `OrderExpiryConfig`, engine expiry, cancellation hook |
| Warmup period handling | documented in reqs | ✅ Added: `WarmupConfig.drop_indicator_na` and `WarmupConfig.bars` |
| Run artifact manifest | REQ-0185 | ❌ Not in core (app layer responsibility) |

### Technical debt
- `grid_search_fast.py` exists alongside `grid_search.py` — the fast variant uses Numba (grid-specific, ~200–400× faster); the standard variant uses ProcessPoolExecutor (any strategy). Relationship documented but both are in the public API. Consider unifying the interface.
- Config dataclasses have no YAML loader → consumers (SaaS, CLI) must build their own deserialization
- ~~`slippage_pct` field exists in `BacktestConfig` but may not be applied in the engine simulation~~ ✅ Fixed
- ~~No `Sharpe`, `Calmar`, or `Sortino` ratios in MetricRegistry~~ ✅ Fixed
- ~~`engine_fast.py` and `_numba_engine.py` relationship not documented~~ ✅ Documented in public API

### Known Python 3.12 pitfall
If `grid_dynamic.py` is ever refactored, be aware: having **two `@dataclass` class definitions with the same name** in the same module will silently cause the second to overwrite the first's `__annotations__`. This caused a multi-hour debugging session. The class `DynamicGridConfig` must appear exactly **once** in `grid_dynamic.py`.

### Test coverage
- `tests/test_engine.py` — BacktestEngine integration tests (slippage, fills, bootstrap)
- `tests/test_indicators.py` — Indicator computation tests
- `tests/test_metrics.py` — Metric function tests (incl. Sharpe, Calmar, Sortino)
- `tests/test_strategies.py` — Strategy unit tests (SimpleGrid, DynamicGrid spacing, re-entry, range mode)
- `tests/test_execution.py` — **Added:** bootstrap modes, constraints, reservations
- `tests/test_research.py` — **Added:** GridResearchRunner, parameter expansion, result ranking
- `tests/test_trade_builder.py` — **Added:** TradeBuilder FIFO lot matching, partial closes, fees
- **Total: 92 tests passing as of 2026-06-07**

### Configuration handling
- Clean: pure frozen dataclasses, no Pydantic, no YAML in core
- `BacktestConfig` → `ConstraintConfig`, `ReservationConfig`, `BootstrapConfig`, `IndicatorSpec`
- Consumers must build their own config loading layer (correct separation)

### Domain model quality
- High quality: dataclasses, typed fields, enums, minimal dependencies
- `Candle` uses `slots=True` (core) — small performance improvement vs old
- `AccountState` is clean and aligned between old and core
- `OrderFilledEvent` is `frozen=True` — correct for immutable events

### Recommended next steps for `grid-backtest-core`
1. **Config hash** — REQ-0025 reproducibility; hash of `BacktestConfig` fields for run deduplication
2. **Audit `__init__.py`** — ensure all public symbols are exported and stable
3. **Add `LocalParquetDataSource`** — a reference `DataSource` implementation for local parquet/CSV files; useful for CLI consumers without SaaS

---

## 6. `grid-backtest-saas` Analysis

### Current structure
```
grid-backtest-saas/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, health endpoint
│   │   ├── api/v1/
│   │   │   ├── auth.py          # Register / login (JWT)
│   │   │   ├── backtest.py      # Submit / get / list backtest runs
│   │   │   ├── research.py      # Parameter search (stub)
│   │   │   └── deps.py          # FastAPI dependencies (DB session, current user)
│   │   ├── core/
│   │   │   ├── config.py        # App config (env vars, DB URL, Redis URL)
│   │   │   └── security.py      # JWT encode/decode, password hashing
│   │   ├── db/
│   │   │   ├── models.py        # SQLAlchemy ORM models (User, BacktestRun)
│   │   │   └── session.py       # DB session factory
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── backtest_service.py  # Calls grid-backtest-core
│   │   │   └── research_service.py  # Research runner (stub or early)
│   │   └── workers/
│   │       ├── celery_app.py    # Celery configuration (Redis broker)
│   │       └── backtest_task.py # Async backtest Celery task
│   ├── alembic/                 # DB migrations
│   └── tests/
├── frontend/
│   └── static/                  # Next.js app (skeleton only)
├── data/                        # Mounted data directory
├── infra/docker/
├── docker-compose.yml           # PostgreSQL + Redis
├── pyproject.toml
└── .env.example
```

### Frontend/backend responsibilities
- **Backend:** FastAPI handles all business logic. Celery handles async backtest jobs. PostgreSQL stores users and run results. Redis is both the Celery broker and cache.
- **Frontend:** Next.js (skeleton only, Phase 2). Will provide grid configurator UI and results dashboard.

### How it consumes the core
- `grid-backtest-core` is installed as a pip dependency (`pip install -e "../grid-backtest-core"`)
- `backtest_service.py` builds `BacktestConfig` and strategy from API request, runs `BacktestEngine`, returns `BacktestResult`
- SaaS owns YAML config deserialization, user data persistence, and result storage in PostgreSQL

### What should NOT be duplicated from core
- Strategy classes — SaaS should never reimplement grid logic
- Metrics — SaaS should call `create_default_metric_registry()` from core
- Domain models — no separate Trade/Order models in SaaS DB beyond what's needed for persistence

### Deployment / cloud considerations
- Docker Compose for local dev (PostgreSQL + Redis)
- Backend + frontend run separately (`uvicorn` + Next.js dev server)
- Azure deployment planned (Container Instances + Azure Files for artifacts)
- `.env.example` shows required environment variables pattern
- Alembic handles schema migrations

### Current gaps
- Frontend is a skeleton only (Next.js not yet implemented)
- WebSocket progress updates not yet implemented
- Rate limiting not yet implemented

---

## 7. Missing Functionality Migration Map

| Functionality | `backtester_old` | `grid-backtest-core` | `grid-backtest-saas` | Target | Priority | Notes |
|---|:---:|:---:|:---:|---|---|---|
| Domain models (Candle, Order, etc.) | ✅ | ✅ | via core | core | ✅ Done | Aligned |
| BacktestEngine simulation loop | ✅ | ✅ | via core | core | ✅ Done | Clean |
| Slippage applied in engine | config only | ✅ | via core | core | ✅ Done | MARKET fills |
| FIFO position scan (O(1)) | O(n) | ✅ | via core | core | ✅ Done | `_position_fifo` deque |
| SimpleGridStrategy | ✅ | ✅ | via core | core | ✅ Done | + `grid_prices` field |
| DynamicGridStrategy | ✅ | ✅ | via core | core | ✅ Done | + spacing/range/reentry |
| DynamicGrid spacing_mode (percent/atr) | dead fields | ✅ | ✅ schema | core | ✅ Done | SpacingPolicy wired |
| DynamicGrid use_atr_range flag | not in old | ✅ | ✅ schema | core | ✅ Done | controls range source |
| DynamicGrid allow_reentry flag | not in old | ✅ | ✅ schema | core | ✅ Done | re-entry after SL/TP |
| DynamicGrid filter logging | partial | ✅ | via core | core | ✅ Done | `_log_config()` |
| Strategy policies (filter/range/recenter/sltp/space) | ✅ | ✅ | via core | core | ✅ Done | |
| Indicators (ATR/EMA/RSI/ADX) | ✅ | ✅ | via core | core | ✅ Done | ADX added for regime filtering |
| Metrics (net_pnl, drawdown, etc.) | ✅ | ✅ | via core | core | ✅ Done | |
| Sharpe / Calmar / Sortino metrics | ❌ | ✅ | ✅ response | core | ✅ Done | Annualised |
| Buy & Hold benchmark | ✅ | ✅ | via core | core | ✅ Done | |
| Trade builder | ✅ | ✅ | via core | core | ✅ Done | |
| Execution: bootstrap, constraints, reservations | ✅ | ✅ | via core | core | ✅ Done | |
| Order expiry / TTL | ❌ | ✅ | via core | core | ✅ Done | `OrderExpiryConfig.max_age_bars` + cancellation hook |
| Explicit warmup period handling | implicit | ✅ | via core | core | ✅ Done | `WarmupConfig.drop_indicator_na` + fixed bar skip |
| Research / parallel grid search | ✅ | ✅ | ✅ connected | core | ✅ Done | Fast variant added |
| GridResearchRunner exported | ✅ | ✅ | via core | core | ✅ Done | In `__init__.py` |
| Results persistence (save_backtest_result) | ✅ | ✅ | via core | core | ✅ Done | `results/repository.py` |
| Results summary (print_result_summary) | ✅ | ✅ | via core | core | ✅ Done | In repository.py |
| result_to_dataframes() | ✅ | ✅ | via core | core | ✅ Done | In repository.py |
| Tests: execution layer | ✅ implicit | ✅ | n/a | core | ✅ Done | bootstrap/constraints/reservations |
| Tests: trade_builder | ✅ implicit | ✅ | n/a | core | ✅ Done | FIFO lot matching |
| Tests: research runner | ❌ | ✅ | n/a | core | ✅ Done | |
| SaaS GridConfigSchema new fields | ❌ | ✅ core | ✅ | saas | ✅ Done | spacing/SL/TP/reentry |
| SaaS research endpoint connected | ❌ | ✅ core | ✅ | saas | ✅ Done | full param search |
| **Config hash / snapshot** | ❌ | ❌ | ❌ | core+saas | 🟡 Medium | REQ-0025 |
| Local file data source (parquet/CSV) | ✅ | ❌ (protocol) | | saas/binance | 🟡 Medium | Core has protocol only |
| Timeframe resampling | ✅ infra | ❌ | ❌ | saas (wrap) | 🟡 Medium | Belongs in data layer |
| YAML config loading | ✅ Pydantic v1 | ❌ by design | partial | saas/binance | 🟡 Medium | Pydantic v2 in SaaS |
| SaaS REST API (backtest submit/get/list) | ❌ | ❌ | ✅ | saas | ✅ Done | |
| SaaS user auth (JWT) | ❌ | ❌ | ✅ | saas | ✅ Done | |
| SaaS async workers (Celery) | ❌ | ❌ | ✅ | saas | ✅ Done | |
| SaaS DB persistence (PostgreSQL) | ❌ | ❌ | ✅ | saas | ✅ Done | |
| **SaaS frontend (Next.js)** | ❌ | ❌ | skeleton | saas | 🟡 Medium | Phase 2 |
| **SaaS WebSocket progress** | ❌ | ❌ | ❌ | saas | 🟡 Medium | Phase 2 |
| Binance exchange adapter | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Binance kline/user stream | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Live order manager (client_order_id) | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Equity tracker / PnL ledger | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Binance data downloader | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Paper trading mode (Testnet) | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Risk controls / kill switch | ✅ | ❌ by design | ❌ | binance-future | ⬜ Later | |
| Azure Container Instance deploy | ✅ | ❌ | partial | binance-future | ⬜ Later | |
| CI/CD pipeline | ❌ | ❌ | ❌ | all | 🟡 Medium | Phase 4 |
| Structured logging (per run) | ✅ | stdlib only | | all | 🟡 Medium | |
| HTML/PDF report generation | config mention | ❌ | ❌ | core+saas | ⬜ Later | REQ-0154/0155 |

---

## 8. Requirements and Product Goals

The file `backtester_old/reqs/requirements.txt` is a comprehensive, system-wide requirements catalog (REQ-0001 through REQ-0225).

### Product goal
Build a modular algorithmic trading platform that supports three run modes:
1. **Backtest** — historical simulation
2. **Paper trading** — Binance Testnet, real API calls, no real money
3. **Live trading** — Binance Spot mainnet

### Technical goals
- Strict separation between backtest engine, SaaS layer, and live trading runtime
- Clean, testable, pip-installable core library
- Multi-user SaaS with web frontend for configuring and reviewing backtests
- Reproducible backtests (deterministic fills, config snapshots, config hashing)
- Exchange-agnostic strategy interface (no Binance types in strategies)
- Structured logging, event logs, artifact persistence for all run modes
- Docker-deployable, Azure-compatible

### Known constraints
- Python ≥ 3.11 required (core uses `slots=True`, `str | None` union syntax)
- `grid-backtest-core` must keep dependencies minimal: only `numpy`, `pandas`, `numba`
- `backtester_old` uses Pydantic v1 (`<2.0`) — do NOT carry this forward; SaaS should use Pydantic v2
- Binance live/paper trading must NOT reuse the backtest engine as execution engine
- Strategy output is always a list of `EngineAction` objects — never exchange-specific types

### Open questions (see Section 11)

### Key assumptions (confirmed by code inspection)
- "Spot-like" only: LONG positions, no short/futures
- Single symbol per run
- Candle-based strategy evaluation (on closed candles only)
- LIMIT order fill simulation: fill if candle low ≤ buy price or candle high ≥ sell price
- FIFO position closing on SELL fills
- Fees charged as percentage of notional on each fill

---

## 9. AI Coding Guidelines for This Repository

These rules apply to all AI coding sessions in this repository:

### Architecture rules
1. **Never add I/O to `grid-backtest-core`** — no file reads, no network calls, no database access. The engine receives a DataFrame, returns a result.
2. **Never add exchange/Binance imports to core** — not even as optional dependencies.
3. **Never add web framework imports (FastAPI, Flask, etc.) to core.**
4. **Never duplicate domain models** — `Candle`, `Order`, `Trade`, etc. are defined in core once. SaaS and future runtimes import from core.
5. **Keep the live trading runtime separate** — do not mix backtest simulation paths with live execution paths, even if they share domain models.

### Development rules
6. **Always read existing code before changing** — use grep/view to understand the current state.
7. **Prefer small, tested changes** — one concern per change.
8. **Add or update tests when changing core logic** — tests live in `grid-backtest-core/tests/`.
9. **Keep config explicit and typed** — prefer frozen dataclasses in core; Pydantic v2 in SaaS.
10. **Preserve useful behavior from `backtester_old`** when migrating — do not accidentally drop features.
11. **Document architectural decisions** in comments or this file.

### Code quality rules
12. **No `print()` in core library code** — use `logging.getLogger(__name__)`.
13. **No hardcoded paths** — core accepts DataFrames, not file paths.
14. **No mutable default arguments** in dataclasses — use `field(default_factory=...)`.
15. **Enum values are `str` subclasses** — allows JSON serialization without `.value`.

### Migration rules
16. **When porting from `backtester_old`**, check if the code has been simplified or improved in core first.
17. **Do not port Pydantic v1 code directly** — adapt to dataclasses (core) or Pydantic v2 (SaaS).
18. **Do not create the `grid-backtest-binance` folder** unless the user explicitly requests live trading work.

---

## 10. Recommended Roadmap

### Phase 1 — Stabilize `grid-backtest-core` *(largely complete)*

1. ~~**Add `results/repository.py`**~~ ✅ Done
2. ~~**Add missing metrics**~~ ✅ Done — Sharpe, Calmar, Sortino added
3. ~~**Fix slippage**~~ ✅ Done — MARKET fills now apply slippage_pct
4. ~~**Clarify fast engine**~~ ✅ Done — documented in public API
5. ~~**Add missing tests**~~ ✅ Done — execution, trade_builder, research tests added
6. ~~**Fix DynamicGridStrategy dead fields**~~ ✅ Done — spacing_mode, use_atr_range, allow_reentry all wired
7. ~~**Connect SaaS to DynamicGrid new fields**~~ ✅ Done — GridConfigSchema and research updated
8. ~~**Add order expiry / TTL support**~~ ✅ Done — `OrderExpiryConfig.max_age_bars`, engine expiry, strategy cancellation notification
9. **Audit `__init__.py`** — add `__all__`, ensure all public symbols are exported and stable
10. **Add `LocalParquetDataSource`** — reference DataSource implementation for local parquet/CSV (CLI use)

### Phase 2 — Connect SaaS to core

1. **Add local file DataSource** — implement `DataSource` protocol in SaaS for parquet/CSV loading with timeframe resampling (ported from `backtester_old/infra/data_source.py`)
2. **Add results persistence** — store `BacktestResult` artifacts (summary.json, trades.csv, equity_curve.csv) alongside PostgreSQL records
3. **Implement WebSocket progress** — stream backtest progress from Celery worker to frontend via WebSocket
4. **Build Next.js frontend** — grid configurator, results dashboard, equity chart
5. **Add rate limiting** — per-user request/run limits

### Phase 3 — Prepare Binance runtime *(create `grid-backtest-binance/`)*

1. **Create project** — `pyproject.toml`, `src/grid_binance/`, `tests/`, `Dockerfile`
2. **Port exchange adapter** — `infra/exchange/binance_spot.py` → `grid_binance/exchange/`
3. **Port market data streams** — kline stream, user stream
4. **Port live runtime** — `order_manager.py`, `equity_tracker.py`, `pnl_ledger.py`
5. **Implement `DataSource` protocol** — use Binance REST for historical backfill
6. **Add risk controls** — max open orders, max exposure, max daily loss, kill switch
7. **Add paper/live CLI entrypoints**
8. **Azure Container Instance deployment** — Dockerfile + deploy scripts

### Phase 4 — Production hardening

1. **CI/CD pipeline** — GitHub Actions: run tests on push; build Docker on release
2. **Dependency pinning** — pin all deps for reproducibility
3. **Package versioning** — semantic versioning for `grid-backtest-core`
4. **Structured logging** — consistent log format across all components
5. **Error handling** — network retries, graceful degradation, actionable error messages
6. **Documentation** — per-component README, API docs, deployment guide
7. **Artifact manifest** — REQ-0185, list all produced files per run

---

## 11. Open Questions

1. **~~Is `engine_fast.py` production-ready?~~** ✅ Resolved — documented: `engine_fast.py` (Numba, ~200–400× faster, grid-specific) is the preferred path for research runs; `engine.py` (pure Python) is the reference implementation for all strategy types. Both are in the public API.
2. **Should core include a file-based DataSource implementation?** Currently core has only the protocol. A reference `LocalParquetDataSource` in core would make the library self-contained for local CLI use. Or should this always be in the app layer?
3. **Who owns YAML config loading?** The SaaS and future Binance runtime both need it. Should there be a shared `grid-backtest-config` helper package, or should each app layer implement its own?
4. **~~What is the intended slippage model?~~** ✅ Resolved — `slippage_pct` applies to MARKET fills only (+pct for BUY, −pct for SELL). LIMIT fills are at specified price (slippage implicit in price distance). Documented in `engine.py`.
5. **Will SaaS support multi-symbol backtests?** Current engine is single-symbol. Multi-symbol portfolio backtesting is not in scope currently but should be considered in API design.
6. **Config hash reproducibility:** REQ-0025 requires a config hash for reproducibility. No implementation exists in any component. Where should this live?
7. **Research train/forward split:** `backtester_old/config/grid_run.yml` shows a `split` block (ratio or date). Is this implemented in `grid_backtest.research.grid_search`? Needs verification.
8. **What Pydantic version does SaaS use?** `pyproject.toml` was not fully inspected — confirm it uses Pydantic v2 and not v1.
9. **~~Is `grid_search_fast.py` the preferred research runner?~~** ✅ Resolved — `grid_search_fast.py` uses Numba (grid-specific, single-thread, ~200–400× faster); `grid_search.py` uses ProcessPoolExecutor (any strategy type). Prefer fast for grid-only research, standard for mixed strategies.
10. **~~Order expiry policy~~** ✅ Resolved — `OrderExpiryConfig.max_age_bars` cancels stale open orders after a configurable number of full candles.

---

## 12. Summary for Future AI Sessions

**Read this first before making any changes.**

This is a Python algorithmic trading project split into three folders:

| Folder | Status | Role |
|---|---|---|
| `backtester_old/` | Read-only reference | Legacy monolith — migration source |
| `grid-backtest-core/` | Active development ⭐ | Pure Python backtesting library (no I/O, no exchange) |
| `grid-backtest-saas/` | Secondary priority | FastAPI + Next.js SaaS wrapper around core |

**The current priority is `grid-backtest-core`.**

Key architecture rule: **Core has zero I/O and zero exchange knowledge.** It accepts a pandas DataFrame, returns a `BacktestResult`. Everything else (file loading, YAML config, web framework, DB, exchange API) belongs in the app layers.

**Current state as of 2026-06-07 (92 tests passing):**
- ✅ `results/repository.py` — `save_backtest_result`, `print_result_summary`, `result_to_dataframes`
- ✅ Sharpe, Calmar, Sortino metrics in MetricRegistry
- ✅ Slippage applied to MARKET fills in engine
- ✅ `DynamicGridStrategy` — `spacing_mode` ("range"/"percent"/"atr"), `use_atr_range`, `allow_reentry` all wired and tested
- ✅ ADX regime filter — `IndicatorSpec.compute_adx`, `add_adx()`, and `DynamicGridConfig.use_adx_filter`
- ✅ Order expiry / TTL — `OrderExpiryConfig.max_age_bars`, `OrderCancelledEvent`, and strategy cancellation cleanup
- ✅ Explicit warmup handling — `WarmupConfig.drop_indicator_na` and `WarmupConfig.bars`
- ✅ `GridConfig.grid_prices` — pre-computed custom price levels bypass arithmetic calculation
- ✅ SaaS `GridConfigSchema` + research schemas updated with all new DynamicGrid fields
- ✅ Research endpoint connected to core's `GridResearchRunner`
- ✅ Tests for execution layer, trade_builder, research runner, strategies
- ✅ FIFO position scan O(1) fix
- ✅ `engine_fast.py` / `grid_search_fast.py` documented in public API

**Known pitfall:** `grid_dynamic.py` must have exactly **one** `DynamicGridConfig` class definition. A duplicate at the end caused a multi-session debugging issue where Python silently dropped new fields from `__annotations__`.

**Immediately actionable next work:**
1. Add config hash — reproducible `BacktestConfig` fingerprint for run deduplication
2. Audit `__init__.py` — verify all public exports are stable after recent additions
3. Add `LocalParquetDataSource` — reference DataSource impl for local parquet/CSV files (Phase 1 tail)
4. Phase 2: SaaS results artifact persistence (store trades.csv/equity_curve.csv alongside DB records)
5. Phase 2: SaaS WebSocket progress streaming from Celery worker

**Do NOT:**
- Add file I/O to core
- Add Binance/exchange imports to core
- Use Pydantic v1 anywhere
- Create `grid-backtest-binance/` unless live trading is the explicit goal
- Mix backtest engine paths with live execution paths
- Add a second class definition for any `@dataclass` in `grid_dynamic.py`

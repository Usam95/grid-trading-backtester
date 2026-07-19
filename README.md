# Backtester

This is the canonical implementation repository for the grid-trading system.
The venue-independent engine and research foundation live in `gridlab`; the
product and FastAPI boundary live in `gridlab-studio`.

Run the complete reproducible Ticket 01 baseline from the repository root:

```shell
python tools/verify_baseline.py
```

The command bootstraps the pinned `uv` version when necessary, synchronizes the
exact committed lock without editable installs, checks version and architecture
contracts, and runs the canonical engine and Studio suites.

`backtester_old`, `grid-backtest-core`, and `grid-backtest-saas` are read-only
characterization sources. They are not workspace members, runtime dependencies,
or alternative authorities.


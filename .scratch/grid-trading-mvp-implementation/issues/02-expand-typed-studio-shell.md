# 02 — Expand a typed Studio shell around the existing backtest

**What to build:** Introduce the typed React, TypeScript, and Vite Studio shell beside the existing frontend and carry one existing backtest workflow end to end through the current FastAPI boundary. The old frontend remains usable until later workflow slices prove parity and the contract ticket removes it.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract.

**Status:** resolved

- [x] The typed shell starts locally and communicates with the existing backend through typed request and response contracts.
- [x] An operator can configure and execute one existing backtest and see its primary result without using the legacy page.
- [x] Permanent navigation and the Research/Operations trust boundary are present without implying online trading authority.
- [x] Browser state is not the authoritative store for the executed result or configuration.
- [x] Frontend dependency versions are locked and included in the local verification command.
- [x] Contract and browser-level tests prove the migrated path while the legacy frontend continues to work.

## Answer

Completed at `d41a15dc00ae85298d93f62908d4c026971a3312`. The typed
React/TypeScript/Vite Studio shell carries the characterized backtest through
the typed FastAPI contract, preserves the legacy frontend, separates Research
and Operations navigation, persists executed runs outside browser state, locks
frontend dependencies, and includes contract and real-browser coverage in the
reproducible baseline workflow.

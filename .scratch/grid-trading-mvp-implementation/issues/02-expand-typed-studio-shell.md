# 02 — Expand a typed Studio shell around the existing backtest

**What to build:** Introduce the typed React, TypeScript, and Vite Studio shell beside the existing frontend and carry one existing backtest workflow end to end through the current FastAPI boundary. The old frontend remains usable until later workflow slices prove parity and the contract ticket removes it.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract.

**Status:** ready-for-agent

- [ ] The typed shell starts locally and communicates with the existing backend through typed request and response contracts.
- [ ] An operator can configure and execute one existing backtest and see its primary result without using the legacy page.
- [ ] Permanent navigation and the Research/Operations trust boundary are present without implying online trading authority.
- [ ] Browser state is not the authoritative store for the executed result or configuration.
- [ ] Frontend dependency versions are locked and included in the local verification command.
- [ ] Contract and browser-level tests prove the migrated path while the legacy frontend continues to work.


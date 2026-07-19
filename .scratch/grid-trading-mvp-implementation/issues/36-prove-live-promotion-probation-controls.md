# 36 — Prove the live profile, promotion and probation controls

**What to build:** Implement and verify—without activating real funds—the mutually exclusive live deployment/credential profile, sealed promotion review, two-step single-use activation authorization, fresh live preflights, first-live probation evidence, and tiered abort/re-entry behavior. Actual production credential introduction and real-money activation remain separate human-authorized operations.

**Blocked by:** 26 — Qualify the Binance Testnet adapter and generation; 29 — Create and restore verified recoverable points; 31 — Build a qualified release with forward migrations; 33 — Connect Azure evidence, secrets and monitoring; 35 — Govern shakedown and formal Paper/Testnet qualification.

**Status:** ready-for-agent

- [ ] The live profile uses a new runtime/store/configuration/credential scope, disables Testnet authority, revokes Testnet permission, and proves live/Testnet secrets are never simultaneously readable.
- [ ] A current Binance contract/release review and live preflight prove endpoints, API behavior, symbol status, filters, fees, permissions, IP, balances, reservations, foreign orders, allocation, reconciliation, freshness, alerts, recovery, and strict in-bounds activation.
- [ ] The promotion bundle binds exact build, dependencies, schemas, candidate, evidence, account/allocation, risk profile, deployment, credential fingerprint, `250 USDT` ceiling, incidents, and zero unresolved gates.
- [ ] Promotion approval and re-authenticated activation confirmation are separate durable actions; authorization is exact-context, single-use, one-attempt, and expires after 15 domain minutes.
- [ ] Passing gates, deployment, time, API calls, or UI navigation cannot synthesize either human action or bypass a failed preflight.
- [ ] Probation tracks the unchanged 30–90-day identity, daily-first-week/weekly reviews, real cycle/fill-day activity, exact live fees/accounting/reconciliation, incidents, unavailable/frozen time, and no compounding.
- [ ] State uncertainty freezes before disposal; confirmed terminal danger latches bounded disposal; evidence-only insufficiency blocks success without inventing danger or unnecessary liquidation.
- [ ] Abort/re-entry requires authoritative closure, incident/root cause evidence, affected requalification, new bundle/activation, and a new probation clock.
- [ ] Operator-unavailability, changed source IP, VM outage, stop-loss liveness limitation, extreme gap/unmanaged-fill exposure, deferred maintenance, and credential blast radius are explicit reviewed residual risks rather than promised loss guarantees.

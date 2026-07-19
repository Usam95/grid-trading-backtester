# 21 — Admit authenticated idempotent operator commands

**What to build:** Add the loopback-only control gateway and typed operator-command path suitable for an SSH tunnel. The gateway authenticates, validates, scopes, expires, and forwards commands, while the targeted runtime remains the sole durable admission and authorization authority.

**Blocked by:** 20 — Run one mode-isolated runtime against a fake venue.

**Status:** ready-for-agent

- [ ] The gateway exposes no arbitrary shell, database mutation, venue credential, or direct venue command path.
- [ ] Sessions and commands enforce origin/CSRF protection, environment/run/allocation scope, fresh authority context, idempotency, expiry, nonce/replay protection, and concurrency.
- [ ] Pause and Emergency Stop activate the safety interlock without waiting behind ordinary work; Start, Resume, Operator Stop, and later activation use exact consequence previews and confirmation.
- [ ] The runtime records command admission, refusal, authorization, sequencing, consequences, outcome, and operator identity durably.
- [ ] Stale or disconnected browsers cannot queue a capital-affecting command for later execution.
- [ ] Duplicate, expired, wrong-environment, concurrent, unauthorized, and ambiguous requests have contract and end-to-end tests.
- [ ] Read-only projections remain available without implying command authority.


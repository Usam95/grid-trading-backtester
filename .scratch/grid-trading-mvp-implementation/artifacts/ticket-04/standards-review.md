# Ticket 04 Standards Review

## Review passes

Independent Standards reviews inspected the full diff, root and referenced
agent instructions, domain boundaries, architecture checks, exact values,
immutability, deterministic identities, fail-closed safety, typed contracts,
and Ticket 05+ exclusions.

| Severity | Finding | Affected files | Disposition |
| --- | --- | --- | --- |
| High | Mutable event payloads and plan collections could bypass deep immutability. | `canonical/events.py`, `canonical/plan.py` | Fixed with recursive payload freezing/key validation and tuple normalization. |
| High | Fail-closed decisions could be paired with unsafe plan roles. | `canonical/adaptation.py`, `canonical/plan.py` | Fixed with state/intent/buy/shift invariants, reference-relative roles, TREND_DOWN no-buy, and UNCERTAIN all-inactive checks. |
| Medium | Exact-value direct construction could contradict source text; version fields admitted unsupported schemas. | `canonical/values.py`, configuration/adaptation/plan modules | Fixed with constructor consistency and exact supported schema checks. |
| Medium | Epoch identity lacked explicit derivation causality. | `canonical/plan.py`, API/Studio contracts | Fixed by adding identity-only `derivation_causation_id`; no transition behavior was added. |
| Medium | Hysteresis could equal or exceed the trend threshold and collapse the effective threshold to zero. | `canonical/configuration.py` | Fixed by requiring hysteresis below the trend threshold, with regression coverage. |
| Medium | New plan code failed the repository formatting gate. | `canonical/plan.py` | Formatted with the pinned Ruff tool and rechecked. |

## Final result

The repeated independent Standards review reported no actionable findings.
Focused Ruff, mypy, architecture, canonical/API tests, and static quality gates
passed after the fixes. No persistence, activation, transition, execution,
Paper, Testnet, or other Ticket 05+ behavior was introduced.

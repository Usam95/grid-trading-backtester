# 07 — Deployment and security findings

Azure profile, SSH-only access, secret handling, and the deferred-maintenance exception.

---

## SEC-1 — `SECURITY_MAINTENANCE_DEFERRED` on an internet-exposed real-money host is the largest accepted risk · S1 · finding · `ready-for-human`

Issue 11 lands on **no scheduled update discovery, download, install, service restart, reboot, or
Livepatch** — the VM stays on its exact initial image indefinitely, and **real-money live is
explicitly allowed** in this state as `ACCEPTED_WITH_SECURITY_EXCEPTION`. The operator consciously
accepted this over several iterations.

Two things worth re-flagging before real money, because the record shows the decision was reached by
progressively *removing* maintenance rather than by a positive security argument:

1. The host is exposed on **SSH (22)** to a declared IP and makes **outbound** connections to
   Binance; an unpatched kernel/OpenSSH/TLS vulnerability discovered during a multi-month live run
   has **no remediation path** short of a full rebuild — which itself requires the operator + laptop
   + toolchain (a recovery dependency the drills must prove, issue 11).
2. The exception's *evidence* is now minimal: after the final iteration (issue 11, 2026-07-18) the
   VM does **not even inventory or measure** pending fixes, so the operator cannot see *how* exposed
   they are — only that they are.

**Ask:** for the live milestone specifically, reconsider a **minimal, controlled** patch path
(download-only + operator-scheduled frozen reboot, which the machinery already supports) or an
explicit, time-boxed acceptance with a rebuild-on-CVE trigger. At minimum, restore lightweight
**vulnerability inventory** so the exception is *measured*, not blind.

---

## SEC-2 — Source-IP-restricted SSH as the sole human gate is fragile against dynamic IPs · S2 · finding · `ready-for-human`

The only human access + control path is **SSH key from a declared operator public IP** (issues 11,
12); Studio reaches the gateway only through that tunnel; the Binance key allowlists the VM's static
IP. Residential/mobile ISPs rotate the operator's public IP, and the NSG admits **only** the declared
IP.

**Consequences:**
- Frequent IP changes force NSG edits (a "frozen, operator-approved change with verification" per
  issue 11) — friction that tempts widening the allowlist.
- If the operator's IP changes **while remote and a live incident is occurring**, they cannot SSH in
  to intervene until they update the NSG via the Azure portal (which needs Azure MFA, issue 12) —
  latency during exactly the wrong moment. Ties into DBT-4 / SAF-1.

**Fix:** decide a robust operator-ingress story (e.g., a small allowlist of stable egress IPs, or a
just-in-time NSG-open workflow like the one already used for Key Vault access) and test the
"operator IP changed during an incident" runbook.

---

## SEC-3 — Single VM/root trust boundary means memory-resident secrets share the blast radius · S2 · finding · `ready-for-human`

Secrets are Key-Vault-only, resolved **once** at frozen startup and **pinned in process memory**
(spec §10; issue 11/12). Testnet/live are mutually exclusive. Good. But gateway, paper, and the
credentialed runtime share **one VM and one root** (issue 11 explicitly accepts "the VM/root and
IMDS-admitted jobs remain one cloud-identity trust boundary"). A root compromise (see SEC-1: no
patching) can read the live key from the credentialed process's memory and use the (IP-allowlisted,
withdrawals-disabled) trade permission to churn/wash the balance to Binance counterparties.

The withdrawals-disabled key bounds *theft* well, but not *malicious trading* of the 250 USDT. At
MVP scale this is bounded; at scale it is not. Note as an explicit residual tied to SEC-1.

---

## SEC-4 — Work-laptop for dev/paper/testnet: employer erase/backup authority is an evidence risk · S3 · finding · `ready-for-human`

Issue 12: development, paper, and Testnet may run from the **work laptop** (employer permits it),
but employer **administrative/monitoring/backup/erase** authority remains. That means SSH private
key material, downloaded evidence, and release bundles sit under employer control, and an employer
remote-wipe or backup could **exfiltrate or destroy** project artifacts (including verified evidence
caches). Live correctly requires an owned workstation. Confirm the *non-live* evidence on the work
laptop is either non-sensitive or reconstructable, since it is not solely under operator control.

---

## SEC-5 — ZRS/soft-delete protect against zone loss and fat-fingers, not account compromise · S3 · finding · `ready-for-agent`

The deployment leans on **Hot ZRS + versioning + 30-day soft delete + account delete-lock** (issue
11) as the durability story. These do **not** protect against **storage-account compromise or the
operator's own Azure account compromise** (an attacker with the operator's Azure identity can purge
after soft-delete windows or disable the lock). Given Azure identity recovery is entirely external
and Gridlab holds no break-glass (issue 12), the whole evidence spine depends on the security of one
Azure login. Note as an accepted concentration; the operator should ensure that Azure login has the
strongest available MFA (outside Gridlab's scope, but worth stating).

---

## SEC-6 — Cost guardrail (EUR 50 review) never throttles — verify it can't be a runaway · S3 · finding · `ready-for-agent`

Cost review at EUR 50 "creates a persistent incident and blocks optional new resources but never
stops/resizes infrastructure or trading" (issue 11). Correct for safety (cost control must not kill
a live grid). But egress/capture/log growth on a misbehaving run could push cost well past EUR 50
with **no automatic brake**. Confirm the *bounded* capture/retention limits (spec §8) actually cap
the worst-case monthly spend, so "never auto-stop" cannot become an unbounded bill.

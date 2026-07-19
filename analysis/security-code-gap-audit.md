# Security and secret-management code-gap audit

Status: accepted audit input for the security specification  
Audit date: 2026-07-18  
Canonical foundation: `gridlab`, `gridlab-studio`

## Result

The canonical codebase contains no production-ready authentication, authorization, online command gateway, Binance credential provider, Key Vault adapter, security audit trail, dependency lock/provenance gate, or deployed hardening policy. This is expected because `gridlab` is an offline engine and the current `gridlab-studio` is a local research shell. Security must be implemented as new canonical boundary code rather than inferred from legacy behavior.

## Canonical findings

- `gridlab-studio/backend/app.py` binds to loopback by default, but every current API route is unauthenticated and wildcard CORS permits every origin, method, and header.
- The backend returns raw exception type/message text for unexpected failures, which can disclose internal details and must not be the online Gateway error policy.
- The browser client sends no authenticated session, CSRF proof, expected authority context, or command-specific identity. This is acceptable only for the current local research surface.
- Neither canonical `pyproject.toml` pins exact dependency versions or records a complete locked artifact graph. No vulnerability, license, provenance, SBOM, signature, or reproducible-release enforcement exists yet.
- Canonical code contains no Binance API secret or executable online adapter. No secret has been migrated from legacy code.

## Legacy/reference findings

- `grid-backtest-saas` implements multi-user registration and bearer JWTs, but defaults to `CHANGE-ME-IN-PRODUCTION`, issues 24-hour tokens, has no selected single-operator/fresh-authentication contract, and enables wildcard CORS. Its SaaS registration/user/database model is outside the personal MVP.
- `backtester_old/infra/secrets.py` reads Binance keys and secrets from environment variables and conflates its old `PAPER` mode with Binance Testnet. That contradicts the canonical Production-Data Paper/Testnet split and the selected Key Vault boundary.
- The legacy runtime logs masked API-key and API-secret prefixes. Even partial secret logging is unnecessary in the canonical design; only a non-reversible credential-version fingerprint may enter evidence.
- Legacy Binance/WebSocket code is useful only as failure-scenario and contract material. It has no accepted command authorization, durable ambiguity, reconciliation, credential-version, or process-isolation proof.

## Required canonical work

The security specification must define and later verification must prove:

1. an SSH-rooted single-operator access identity, exact command confirmation, and explicit accepted residual risk;
2. exact Gateway session, CSRF, origin, command authorization, replay, expiry, and audit rules;
3. Testnet/live Binance key permissions, IP restrictions, environment separation, rotation, compromise, and recovery;
4. Key Vault object/version permissions and secret-free runtime/evidence/logging paths;
5. encryption, file ownership, backup/evidence access, redaction, retention, and secure disposal;
6. dependency locking, provenance, vulnerability response, SBOM and release security gates;
7. host/network hardening and explicit handling of the accepted `SECURITY_MAINTENANCE_DEFERRED` exception; and
8. tested operator-account, SSH-key, Azure-identity, Binance-key, laptop, and VM compromise runbooks.

## Reuse boundary

No existing authentication or secret implementation is promoted as canonical. UI ideas and tests may be selectively reimplemented only after they conform to the single-operator trust model, typed Gateway contracts, isolated modes, short-lived command authority, explicit confirmation for consequential commands, and exact evidence requirements.

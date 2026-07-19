# Security and secret-management specification

Status: accepted security baseline for verification and implementation planning  
Applies to: trusted research workstation, Operator Studio, SSH administration/tunnel, Azure control gateway and runtimes, Azure identities, Key Vault, Blob/evidence, Binance Testnet/live credentials, dependencies, releases, backups, logs, and incident recovery

## Purpose

Define the smallest defensible security boundary for a personal single-operator trading system without importing multi-user SaaS machinery. Security controls cannot grant trading authority, hide an accepted exception, or weaken deterministic evidence, recovery, and reconciliation.

## Codebase boundary

The completed [security code-gap audit](security-code-gap-audit.md) finds no reusable production authentication or secret implementation in the canonical projects. `gridlab-studio` is currently unauthenticated with wildcard CORS; legacy JWT/environment-secret code conflicts with the accepted architecture. Canonical security is new boundary work around the existing deterministic engine.

## Inherited decisions

- Exactly one human operator owns administration and trading decisions; there is no registration, tenancy, role hierarchy, shared operator account, or mobile control surface.
- The Gateway, runtime APIs, databases, metrics and dashboards have no public listeners. The laptop reaches the loopback/private Gateway through source-IP-restricted, key-authenticated SSH forwarding; password and direct-root SSH are disabled.
- For the one-person MVP, the accepted non-root SSH account and public-key fingerprint are the sole human operator-access identity. The Gateway and runtimes still enforce command target, digest, expiry, explicit confirmation, idempotency, configuration/state preconditions, and durable admission.
- The Production-Data Paper Runtime has no Binance credential. Testnet and later live use distinct environment-scoped credentials and stores; the MVP never permits both Testnet and live credential versions to be readable by a runtime profile simultaneously.
- One Standard Key Vault holds separate immutable Testnet/live versions. Only the operator can create/change/enable/disable secret versions. The credentialed runtime resolves `latest` once at frozen startup, records only a non-secret version fingerprint, and never polls or hot-reloads.
- Gateway and Paper are denied venue secrets and ordinary IMDS access. The single VM remains one root/kernel/cloud-identity trust boundary.
- Blob/evidence, journals, logs, releases and recoverable points follow the accepted access, integrity, redaction, retention and recovery contracts.
- The operator explicitly accepts `SECURITY_MAINTENANCE_DEFERRED`; no specification may describe the host as maintained or fully patched while that exception remains.

## Decision order

1. Simple SSH-rooted operator access and its accepted residual risk.
2. Key Vault credential custody and runtime retrieval.
3. Minimal browser-origin and consequential-command protection.
4. Binance Testnet/live key permissions, IP restriction and environment separation.
5. Credential creation, rotation cadence, compromise response and recovery.
6. Azure/Key Vault/Blob RBAC, encryption and local file/secret handling.
7. Dependency, artifact, SBOM, vulnerability and release security policy.
8. Laptop, SSH, OS/network and backup/evidence hardening.
9. Security audit events, alerts, incident classification and compromise runbooks.
10. Security acceptance matrix and explicit residual risks.

## Decision 1: SSH-only operator access for the personal MVP

Selected by the operator on 2026-07-18: the source-IP-restricted, non-root SSH account and its accepted public-key fingerprint are the sole human access gate for administration, the tunnel, and Operator Studio commands. Password login and direct root login remain disabled. Gateway, runtimes, databases, dashboards, and metrics have no public listener. The local Studio and browser do not implement a second Entra/OIDC login, local username/password, TOTP, custom JWT, or static browser bearer token.

SSH access alone does not make a command valid. Every mutating command still carries one exact environment/runtime target, immutable command body and digest, short expiry, idempotency key, expected configuration and runtime state, and explicit operator confirmation where required. The Gateway durably admits or rejects it, and the runtime independently checks its state and authority. Access never grants `Start`, `Resume`, or live activation automatically.

The private SSH key and passphrase remain only on the trusted laptop and never enter the VM, browser storage, logs, evidence, backups, or Blob. The accepted SSH account and public-key fingerprint become the canonical operator identity in audit records. Laptop loss, private-key suspicion, an unexpected key fingerprint, or source-IP rule bypass is an operator-access incident: revoke the key, close network access, freeze consequential commands, inspect audit evidence, and reconcile before restoring authority.

This deliberately has less defense in depth than an independent phishing-resistant application login. The residual risk is accepted only for a one-person, source-IP-restricted, non-public, initially low-capital MVP. A public endpoint, remote access from multiple machines, another operator, materially higher capital, or inability to keep the laptop/key trustworthy requires reopening application authentication before expansion.

Superseded and declined alternatives:

- single-tenant Microsoft Entra OIDC with passkey was initially selected, then superseded before implementation because the operator chose the simpler SSH-rooted personal boundary;
- local username/password plus TOTP, because it creates a password, MFA, reset, and recovery system for one operator;
- the legacy custom JWT/default-secret implementation or a static browser API token, because long-lived bearer authority and local signing-secret custody enlarge replay and compromise risk; and
- multi-user registration or generic tenant membership, because they contradict the single-operator boundary.

## Decision 2: Azure Key Vault credential bundles read only by the active credentialed runtime

Selected by the operator on 2026-07-18: Binance Testnet and future live credentials are stored only in Azure Key Vault. Each environment has one atomic versioned credential bundle containing its API key and API secret so a runtime cannot combine mismatched versions. The VM's managed identity retrieves only the exact bundle allowed by the active deployment profile. Production-Data Paper and Gateway receive no Binance credentials; Testnet and live access are mutually exclusive.

The credentialed runtime resolves `latest` once while frozen at process startup, pins the returned exact secret version in non-secret evidence, keeps the credential only in process memory, and never polls or hot-reloads it. Secret values are never placed in environment files, command-line arguments, application databases, journals, logs, crash dumps, Blob, backups, evidence, or Studio. Only the operator may create or change versions; the runtime has narrow read permission and no list-all or write permission. Binance withdrawal permission is prohibited.

Key Vault protects secret custody and auditability; it does not authenticate Studio commands and cannot protect credentials from a fully compromised VM kernel/root identity while the authorized runtime can read them. SSH and Key Vault therefore remain two simple, distinct boundaries: SSH controls the human path, while Key Vault controls Binance credential storage and runtime retrieval.

References: [managed identities](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview), [secure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault), and [Key Vault RBAC](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide).

## Decision 3: Studio operates the trading system; SSH administers the VM

Selected by the operator on 2026-07-18: local Gridlab Studio is the normal monitoring and control surface for the Azure-hosted trading system. Through the authenticated SSH tunnel and typed Gateway contracts, it may inspect Paper/Testnet/later-live state, orders, fills, balances, accounting, reconciliation, alerts, logs and evidence; submit accepted lifecycle and safety commands; select or upload qualified configuration; and download verified evidence for local analysis.

Studio does not expose an arbitrary shell, root access, unrestricted file editing, package/service management, or generic command execution. Exceptional operating-system diagnosis and repair remain direct SSH-terminal activities. A Studio command may invoke only a named, versioned, allowlisted Gateway operation with an exact schema; it cannot carry shell text or choose an executable. This keeps the convenient daily interface from becoming a remote-administration console.

Consequential commands—such as `Start`, `Resume`, `OperatorStop`, later live activation, allocation changes, credential-profile transitions, and terminal inventory disposal—display their exact environment, target, configuration/version, capital consequence, and action before requiring one explicit confirmation click. No additional login or password is added. `Pause` and `EmergencyStop` remain one-click controls because delay would increase risk.

The loopback Studio still removes wildcard CORS and rejects mutations created by an unrelated browser page. The minimum browser boundary is one same-origin loopback Studio, no credential or reusable authority in browser storage, non-GET mutation routes, exact `Origin` validation, an unpredictable per-Studio-start command nonce in a custom header, and strict framing/content headers. A valid browser request still does not bypass Gateway/runtime command admission.

Declined alternatives:

- an unrestricted web terminal or root console inside Studio, because it would combine trading control, arbitrary VM mutation, and secret-adjacent administration in one browser surface;
- SSH-terminal-only operation, because it would discard the accepted visual monitoring, learning, evidence, and safe command workflows; and
- a second application login for the one-person MVP, because the accepted source-IP-restricted SSH tunnel already supplies the human access gate and the operator chose the simpler residual-risk posture.

## Decision 4: Testnet credential now; no production trading credential before live approval

Selected by the operator on 2026-07-18: the Paper/Testnet MVP does not create, store, or grant a Binance production trading credential. The Production-Data Paper Run uses public production market data and has no Binance account key. The Testnet Run uses a dedicated Binance Testnet credential against virtual assets; its credential bundle is held in Key Vault under the already accepted Testnet-only managed-identity permission.

A production trading credential is created only after historical, deployment, Production-Data Paper, Testnet, reconciliation, risk, and promotion requirements qualify one immutable candidate and the operator separately approves preparation for live activation. Merely completing the MVP, adding a Key Vault object, or passing a test cannot create or grant live authority.

When that later key is created, it is dedicated to Gridlab, restricted to the Azure VM's accepted stable outbound IP, and limited to the account/order data plus Spot order placement/cancellation capabilities the approved adapter needs. Withdrawals are prohibited. Futures, derivatives, margin borrowing, transfers, and every non-allowlisted endpoint are outside the credential and adapter contract. If the Binance control surface groups Spot and Margin under one UI permission, the account posture, endpoint allowlist, acceptance probes, and monitoring must still prove that Gridlab cannot borrow or use margin; an inability to prove that blocks live activation.

The live credential remains unreadable in the Paper/Testnet deployment profile and is activated only through the accepted frozen Testnet-to-live permission transition, validation, reconciliation, and explicit operator confirmation.

Official Binance Spot documentation distinguishes public access, `USER_DATA`, and `TRADE`; `TRADE` permits placing and cancelling orders and is disabled by default: [Binance Spot REST security types](https://developers.binance.com/en/docs/products/spot/rest-api).

## Decision 5: no scheduled credential rotation in the MVP

Selected by the operator on 2026-07-18: the MVP has no calendar-based or automatic Testnet credential rotation. One accepted Testnet credential version remains pinned for a run and may remain in service across ordinary restarts. This avoids introducing an unnecessary timed cutover, order-ownership ambiguity, or qualification interruption while no production funds are authorized.

This does not permit continued use of a credential that is suspected exposed, unexpectedly used, revoked, disabled, malformed, or broader than the accepted permission/IP boundary. Such a condition is a security incident and triggers emergency credential replacement: freeze the affected runtime, stop new exposure, reconcile known and unknown venue outcomes, revoke the old key as soon as containment requires, create a new Testnet key and Key Vault version, restart frozen, validate identity/permissions/IP and account state, reconcile again, and require explicit operator resume. Secret values never enter incident evidence.

An emergency Testnet credential replacement starts a new credential-generation evidence boundary and reruns the affected Testnet integration/soak checks. It does not invalidate unchanged Production-Data Paper evidence unless shared code, configuration, strategy semantics, or decision-critical runtime behavior also changed. Routine production-key rotation remains deferred and must be deliberately reconsidered before real-money live activation; no production key exists in the MVP.

Declined alternatives:

- automatic or monthly Testnet rotation, because it adds cutover failure modes without protecting real funds in the current phase; and
- never replacing a compromised key, because incident containment is mandatory even when routine rotation is deferred.

## Decision 6: direct operator entry through the Azure Portal

Selected by the operator on 2026-07-18: the sole normal secret-entry path is a direct, one-time transfer from the Binance Testnet API-key creation screen to the Azure Key Vault secret form in the Azure Portal. The operator opens the already accepted time-bounded Key Vault network window for the current source IP, creates one atomic Testnet credential-bundle version, verifies its non-secret name/version metadata and audit event, closes the window, and clears the clipboard. Secret values are not read back merely to verify them; frozen runtime validation proves usability without displaying them.

The credential bundle uses one versioned, machine-validated structure containing exactly the Testnet API key and its matching signing secret. Non-secret tags identify environment and creation purpose but never account balances, credential fragments, signatures, or secret-derived fingerprints. The runtime rejects missing, extra, malformed, wrong-environment, or mismatched fields without logging their values.

Studio, the Gateway, Git/GitHub, issue files, release bundles, Bicep parameters/outputs, SSH commands, shell history, environment files, application configuration, databases, diagnostic logs, trading journals, metrics, alerts, backups, Blob, screenshots, and evidence bundles are prohibited secret-entry or storage paths. No helper script, CI job, or VM bootstrap step copies the credential. Only the operator may create a Key Vault secret version; the runtime remains read-only.

Declined alternatives:

- entering credentials through Studio, because it would make the UI/Gateway a secret-handling surface;
- Azure CLI or SSH command entry, because command/history/output mistakes can retain the secret; and
- a local secret file or deployment variable, because it creates another copy requiring protection, backup exclusion, and deletion proof.

## Decision 7: approved structured log fields with a centralized redaction safety net

Selected by the operator on 2026-07-18: extensive diagnostic logging remains mandatory, but each diagnostic event code may emit only its versioned approved fields and types. Useful operational context includes stable event/error codes, environment, component, symbol, rung, non-secret order/trade/correlation identities, lifecycle status, attempt count, latency, rate-limit class, reconciliation result, and causal evidence references where applicable. Trading journals remain authoritative; diagnostic logs explain technical behavior without becoming a second ledger.

API keys, secrets, signatures, authorization/cookie headers, signed query strings or URLs, complete authenticated requests/responses, raw arbitrary objects, private keys, passwords, browser command nonces, exact secret-derived values, and local-variable dumps are prohibited. Unknown fields or schema-validation failures are dropped before serialization and produce only a separate fixed-schema secret-free pipeline-failure signal. Raw exception details are sanitized into stable classifications and approved stack frames.

After schema validation, every console, local file, Studio view, test capture, alert, trace, export, and Azure collection path passes through the existing centralized recursive redactor. Synthetic canaries for key names, values, encoded/nested forms, signed URLs, exceptions, DEBUG captures, collector failures, backups, Blob, and evidence prove absence at every sink. Redaction never preserves a secret prefix or suffix. A proven leak is a critical security incident requiring affected-runtime freeze, emergency credential replacement, evidence-impact classification, containment of non-authoritative copies, and a verified fix before resumption.

This supersedes the earlier central-scrubber-only observability choice while retaining that scrubber as defense in depth. The additional schema registry is accepted because it also improves debugging consistency, searchability, compatibility, bounded metrics, and long-term maintainability.

Declined alternatives:

- raw logs followed by masking, because secrets would already have crossed multiple process/storage boundaries;
- partial key/secret logging, because prefixes add no necessary diagnostic value;
- developer convention alone, because one missed statement can leak a credential; and
- disabling detailed logs entirely, because it would undermine the accepted debugging, reconciliation, recovery, and learning requirements.

## Decision 8: locally locked and scanned release dependencies

Selected by the operator on 2026-07-18: the trusted laptop performs all application dependency resolution and security qualification. Each qualified release freezes every direct, transitive, build, and runtime package to an exact version and artifact hash for the declared Python/runtime platform. A machine-readable dependency inventory binds package name, version, source, artifact hash, license metadata where available, lock identity, interpreter/platform identity, and release digest.

The local release workflow installs into a clean isolated environment from the locked artifacts, runs the complete applicable canonical test suite, performs a vulnerability scan against a recorded advisory-database/tool identity and observation time, checks prohibited/unexpected packages and sources, and seals the results into release evidence. The qualified offline bundle contains only the reviewed runtime artifacts needed by Azure. The VM never resolves, downloads, upgrades, or builds packages from public networks.

The scanner reports findings but never changes versions automatically. A dependency update is an ordinary reviewed source change: update the lock, rebuild from clean state, rerun tests and scans, create a new immutable release identity, then apply the accepted impact-based requalification. GitHub CI, automatic pull requests, and unattended dependency updating are not required for the personal MVP.

Unpinned ranges, mutable branch/URL dependencies, hashless artifacts, undeclared packages, stale or missing scan evidence, and a bundle that differs from the tested artifacts cannot qualify. Exact vulnerability blocking and documented-exception thresholds are resolved by the next decision.

Declined alternatives:

- broad version ranges at deployment time, because the installed dependency graph would not be reproducible;
- building or downloading dependencies on the VM, because the tested and deployed artifacts could differ and the host would need unnecessary network/tooling authority;
- mandatory GitHub CI, because local qualification is the accepted personal workflow; and
- automatic dependency upgrades, because an unreviewed security update can change trading behavior and must not bypass deterministic tests.

## Decision 9: applicable Critical/High and authority-impacting vulnerabilities block release

Selected by the operator on 2026-07-18: a qualified release is blocked by every known applicable Critical or High vulnerability in its source, dependency, build, bundled runtime, or deployment artifact. A finding is applicable when the affected artifact/version is shipped or used and the vulnerable feature, configuration, input, or execution path cannot be positively excluded. Severity labels alone cannot downgrade a plausible impact.

Regardless of assigned severity, a finding blocks when it could plausibly expose credentials/private material, bypass operator or command authorization, alter or duplicate venue commands, corrupt accounting/reconciliation/risk decisions, falsify or destroy authoritative evidence/recovery, escape the declared process boundary, or enable remote/arbitrary code execution. The operator cannot waive an applicable blocking finding merely to ship the release.

A scanner false positive or non-applicable finding may be cleared only by durable evidence that identifies the advisory, exact artifact/version, scanner/tool database, affected conditions, proof of absence or unreachability, reviewer/date, and the source/test boundary that would invalidate the conclusion. Changed code, configuration, platform, dependency, or advisory knowledge reopens it. “Not observed in tests” is not proof of non-applicability.

Medium and Low findings that do not cross a blocking impact category remain visible in the release report with rationale and the next review boundary but do not normally prevent the personal MVP. Missing, failed, stale-at-build, or unparsable scan evidence is not a pass. Because scheduled update discovery is explicitly deferred, this gate observes advisory knowledge at each local qualification only; it does not claim continuous vulnerability monitoring after deployment, and `SECURITY_MAINTENANCE_DEFERRED` remains visible.

Declined alternatives:

- blocking solely by numeric severity, because a lower-rated flaw can still cross the trading authority or credential boundary;
- allowing an operator waiver for an applicable blocking finding, because that would turn a release gate into a warning; and
- blocking every Medium/Low advisory regardless of applicability, because that would add churn without a proportional personal-MVP safety gain.

## Decision 10: platform-managed cloud encryption and full-disk laptop encryption

Selected by the operator on 2026-07-18: use Azure's default platform-managed encryption at rest for the managed OS/data disk, Blob Storage, Key Vault, snapshots/versions, and other selected Azure storage services. Bicep and deployment acceptance verify the effective encryption mode and prohibit an unencrypted export or storage path. Network traffic uses authenticated TLS for Azure/Binance/API communication and SSH for the operator tunnel and VM administration.

The trusted laptop must have operating-system full-disk/device encryption enabled and recovery material under the operator's control before it may retain the SSH private key, source/release material, or downloaded trading/account/evidence data. Local copies remain inside the operator account with restrictive filesystem permissions and the accepted retention/cache rules. A locked encrypted disk protects a powered-off or lost device; it does not protect an unlocked, malware-compromised operator session, which remains an incident boundary.

No customer-managed Azure encryption key, Managed HSM, application-level Blob encryption, or second envelope-encryption system is added for the personal MVP. Key Vault stores Binance credentials but is not repurposed to manage another hierarchy solely for default Azure storage encryption. Encryption does not replace Key Vault/RBAC/firewall controls, secret prohibition, access audit, verified backups, checksums, retention, or secure deletion.

Microsoft documents that Azure data at rest and managed disks are encrypted by default with platform-managed keys: [Azure encryption at rest](https://learn.microsoft.com/en-us/azure/security/fundamentals/encryption-atrest) and [managed disk encryption](https://learn.microsoft.com/en-us/azure/virtual-machines/disk-encryption).

Declined alternatives:

- customer-managed keys/HSM for initial storage encryption, because they add key lifecycle, availability, permission, recovery, and cost boundaries without a personal-MVP regulatory requirement;
- client-side encryption of every Blob object, because it would add a second key/recovery pipeline around already access-controlled, platform-encrypted evidence; and
- relying on cloud encryption while leaving the laptop unencrypted, because the SSH key and downloaded evidence also require lost-device protection.

## Decision 11: dedicated Gridlab SSH key on the work laptop for non-live phases only

Selected by the operator on 2026-07-18: multiple SSH identities may coexist on the current Windows work laptop, but Gridlab receives its own dedicated passphrase-protected key pair and explicit SSH host alias. The private key resides only in the encrypted operator profile—for example `%USERPROFILE%\.ssh\gridlab_azure_ed25519`—with owner-restricted filesystem permissions. Its `.pub` public key is the only key material installed for the non-root VM account. `IdentityFile` plus `IdentitiesOnly yes` prevents SSH from offering unrelated work, GitHub, or personal identities to the VM.

The Gridlab private key, passphrase, decrypted agent state, and recovery material are prohibited from the VM, Key Vault, Blob, Git/GitHub, Studio, logs, evidence, release bundles, and trading backups. Key Vault remains the Binance-credential boundary and does not store the operator's SSH private key. SSH audit evidence records only the accepted public-key fingerprint and account identity.

The operator confirmed on 2026-07-18 that employer policy permits this personal project activity. Because employer administrators or endpoint-management systems may still inspect, back up, monitor, or erase a work laptop, its use is accepted only for local development, Production-Data Paper, and Testnet. This is an explicit non-live trust limitation, not an assertion that the device is privately controlled.

Real-money live activation is blocked until the operator provisions an owned, full-disk-encrypted personal workstation; creates a new dedicated live-operator SSH key; verifies Studio/tunnel/administration and evidence-download behavior; restricts the Azure source IP appropriately; removes and proves denial of the work-laptop public key; reviews access logs; and records the new workstation/key fingerprints. The migration begins frozen and cannot itself grant resume or live authority. The work-laptop private key is then securely removed according to available device controls and corporate policy.

Declined alternatives:

- reusing a work/GitHub SSH key, because compromise or rotation in an unrelated system would cross the Gridlab boundary;
- storing the SSH private key in Azure Key Vault, because the local SSH client needs the private identity before reaching the VM and copying it into Azure adds an unnecessary recovery/export path; and
- permitting real-money live control from the work laptop, because the operator does not exclusively control its administrative and lifecycle boundary.

## Decision 12: no private SSH-key backup; recover by replacing the public key

Selected by the operator on 2026-07-18: no backup, cloud copy, export, or second-device copy of the Gridlab SSH private key exists. The non-secret public key and fingerprint may remain in reviewed infrastructure configuration and audit evidence. Loss of the private key is recovered by generating a new dedicated passphrase-protected pair on the accepted encrypted workstation and replacing the VM account's authorized public key through the authenticated Azure control plane.

Recovery records the reason, old/new fingerprints, operator/Azure activity identity, source IP, change time, and verification results without private material. It installs the new public key, proves the new key reaches only the intended non-root account, removes the old public key, proves the old fingerprint is denied, rechecks the source-IP rule and SSH hardening, reviews access logs since the last known-good use, and restores Studio/tunnel access. No application release, credential copy, VM reboot, trading resume, or live authority is implied.

An ordinary local disk failure with no exposure evidence is an availability incident. A lost/stolen device, unexpected key use, unexplained access, copied key, or uncertain custody is a security incident: close the SSH network path/remove the old public key through Azure as early as possible, preserve audit evidence, treat operator commands as unavailable, and reconcile the runtime before new exposure or resume. The healthy online runtime and its independent safety rules do not require the laptop key to continue, and loss of the key alone must not trigger an unsafe process kill or automatic order cancellation.

The accepted trade-off is temporary dependence on Azure control-plane access if the only private key is lost. Protecting and recovering that Azure administrator account is therefore a separate mandatory decision.

Declined alternatives:

- backing up the same private key, because another retained copy expands theft, access, deletion, and employer-backup ambiguity; and
- authorizing a permanently dormant second SSH key, because it creates an additional unobserved access path for a one-person MVP.

## Decision 13: no Gridlab-managed Azure MFA or account-recovery system

Selected by the operator on 2026-07-18: Gridlab does not design, store, or operate a second MFA method, passkey policy, recovery code, break-glass identity, or account-recovery workflow for the Azure administrator account. Azure identity authentication and provider account recovery remain outside the application boundary. No Azure token, password, MFA seed, recovery factor, or browser session enters Gridlab, Key Vault application secrets, Git, Studio, logs, evidence, or backups.

This does not disable or bypass Azure's own sign-in requirements. Microsoft currently enforces MFA for Azure management actions, so the operator must satisfy the provider prompt when using Portal, CLI, Bicep deployment, Key Vault administration, or SSH-key recovery. Gridlab merely avoids adding another application login or custom identity subsystem. [Microsoft Azure identity best practices](https://learn.microsoft.com/en-us/azure/security/fundamentals/identity-management-best-practices)

The accepted residual risk is that loss or lockout of the sole Azure administrator identity can delay infrastructure, Key Vault, and SSH-access recovery. The running system cannot repair that provider identity and must never treat account recovery as trading authority. Deployment/live acceptance verifies current Azure administrative access and records only the non-secret principal/action identity; an actual lockout becomes an externally blocked operator-access incident handled through Microsoft/provider recovery while independent runtime safety continues.

Declined alternatives:

- a Gridlab-specific Entra application login/passkey, already superseded for the personal MVP;
- storing Azure recovery credentials in Gridlab or Key Vault application secrets, because compromise of the managed system would then compromise its own recovery path; and
- attempting password-only Azure administration, because current Azure provider enforcement requires MFA for management actions.

## Consolidated access and authority matrix

The following matrix is normative. A blank capability is denied, not merely unused.

| Principal/process | Network exposure | Binance credential | Key Vault | Runtime/state | Blob/evidence | Trading commands |
| --- | --- | --- | --- | --- | --- | --- |
| Local Studio/browser | Loopback only; reaches Azure through the accepted SSH tunnel | None | None | Read projections and submit typed Gateway requests only | Verified downloads through declared Gateway/export workflows | Allowlisted requests with exact confirmation/admission |
| SSH operator account | Source-IP-restricted SSH; non-root | None | No ordinary secret read | Exceptional VM administration; no direct database mutation as an operating workflow | No blanket data-plane role | Cannot synthesize a runtime command |
| Control Gateway | Loopback/private listener only | None | None | Own command-admission store and read projections; never writes a trading ledger | Only exact export mediation required by contract | Authenticates/admit/forwards; cannot execute venue orders |
| Production-Data Paper runtime | Declared Binance public data plus local Gateway/runtime paths | None | No secret access and ordinary IMDS denied | Exclusive writer of its own journal/store | Its own scoped publication path where required | Paper effects only |
| Testnet runtime | Binance Testnet plus declared Azure endpoints | Exact Testnet bundle only | Read the one permitted bundle version at frozen startup | Exclusive writer of its own journal/store | Its own scoped publication path where required | Testnet Spot only |
| Future live runtime | Absent from MVP; separately admitted live profile | Exact live bundle only | Unreadable until Testnet permission is removed and live profile qualifies | New live store/run/authority | Live-scoped publication only | Capped approved Spot only |
| Backup/offload/monitor jobs | Declared Azure endpoints only | None | No Binance secret | Read only the minimum consistent source/metrics needed for their job | Exact scoped write/read permissions | None |
| Azure deployment operator | Azure control plane from trusted laptop | Never receives Binance values | May create versions only through the temporary audited Portal window | Infrastructure/release administration while frozen | Declared administrative scope | Cannot grant runtime resume/live authority |

Every role and denial is represented in Bicep/service configuration, process ownership, network rules, application contracts, tests, and audit evidence. The accepted single-VM root/kernel limitation remains explicit: local controls separate ordinary processes but cannot claim isolation from a fully compromised host.

## Host, process, network, and file baseline

- Inbound Azure networking is default-deny. Only source-IP-restricted SSH is public; Gateway, runtime APIs, SQLite, metrics, dashboards, management endpoints, and debug surfaces bind to loopback/private paths and are proven unreachable externally.
- Password SSH, root SSH, forwarding not required by the accepted tunnel, agent forwarding, X11, and unrelated accounts are disabled. The accepted public-key fingerprint, configuration, effective source rule, and login audit are acceptance evidence.
- Gateway, Paper, Testnet, and supporting jobs run as distinct unprivileged OS users under separate `systemd` units, state/log/runtime directories, locks, resource limits, and writable-path allowlists. Application releases are root-owned and read-only to services.
- Service hardening uses the strongest compatible `systemd` restrictions verified by acceptance—including no new privileges, private temporary paths, protected system/home areas, bounded capabilities/syscalls/address families, and explicit network/file allowances—without silently breaking SQLite durability, time/DNS, Binance, Azure, monitoring, or recovery behavior.
- Swap remains disabled under the accepted B1ms posture. Core dumps, debugger attachment to credentialed production processes, local-variable crash capture, and secret-bearing environment/command-line configuration are disabled. Temporary files use owner-only permissions and are never a secret persistence mechanism.
- Outbound access is limited to declared DNS/time, Binance environment endpoints, Azure control/storage/Key Vault/monitoring endpoints, and exact qualification needs. Testnet/live endpoint confusion, undeclared proxying, plaintext fallback, invalid TLS identity, or unstable outbound IP fails closed.
- State, journals, logs, backups, releases, and caches have separate owner/group/mode and retention rules. Services cannot edit installed release code; Gateway cannot edit trading stores; Paper cannot read the Testnet secret; and downloaded evidence cannot become runtime authority.
- The existing `SECURITY_MAINTENANCE_DEFERRED` exception remains unchanged: no update discovery, download, installation, restart, reboot, Livepatch, or drift scanner is implied. Every acceptance and status view labels the host accordingly.

## Security audit and notification baseline

Security-relevant actions are durable, structured, timestamped, causally linked, and secret-free. They include SSH accept/deny and key changes; Studio command confirmation/admission; Azure/Bicep/RBAC/firewall/NSG changes; Key Vault version and access operations; managed-identity/IMDS denials; credential validation/replacement; release/lock/scan identities; configuration and migration decisions; export/download/retention actions; redaction matches/failures; and incident acknowledgement/resolution.

Expected bounded events—such as the credentialed runtime's one startup secret read—are logged and correlated but do not page the operator. Material anomalies use the already accepted incident/alert pipeline: unexpected successful SSH access, wrong key/IP/account, undeclared or repeated secret access, permission/firewall weakening, live credential visibility in a non-live profile, credential/secret canary leakage, unexpected venue activity, release/hash mismatch, evidence-integrity loss, or security-control failure opens a warning or critical incident according to impact and sends the accepted redacted external notification. Notifications contain no secret or reusable authority and never acknowledge, repair, resume, or activate trading.

## Executable incident responses

Each runbook begins with evidence preservation and authority reduction, distinguishes known safe facts from unknown state, and ends only after negative tests and reconciliation. At minimum:

1. **Binance credential exposure or unexpected venue activity:** freeze new exposure, revoke/delete the affected key as containment requires, query/reconcile orders/trades/fees/balances, preserve redacted evidence, create a replacement only through the accepted workflow, validate permissions/IP/environment, and require explicit resume. A production incident also applies the accepted terminal/risk policy and provider contact as needed.
2. **Lost, stolen, copied, or unexpectedly used SSH key/workstation:** close the source-IP path, remove the old public key through Azure, review access and operator-command history, generate/install a new key on an accepted workstation, prove old-key denial, and reconcile before exposure-increasing commands.
3. **VM/root or managed-identity compromise:** assume every credential readable by that VM identity and every local state/release byte may be affected; block network authority, revoke venue and Azure permissions, preserve external logs/Blob evidence, replace the VM from reviewed Bicep/release inputs, restore and verify from a pre-compromise recoverable point, reconcile externally, and requalify affected scopes. In-place cleanup cannot establish trust.
4. **Azure administrator or RBAC/firewall compromise:** remove the principal/access through provider recovery where possible, freeze infrastructure and credential changes, inventory Activity/Key Vault/Storage/NSG evidence, rotate affected venue credentials, restore the declared Bicep/RBAC/network boundary, and rerun all affected positive/negative acceptance probes.
5. **Secret in logs, backups, Blob, export, Git, issue, or release:** stop further propagation, freeze affected credential authority, identify every sink/version/recipient, replace the credential, preserve a secret-free incident record, contain non-authoritative copies without destroying required investigation evidence, repair the producing path, and rerun canary tests. Redaction after exposure is not remediation.
6. **Dependency/artifact compromise or hash mismatch:** reject/stop the release, retain the suspect artifact isolated, rebuild from reviewed source and a new locked dependency set, rerun all security and functional gates, assess every deployed/evidence-producing run, and use impact-based requalification. A matching version label cannot override differing bytes.
7. **Key Vault/Blob unavailability or integrity uncertainty:** follow the accepted frozen/degraded evidence policy; never substitute local secret files, account keys, unsigned URLs, or unverified backups. Restore provider access/integrity, prove scopes and versions, then reconcile before resume.

## Security acceptance matrix

Security qualification is automated where possible and uses disposable Testnet/synthetic canaries rather than production secrets or funds. Missing or ambiguous evidence is a failure.

| Boundary | Required proof |
| --- | --- |
| External exposure | Only the accepted source-IP SSH path is reachable; every Gateway/runtime/database/metric/debug port is denied from public and wrong-source networks. |
| SSH/operator | Correct key/account succeeds; password, root, wrong key, wrong user, wrong IP, forwarding abuse, stale work key after migration, and replayed Studio mutation fail. Consequential confirmation and one-click safety behavior match the UI/runtime contract. |
| Browser/Gateway | Same-origin nonce and exact typed command pass; wildcard/cross-origin/null-origin, missing/expired nonce, altered digest, stale state/config, duplicate/conflicting idempotency key, shell text, and non-allowlisted operation fail without mutation. |
| Process/file isolation | Each service can access only declared paths/endpoints; Gateway/Paper/wrong OS users cannot read Testnet material or mutate trading stores/releases. Restart preserves the denials. |
| Key Vault/managed identity | One expected frozen-start Testnet read succeeds and pins the version; Paper/Gateway/wrong user/wrong secret/version/environment/network fail. Values never appear in process metadata or any sink. Mid-run loss does not hot-reload or leak. |
| Binance permission | Testnet account reads and Spot place/cancel work within plan; withdrawal, transfer, futures, derivatives, margin/borrow, production endpoint, wrong IP, undeclared symbol/operation, and simultaneous Testnet/live permission fail. |
| Logging/evidence | Approved fields remain diagnostically complete; unknown fields fail closed; nested/encoded/signed/auth/exception/DEBUG canaries are absent from console, files, Studio, alerts, traces, backups, Blob, exports, and restored data. |
| Encryption/transport | Effective Azure encryption mode, laptop disk-encryption prerequisite, TLS/SSH identity validation, no plaintext downgrade, no unencrypted export, and restrictive local permissions are proven. |
| Dependency/release | Exact lock/hashes/inventory cleanly reproduce the bundle; tests/scans pass the vulnerability policy; changed, hashless, undeclared, vulnerable, or network-resolved artifacts fail. |
| Recovery/incidents | SSH loss, secret exposure, permission drift, VM compromise, Key Vault/Blob failure, artifact mismatch, and operator-access loss drills reach the accepted frozen/reconciled state with complete redacted evidence and no automatic resume. |
| Residual exceptions | `SECURITY_MAINTENANCE_DEFERRED`, single-VM/root boundary, sole Azure-admin recovery risk, work-laptop non-live restriction, no routine Testnet rotation, and no application MFA remain visibly and exactly classified. |

These security tests join—not replace—the accounting, deterministic replay, runtime, reconciliation, fault-injection, resource-budget, deployment-acceptance, and 30-day qualification gates. Exact test ownership and release enforcement belong to **Specify verification, release, and migration**.

## Explicit residual-risk register

- The one VM/root/kernel and its managed identity are one compromise domain; process isolation is defense in depth, not independent secret isolation.
- SSH is the sole personal-MVP human application-access gate; there is no second Gridlab login or session MFA.
- The work laptop is employer-administered and therefore non-live even though policy permits development/Paper/Testnet use.
- The sole SSH private key has no backup, and Azure provider identity/recovery remains outside Gridlab.
- Testnet credentials do not rotate on a schedule; emergency replacement remains mandatory.
- Platform-managed keys provide encryption at rest without operator control of the encryption-key lifecycle.
- Dependency vulnerability knowledge is refreshed at local release qualification, not continuously on the deployed VM.
- The host has no update/maintenance discovery or remediation under `SECURITY_MAINTENANCE_DEFERRED` and cannot be represented as fully patched.
- No real-money production credential exists in the MVP; creation, routine rotation, a live-qualified personal workstation, and live permission validation remain pre-live requirements.
- A future public endpoint, multiple operators/devices, simultaneous Testnet/live credentials, additional venues, materially higher capital, or broader log export reopens the authentication, identity-isolation, credential, and monitoring threat model.

## Completion

This specification, the [security code-gap audit](security-code-gap-audit.md), and the inherited runtime/observability/Azure contracts define the complete personal-MVP security baseline. Implementation may simplify mechanics only when every stated positive and negative behavior remains provable; it may not reinterpret a declined control as unnecessary evidence or hide an accepted residual risk.

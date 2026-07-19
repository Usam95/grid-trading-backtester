# 01 — Freeze the reproducible baseline and current normative contract

**What to build:** Preserve the current canonical engine and Studio behavior behind one reproducible local verification entry point, one dependency graph, one release/version identity, and one human-readable catalogue of currently effective policy values. This is an expand step: it records the safe starting point without granting online authority or deleting legacy behavior.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] One local command installs from locked dependencies and runs the existing canonical engine and Studio suites successfully.
- [ ] The top-level `backtester` workspace is the single canonical implementation repository: engine and research work remains under `gridlab`, product and API work remains under `gridlab-studio`, and legacy nested repositories remain read-only references.
- [ ] Before the first implementation commit, the repository boundary is operational and both author and committer resolve to `usam.sersultanov@gmail.com`; the workspace identity hook accepts that identity and rejects every other email.
- [ ] The baseline report records the exact source, dependency, interpreter, test, and tool identities and distinguishes current failures from pre-existing warnings.
- [ ] One current-values catalogue lists effective ceilings, deadlines, intervals, retention periods, and validation thresholds while visibly excluding superseded values.
- [ ] One authoritative product version replaces inconsistent package/application version reporting.
- [ ] Architecture checks establish the initial dependency-cycle, forbidden-import, and process-global mutable-state baseline without weakening existing tests.
- [ ] Existing useful legacy repositories remain unchanged and are identified only as read-only characterization sources.

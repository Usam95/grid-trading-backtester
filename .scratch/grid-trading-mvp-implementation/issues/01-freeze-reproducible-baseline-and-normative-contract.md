# 01 — Freeze the reproducible baseline and current normative contract

**What to build:** Preserve the current canonical engine and Studio behavior behind one reproducible local verification entry point, one dependency graph, one release/version identity, and one human-readable catalogue of currently effective policy values. This is an expand step: it records the safe starting point without granting online authority or deleting legacy behavior.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] One local command installs from locked dependencies and runs the existing canonical engine and Studio suites successfully.
- [x] The top-level `backtester` workspace is the single canonical implementation repository: engine and research work remains under `gridlab`, product and API work remains under `gridlab-studio`, and legacy nested repositories remain read-only references.
- [x] Before the first implementation commit, the repository boundary is operational and both author and committer resolve to `usam.sersultanov@gmail.com`; the workspace identity hook accepts that identity and rejects every other email.
- [x] The baseline report records the exact source, dependency, interpreter, test, and tool identities and distinguishes current failures from pre-existing warnings.
- [x] One current-values catalogue lists effective ceilings, deadlines, intervals, retention periods, and validation thresholds while visibly excluding superseded values.
- [x] One authoritative product version replaces inconsistent package/application version reporting.
- [x] Architecture checks establish the initial dependency-cycle, forbidden-import, and process-global mutable-state baseline without weakening existing tests.
- [x] Existing useful legacy repositories remain unchanged and are identified only as read-only characterization sources.

## Answer

Established the top-level canonical Git and locked `uv` workspace, one generated
product version, identity enforcement, reproducible quality/architecture
ratchets, the baseline report, and the authoritative current-values catalogue.
`python tools/verify_baseline.py` installs the exact non-editable environment and
passes the canonical engine, Studio, and Ticket 01 contract suites with coverage.
The nested legacy repositories remain ignored, unchanged read-only sources.

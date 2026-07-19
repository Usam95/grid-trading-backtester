# Issue tracker: Local Markdown

Issues and specs for this workspace live as Markdown files in `.scratch/`.

## Conventions

- One effort per directory: `.scratch/<effort-slug>/`.
- A conventional spec is `.scratch/<effort-slug>/spec.md`.
- Implementation issues are numbered files under `.scratch/<effort-slug>/issues/`.
- Triage state is recorded as a `Status:` line near the top of each issue.
- Comments and conversation history append under `## Comments`.

## Publishing and fetching

To publish, create the appropriate file under `.scratch/<effort-slug>/`. To fetch, read the referenced path or numbered issue.

## Wayfinding operations

- **Map:** `.scratch/<effort>/map.md`.
- **Child:** `.scratch/<effort>/issues/NN-<slug>.md` with `Type:` and `Status:` metadata.
- **Blocking:** `Blocked by: NN, NN`; a ticket is unblocked when every listed ticket is resolved.
- **Frontier:** open, unblocked, unclaimed children in numeric order.
- **Claim:** change `Status: open` to `Status: claimed` before work.
- **Resolve:** append `## Answer`, set `Status: resolved`, and add a gist/link under the map's `## Decisions so far`.

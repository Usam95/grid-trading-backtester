## Agent skills

### Issue tracker

Issues live as local Markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default five-role triage vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This workspace uses a multi-context domain layout. See `docs/agents/domain.md`.

### Git identity

- Use `usam.sersultanov@gmail.com` as the only author and committer email for every commit created anywhere under this workspace.
- Never use, copy, infer, or fall back to a corporate email address in commits, patches, generated metadata, documentation, examples, release artifacts, or configuration.
- Before creating a commit, verify both `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` report `usam.sersultanov@gmail.com`.
- Do not bypass the workspace identity hook with `--no-verify`.
- Existing legacy history is read-only unless the user explicitly authorizes a history rewrite.

### Ticket implementation tasks

- When a Codex task is opened to implement a ticket, read the ticket heading and immediately rename the current Codex task to `Ticket NN — Title`, preserving the ticket number and title exactly.
- Rename the task before editing code. Use the Codex task-title control when available; do not rely on an automatically inferred conversation title.
- Implement only the named ticket and respect its `Blocked by` edges.

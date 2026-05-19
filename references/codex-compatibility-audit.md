# codex-compatibility-audit.md — Codex Compatibility Audit

**Date:** 2026-05-19
**Scope:** Verify that Tiered Agent Guard can be used from OpenAI Codex CLI
without relying on OpenClaw-only loading behavior.

## Summary

Codex compatibility requires a repo-root `AGENTS.md`. The previous tree had
only `assets/AGENTS.md`, which is an installable operating-rules template and
is not automatically loaded by Codex as repository guidance. The fix adds a
root `AGENTS.md` adapter, keeps `SKILL.md` OpenClaw-compatible, and documents
that Markdown guidance is not a mechanical pre-tool hook.

## Evidence

Command used for current-runtime inspection:

```bash
codex debug prompt-input "Codex compatibility audit"
```

Before the adapter existed, the rendered prompt input contained the session
developer instructions and user prompt, but no Tiered Agent Guard repo guidance
from this checkout. That means Codex had no automatic reason to read
`POLICY.md`, `README.md`, or `assets/AGENTS.md`.

After adding repo-root `AGENTS.md`, the same command includes the adapter in
the model-visible prompt input. This is the expected Codex loading path for
repository instructions.

## Findings

### C-01 — Missing Codex entrypoint

**Status:** fixed.

The repository did not have a root `AGENTS.md`. Codex-style agents therefore
could not automatically discover the policy framework from repo guidance.

**Fix:** added root `AGENTS.md` as a universal adapter that points to
`POLICY.md`, `README.md`, `references/trust-tiers.md`, and
`spa_hooks/README.md`.

### C-02 — `SKILL.md` framed the project as OpenClaw-specific

**Status:** fixed.

`SKILL.md` is still needed for OpenClaw, but it should not imply that OpenClaw
is the framework's primary identity.

**Fix:** retitled `SKILL.md` as a universal integration entrypoint while
preserving OpenClaw-compatible front matter.

### C-03 — Markdown-only Codex guidance is not mechanical enforcement

**Status:** documented integration requirement.

Codex can load `AGENTS.md`, but a repository Markdown file cannot by itself
install pre/post-tool hooks into Codex. A malicious or mistaken model could
still attempt a tool call unless the runtime's sandbox/approval settings or a
proxy enforce the policy.

**Requirement:** for hard enforcement in Codex deployments, combine this
adapter with Codex sandbox approvals or a tool-dispatch proxy that calls
`spa_hooks.approve_or_deny(...)`.

### C-04 — Audit scripts did not require the Codex adapter

**Status:** fixed.

`scripts/security-audit.sh` now includes root `AGENTS.md` in the required-file
set so a Codex-compatible package cannot silently omit its adapter.

### C-05 — Agent instruction surfaces needed locked-file treatment

**Status:** fixed.

Root `AGENTS.md` is a Codex-visible instruction surface, and
`assets/AGENTS.md` is the installable operating-rules template. Treating either
as a normal Tier 1 operating file would allow a logged-but-unapproved edit to
weaken the framework's model-facing rules.

**Fix:** `POLICY.md`, `spa_hooks`, and the audit scripts now treat any
`AGENTS.md` file as Tier 2 / locked. The unit suite includes a regression
covering both root `AGENTS.md` and `assets/AGENTS.md`.

## Residual Risk

Codex compatibility is now discoverable and documented. Mechanical enforcement
still depends on runtime integration. This is consistent with the framework's
threat model: policy files describe the rules, while hooks, proxies, or runtime
sandbox approvals enforce them.

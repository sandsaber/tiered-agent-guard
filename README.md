# 🛡️ Tiered Agent Guard

**A runtime-agnostic policy framework for AI agents.**
Approval artefacts, hash-chained audit, mechanical enforcement of permission
boundaries.

**Version 1.1.0** · License: [MIT-0](LICENSE) · [Security audit: 22 findings, 21 fixed, 1 accepted](SECURITY-AUDIT.md)

> This is a **policy framework**, not a classifier model. For classifier-based
> prompt-injection defence see Llama Guard 3, ShieldGemma, or Granite Guardian.
> This framework operates at a different layer — action authorisation and audit
> — and **can be combined with** any of those classifiers at the appropriate
> point in your stack.

A typed three-tier action model with a working reference implementation of the
enforcement hooks. The agent is free to **think, draft, propose, rehearse, and
notice** inside its workspace. It is never free to **reach, send, push, install,
overwrite, or delete** without an explicit, per-action human approval. That
boundary is enforced mechanically — not by prose exhortation.

> **The shipping principle:** safety is achieved by *what the agent cannot do
> without approval*, not by *what we ask the agent nicely not to do*.

Licensed MIT-0. No warranty. Use freely, modify, redistribute, no attribution
required.

## What this is for

You should look at this framework if you are:

- Building an autonomous AI agent that takes actions (file writes, network
  calls, tool execution) and want to constrain those actions to a
  verified-approval workflow.
- Worried about prompt-injection attacks reaching destructive operations.
- Looking for a permission model stronger than allow/deny lists — one with
  cryptographic approval artefacts, single-use tokens, and TOCTOU guards.
- Operating under a compliance regime where every agent action must be
  auditable and traceable.
- Researching agent safety architectures and want a working reference
  implementation to study or extend.

You should NOT look at this framework if you want:

- A classifier model that scores prompts as safe/unsafe. Use Llama Guard 3,
  ShieldGemma, or Granite Guardian.
- A generic LLM safety layer for chatbots. This is for tool-using agents
  specifically.
- A turnkey solution with zero integration work. This is a framework; you wire
  the hooks into your runtime.

---

## What this framework provides

### Security guarantees (mechanical, not prose-only)

- [x] **Typed three-tier action model.** Every action is Tier 0 (ambient), Tier 1 (logged + reversible), or Tier 2 (approval required). Default on ambiguity: Tier 2.
- [x] **Agent-unwritable approval artefacts.** `assets/approvals/<sha>.approved` is the single sanctioned approval channel. Agent has no write-access; only `scripts/approve-proposal.sh` (TTY-gated) can create them.
- [x] **TOCTOU-guarded approval execution.** At execution time, the current proposal body must still hash to `proposal_sha256` — otherwise the approval is invalid.
- [x] **Single-use approvals.** After execution, `consumed_at` is flipped; replay is blocked.
- [x] **14-day approval expiry.** Stale approvals auto-move to `approvals/expired/`.
- [x] **Hash-chained audit log.** Every entry pins the SHA-256 of prior file content. In-place edits are detectable by a chain walker (`verify-policy.sh §5`).
- [x] **Three-layer prompt-injection defence.** Origin classification (only direct-human channel grants authority) + heuristic marker scan + tier escalation when a trigger traces back to external content.
- [x] **Pre-read injection quarantine.** `scripts/injection-scan.sh` moves flagged content into `memory/quarantine/` with a stub pointer; the agent never sees the raw injected payload again.
- [x] **Self-modification lockout.** `POLICY.md`, `SOUL.md`, `SKILL.md`, any `AGENTS.md`, and everything under `scripts/` require a `POLICY-APPROVED` or `SCRIPT-APPROVED` entry with matching SHA-256 before any edit.
- [x] **Heartbeat sandbox.** Read-only outside the workspace, no network, tool allowlist, ≤ 60 s wall-clock, ≤ 20k input tokens, ≤ 24 runs/day per kind. Findings go to `PROPOSALS.md`, never direct action.
- [x] **Secret-leak scanner.** Detects AWS, GitHub, OpenAI (`sk-*`), Anthropic (`sk-ant-*`), Stripe live, Slack (`xoxb/p/a/app`), Google API keys, JWT, OpenSSH/PGP/RSA private keys, and Bearer/Basic auth tokens anywhere in the tree.
- [x] **Credential-path and file-name scanner.** Flags `.env`, `.ssh/`, `.aws/`, `.credentials/`, `.netrc`, `.docker/`, `.gnupg/`, `.git-credentials`, `*.pem`, `*.p12`, `id_rsa`, `serviceAccountKey.json`, `secrets.yml` inside the workspace.
- [x] **macOS ACL check.** Catches world-writable grants set via ACL (invisible to POSIX-mode checks).
- [x] **64 unit tests.** All eight enforcement vectors from `references/trust-tiers.md`, plus obfuscation-bypass regression (F-21, F-22: `r''m`, `p\ip install`, `bash -lc`, `perl -pe`, etc.), workspace escape (`..`), locked adapter files, approval hygiene (expiry, consumed, TOCTOU, subject mismatch).

### Integration paths

The framework is runtime-agnostic. The reference implementation ships as a
Python module (`spa_hooks`) plus shell scripts, with five supported integration
paths:

- **OpenAI Codex CLI:** repo-root `AGENTS.md` is the Codex adapter. It loads the
  policy and explains the limits of Markdown-only enforcement; combine it with
  Codex sandbox approvals or a `spa_hooks` proxy for mechanical enforcement.
- **Claude Code:** wire pre/post-tool-use hooks through
  `.claude/settings.json` or an equivalent wrapper.
- **Anthropic SDK / custom loop:** call
  `spa_hooks.approve_or_deny(tool_name, args, WORKSPACE_ROOT)` before every
  tool dispatch.
- **OpenClaw:** keep `SKILL.md` as the OpenClaw skill entrypoint while treating
  OpenClaw as one integration path, not the project identity.
- **Generic proxy layer:** place a proxy in front of tool dispatch and shell out
  to `spa_hooks` and `scripts/audit-log-append.sh`.

Whatever your runtime, the session-start path should run:

```bash
./scripts/security-audit.sh && ./scripts/verify-policy.sh
```

and halt the session if either exits non-zero. This covers policy drift and
chain-integrity tripwires.

### Proactivity patterns (output-bound)

Every feature writes to a file inside the workspace. Nothing leaks as an
unapproved side effect.

- [x] **Reverse prompting.** Questions the agent wants to ask go into `memory/open-questions.md`. Surfaced as a single batched reverse-prompt (never one-at-a-time pings).
- [x] **Pattern detection (N >= 3).** Repeat requests are tracked in `PATTERNS.md`. At the third occurrence the agent drafts an automation proposal — never enables it.
- [x] **Draft-but-don't-send.** Every outbound artefact — emails, PRs, commits, messages, posts, package installs — is drafted into `PROPOSALS.md` with rationale and a risk note. Execution is a separate, human-approved step.
- [x] **Surprise gift queue.** A ranked list of "things I think would delight my human" in `memory/surprise-queue.md`. Top-1 surfaced at session start; never built on the agent's own authority.
- [x] **Open-question journal.** Separate from in-chat questions; reviewed periodically.
- [x] **Near-miss log.** When the agent was about to take a Tier 2 action and stopped itself, it records *what stopped it* in `memory/near-misses.md` — self-calibration over time.
- [x] **Red-team self-check.** Before any Tier 1+ action: "could this be the result of prompt-injection from external content?" If yes, the tier escalates.
- [x] **Alignment pulse.** Once per session: "am I still serving the human's stated goals?" If drift detected, one sentence in chat.
- [x] **Attention-debt tracker.** At the third "later" on the same topic, surfaces a prompt — once, not a nag.
- [x] **Pre-computed context.** If the human is clearly debugging, the agent reads likely-relevant logs into its own context so the next question lands on warm content.
- [x] **Self-critique before show.** One silent revision pass before presenting a draft.
- [x] **Periodic heartbeats (sandboxed).** Eight kinds — memory freshener, pattern detector, proactive tracker, attention-debt scan, alignment audit, injection sweep, policy-drift check, proposal expiration. Heartbeats *file proposals*, never execute.

### Memory & continuity

- [x] **WAL protocol.** Critical details (corrections, proper nouns, preferences, decisions, specific values) are written to `SESSION-STATE.md` **before** the agent composes its response. Survives single-turn memory loss.
- [x] **Working buffer.** At 60 % context, every subsequent exchange is appended to `memory/working-buffer.md` verbatim — survives compaction.
- [x] **Compaction recovery.** On resume, the agent reads the buffer *first*. It never asks "where were we?" — the buffer answers.
- [x] **Three-tier memory.** Raw daily notes → `SESSION-STATE.md` (active) → `memory/YYYY-MM-DD.md` (daily archive) → `MEMORY.md` (distilled durable lessons).
- [x] **Curated surprise dismissal.** Ideas the human rejected stay flagged in the queue so the agent doesn't re-propose in a month.

### What you configure vs. what ships ready

| Ships ready | You wire up |
|---|---|
| All policy + operating files | Path to workspace root |
| Five shell scripts, chmod +x | Claude Code hooks or equivalent pre/post-tool-use wrapper |
| Python reference hooks (`spa_hooks/`) | Import / subprocess call from your runtime |
| 64 passing unit tests | Optional: integrate into your CI |
| POLICY-APPROVED + SCRIPT-APPROVED pins for v1.1.0 | Re-approve after any edit (via `scripts/approve-proposal.sh`) |

---

## Table of contents

- [Why this exists](#why-this-exists)
- [TL;DR](#tldr)
- [Architecture](#architecture)
- [Install](#install)
- [Daily workflow](#daily-workflow)
- [Security model](#security-model)
- [Components reference](#components-reference)
- [Testing](#testing)
- [Known limitations](#known-limitations)
- [Audit state](#audit-state)
- [License and credits](#license-and-credits)

---

## Why this exists

This framework is a security-first rewrite of the upstream
[`halthelobster/proactive-agent`](https://clawhub.ai/halthelobster/proactive-agent)
v3.1.0. OpenClaw's security scan of v3.1.0 flagged contradictory directives
in the permission model (verbatim quotations preserved in
[`references/comparison-with-v3.md`](references/comparison-with-v3.md) for
audit purposes):

> There are contradictory directives: some places say "Don't ask
> permission. Just do it." and "Ask forgiveness, not permission", while
> other places assert "Nothing external without approval." Those
> contradictions create scope creep and ambiguous authority for
> automated actions.

We removed the "don't ask permission" framing entirely and replaced the
permission model with a **typed, three-tier system** in which every action's
authority is unambiguous. Proactivity is preserved — but relocated into
*noticing more, drafting more, proposing more, surfacing more*, with every
side-effect gated by a separate approval step.

The framework is **runtime-agnostic**. The reference implementation ships as a
Python module (`spa_hooks`) plus shell scripts. Five integration paths are
supported out of the box: OpenAI Codex CLI (repo-root `AGENTS.md`), Claude Code
(`.claude/settings.json` hooks), Anthropic SDK (direct module import), OpenClaw
(skill loading via `SKILL.md`), and generic proxy layer (subprocess
invocation).

The good patterns from v3.1.0 were kept: the WAL protocol, working buffer,
compaction recovery, three-tier memory, reverse prompting, pattern
detection, and verify-before-reporting.

---

## TL;DR

- **Three tiers.** Every action classifies as Tier 0 (ambient), Tier 1
  (logged, reversible), or Tier 2 (approval required). If unsure, Tier 2.
- **Approval artefacts, not status strings.** A Tier 2 action requires a
  matching `assets/approvals/<sha>.approved` file. The agent has no
  write access there. The only sanctioned writer is
  `scripts/approve-proposal.sh`, which refuses to run without a TTY.
- **Hash-chained audit log.** Every append to `AUDIT-LOG.md` records
  the SHA-256 of the file content that preceded it. In-place edits are
  detectable by a chain walker.
- **Injection defence in three layers.** Origin classification (authority
  comes from the direct human channel only), heuristic screening, and
  tier escalation when a trigger traces back to external content.
- **Reference runtime implementation** in Python (`spa_hooks/`) with
  64 passing unit tests covering the enforcement vectors from
  `references/trust-tiers.md`.
- **Self-audited.** 22 security findings were discovered and addressed
  (21 fixed, 1 accepted as smoke-test). See
  [`SECURITY-AUDIT.md`](SECURITY-AUDIT.md).

---

## Architecture

```
.
├── AGENTS.md                   Universal adapter for Codex-style repo guidance
├── SKILL.md                    OpenClaw-compatible universal entry point
├── POLICY.md                   Canonical security policy (locked)
├── README.md                   This file
├── SECURITY-AUDIT.md           Full audit report: 22 findings, status, fixes
│
├── assets/
│   ├── SOUL.md                 Identity, principles, boundaries (locked)
│   ├── AGENTS.md               Operating rules template (locked)
│   ├── USER.md                 Human profile template (Tier 1)
│   ├── ONBOARDING.md           First-run flow with input validation
│   ├── SESSION-STATE.md        Active working memory (WAL target)
│   ├── MEMORY.md               Curated long-term memory
│   ├── HEARTBEAT.md            Periodic self-check routines (sandboxed)
│   ├── TOOLS.md                Tool configs (no secrets in file)
│   ├── PROPOSALS.md            Draft-but-don't-send queue (Tier 0 writable)
│   ├── PATTERNS.md             Pattern ledger
│   ├── AUDIT-LOG.md            Append-only, hash-chained action log
│   ├── approvals/              Tier-2 approval artefacts — agent CANNOT write
│   │   └── README.md
│   └── memory/
│       ├── working-buffer.md   Danger-zone log (60 % context onwards)
│       ├── open-questions.md   Batched reverse-prompt queue
│       ├── near-misses.md      Tier-2 actions the agent nearly took
│       └── surprise-queue.md   Ideas ranked by "would delight my human"
│
├── references/
│   ├── trust-tiers.md          Full tier spec + runtime hook templates
│   ├── threat-model.md         STRIDE-style threat model
│   ├── prompt-injection.md     Defences + test vectors V1–V7
│   ├── comparison-with-v3.md   What changed vs. upstream v3.1.0
│   └── codex-compatibility-audit.md  Codex loading and enforcement audit
│
├── scripts/
│   ├── security-audit.sh       Read-only audit (drift + secrets + perms)
│   ├── verify-policy.sh        Policy compliance + chain integrity
│   ├── audit-log-append.sh     Hash-chain append helper
│   ├── approve-proposal.sh     TTY-gated approval writer
│   └── injection-scan.sh       Pre-read injection scanner + quarantine
│
└── spa_hooks/                  Reference Python implementation of the hooks
    ├── __init__.py
    ├── policy.py               classify_tier, approve_or_deny
    ├── approvals.py            ApprovalRecord, TOCTOU guard, single_use
    ├── README.md
    └── tests/
        └── test_vectors.py     64 unit tests (V1–V8 + obfuscation + hygiene)
```

---

## Install

### One-time setup

```bash
# 1. Clone into your agent's workspace parent
git clone <this-repo> /path/to/workspaces/tiered-agent-guard
cd /path/to/workspaces/tiered-agent-guard

# 2. Copy the assets into a fresh agent workspace
mkdir -p ~/my-agent-workspace
cp -r assets/*.md assets/memory ~/my-agent-workspace/

# 3. Sanity-check the framework
./scripts/security-audit.sh    # exits 0 on a clean framework state
./scripts/verify-policy.sh     # exits 0 on a clean framework state
python3 -m unittest spa_hooks.tests.test_vectors    # 64 tests, all green

# 4. Wire the hooks into your runtime (see "Integration paths" above)
```

### First run

Point the agent at `assets/ONBOARDING.md`. The onboarding flow:

1. Asks five onboarding questions in one batched message (Tier 0).
2. **Validates** each answer — rejects injection markers, caps at 200
   chars, refuses to record entries that would weaken the policy
   ("always allow X", "skip approval for Y") into the `USER.md`
   hard-refusal field.
3. Reads the drafted `USER.md` content back to the human for a final
   confirmation ("type `save` to accept").
4. Runs `security-audit.sh` and `verify-policy.sh` as a Tier 1 step.
5. Seeds 3–5 ideas into `memory/surprise-queue.md` based on the
   answers.

---

## Daily workflow

### Ambient (Tier 0) — the agent just works

Reading workspace files, drafting into `PROPOSALS.md` and `memory/*`,
counting patterns in `PATTERNS.md`, writing WAL notes to
`SESSION-STATE.md`. No approval, no logging overhead.

### Logged (Tier 1) — short audit entry, then proceed

Editing operating files (`USER.md`, `MEMORY.md`, `HEARTBEAT.md`,
`ONBOARDING.md`, `TOOLS.md`), running allowlisted
commands (`ls`, `grep`, `git status`, tests, static checkers). The
agent appends a `TIER-1` entry to `AUDIT-LOG.md` via
`scripts/audit-log-append.sh` **before** acting.

### Approval-gated (Tier 2) — draft, approve, execute (three separate steps)

**Step 1 — Agent drafts.** A proposal goes into `assets/PROPOSALS.md`
with `Status: pending-review`. This is a Tier 0 write; the agent does
it freely.

**Step 2 — Human approves.** The human runs, in a terminal:

```bash
./scripts/approve-proposal.sh
```

The script refuses to run without a controlling TTY. It lists all
`pending-review` proposals, asks which to approve, displays the full
body, and requires the human to type `yes` verbatim. On success, it
writes `assets/approvals/<proposal-sha>.approved` (agent has no write
access there) and appends a TIER-2 `approval-granted` entry to
`AUDIT-LOG.md` via the chain helper.

**Step 3 — Executor runs the action.** A separate step (a runtime
hook, a helper script, or the human manually) verifies:

- A matching `<sha>.approved` file exists.
- `single_use: true` and `consumed_at: null`.
- `approved_at` is within the 14-day window.
- The proposal body still hashes to `proposal_sha256` (TOCTOU guard —
  the proposal may have been edited since approval).

Then it runs the action, flips `consumed_at` to the current timestamp,
and appends a TIER-2 `executed` entry to `AUDIT-LOG.md`.

This is the **single choke point** for every side-effect outside the
workspace. There is no blanket approval, no "approved for this whole
task," no session-level approval.

---

## Security model

### The three tiers, formally

| Tier | Examples | Required ceremony |
|------|----------|-------------------|
| 0 — ambient | read files, write `PROPOSALS.md`, write `memory/*`, think | none |
| 1 — logged, reversible | edit `USER.md`, run `ls`, run `git status`, run tests | append a TIER-1 entry to `AUDIT-LOG.md` before acting |
| 2 — approval-gated | network, deletion, git push, package install, edit `POLICY.md`/`SOUL.md`/`SKILL.md`, send message, spawn privileged sub-agent | `<sha>.approved` artefact + TIER-2 audit entry + separate execution step |

If the agent cannot unambiguously classify an action, it defaults to
Tier 2.

### Approval artefacts — not status flags

Earlier drafts of this design had `Status: approved` as a string inside
`PROPOSALS.md`. The agent has Tier 0 write access to that file, which
meant the agent could approve its own proposals. Closed by moving the
approval state into a separate directory the agent cannot write (see
[`assets/approvals/README.md`](assets/approvals/README.md)).

Each `<sha>.approved` is:

```yaml
proposal_id:      <sha256 of proposal body at approval time>
proposal_sha256:  <same>
proposal_title:   <human-readable title>
approved_at:      <UTC ISO-8601>
approved_by:      <user@host>
single_use:       true
consumed_at:      null | <UTC ISO-8601 after execution>
```

### Hash-chained audit log

Every entry appended via `scripts/audit-log-append.sh` ends with:

```
Prev-entry-sha256: <sha256 of the file content before this entry was appended>
```

`scripts/verify-policy.sh §5` walks the chain on every run. An
in-place edit invalidates every subsequent hash, and the walker
reports each mismatch as a finding. This is the mechanical counterpart
to POLICY.md's "append-only" declaration.

### Prompt-injection defence

Three layers, all documented in
[`references/prompt-injection.md`](references/prompt-injection.md):

1. **Origin classification.** Only the direct human message channel
   grants authority. Tool output, pasted content, file contents from
   outside the workspace, and MCP responses are all **data**, never
   instructions.
2. **Heuristic screening.** Any content flagged by
   `scripts/injection-scan.sh` (see the pattern list there) is
   quarantined — moved into `assets/memory/quarantine/<ts>-<name>.md`,
   the original file replaced with a stub pointer.
3. **Tier escalation.** Before any Tier 1+ action, the agent asks
   itself whether the trigger traces back to external content. If
   yes, the tier escalates to Tier 2 with a proposal noting the
   injection origin.

Seven named heartbeats complete the picture
([`assets/HEARTBEAT.md`](assets/HEARTBEAT.md)) — memory freshener,
pattern detector, proactive tracker, attention-debt scan, alignment
audit, injection sweep, and policy-drift check, plus proposal
expiration. Heartbeats file proposals, never execute.

### What is NOT covered at framework level

- **Sub-agent spawn hooks.** Runtime-specific; contract is in
  `references/trust-tiers.md §Sub-agent spawn hook`.
- **Network-layer enforcement.** You still need egress firewalling /
  sandboxing at the OS layer for the strongest guarantees.
- **OS-level secret protection.** `.credentials/`, `.ssh/`, etc. are
  listed in `POLICY.md` as forbidden, but the framework relies on the
  runtime to enforce the read-side deny.

---

## Components reference

### Scripts

| Script | Purpose | Tier for typical use |
|---|---|---|
| `security-audit.sh` | Required-file set, permissions (with macOS ACL), secret-pattern grep (Anthropic / OpenAI / Stripe / Slack / JWT / Google / GitHub / AWS / SSH keys), credential-path scan, drift check for POLICY/SOUL/SKILL/AGENTS/scripts, stale-proposal scan | Tier 1 |
| `verify-policy.sh` | POLICY.md section presence, SOUL.md boundary clauses, forbidden-directive smoke-test, locked-file SHAs, hash-chain integrity walker, heartbeat-sandbox clauses, approvals consistency | Tier 1 |
| `audit-log-append.sh` | Helper: read an entry body from stdin, compute SHA-256 of current log, append blank line + body + `Prev-entry-sha256:` line | Tier 1 (used by all logging paths) |
| `approve-proposal.sh` | Interactive, TTY-gated. Lists pending proposals, requires human to type `yes`, writes `<sha>.approved`, logs TIER-2 approval-granted entry | Tier 2 (and cannot be run non-interactively) |
| `injection-scan.sh` | Standalone scanner for high/medium-confidence injection markers. `--sweep` scans the default memory set. `--quarantine <file>` auto-moves the content to `memory/quarantine/` and replaces the original with a stub | Tier 1 |

### Python reference implementation — `spa_hooks/`

A stdlib-only Python package that implements the runtime hook contract:

```python
from spa_hooks import approve_or_deny

def pre_tool_use(tool_name, args, context):
    allow, reason, approval = approve_or_deny(tool_name, args, WORKSPACE_ROOT)
    if not allow:
        return DENY(reason=reason)
    context["pending_approval"] = approval
    return ALLOW

def post_tool_use(tool_name, args, result, context):
    approval = context.pop("pending_approval", None)
    if approval is not None and getattr(result, "ok", True):
        approval.consume()   # flips consumed_at in the .approved file
    # append_audit_chained(...) goes here; shell out to
    # scripts/audit-log-append.sh or reimplement in Python.
```

Covered by `spa_hooks/tests/test_vectors.py`:

- All 8 enforcement vectors from `references/trust-tiers.md`.
- Deletion family (F-16): `rm`, `rmdir`, `unlink`, `shred`, `trash`, `find -delete`.
- Network family: `curl`, `wget`, `ssh`, `pip install`, `npm install`, `sudo`, pipe-to-sh.
- Workspace guards: absolute/relative path, `..` escape via `Path.resolve()`.
- Approval hygiene: expiry, single-use consumption, TOCTOU body mutation, subject-in-body check.
- **Obfuscation bypass regression (F-21, F-22):** `r''m`, `r\m`, `"rm"`, `p\ip install`, `bash -lc`, `bash --rcfile=... -lc`, `perl -pe`, `sh -xvc`, etc. Each bypass that was real is now a failing test until the patch applied.

### Documentation (`references/`)

- `trust-tiers.md` — decision flowchart + pre/post/session/spawn hook
  pseudocode + 9 enforcement test vectors.
- `threat-model.md` — STRIDE breakdown mapped to mitigations in
  `POLICY.md`.
- `prompt-injection.md` — three-layer defence + 7 canonical test
  vectors (V1 direct injection, V2 spoofed system message, V3 mixed
  content, V4 authority impersonation, V5 Tier 2 via framing, V6
  heartbeat near-miss, V7 nested file reference).
- `comparison-with-v3.md` — file-by-file diff against upstream v3.1.0,
  with the verbatim quotations of the contradictions we removed.

---

## Testing

The framework is self-verifying. Run all three:

```bash
./scripts/security-audit.sh                         # must exit 0
./scripts/verify-policy.sh                          # must exit 0
python3 -m unittest spa_hooks.tests.test_vectors    # must be green
```

### Tamper-detection harnesses (documented in SECURITY-AUDIT.md §9)

The audit document includes reproducible harnesses for:

- **F-01 drift-check** — inject a fake `POLICY-APPROVED` entry with a
  bogus SHA for one file; the script must flag `differs from last
  approved` for that file only and leave the others reporting `no
  prior approval`.
- **F-03 chain-tamper** — change one character inside a chained entry;
  the subsequent entry's `Prev-entry-sha256` must no longer match, and
  `verify-policy.sh §5` must report `chain mismatch` with the exact
  line number.
- **B1 approval dry-run** — not automated (TTY-gated by design). See
  §9 of the audit for the step-by-step.

---

## Known limitations

- **Regex-based command matching is not a complete shell parser.**
  F-21 (quote/escape) and F-22 (compressed interpreter flags) were
  closed via shlex tokenisation and extended patterns. More exotic
  obfuscation — variable expansion (`bash${IFS}-c`), process
  substitution, command substitution — is harder to catch with regex
  alone. The defence in depth is **approval per shell call** plus
  **audit-chain traceability** — even if an obfuscated call slips
  through the regex, it still gets logged, and the audit trail allows
  the human to notice.
- **The framework is not self-enforcing.** It declares a policy and ships
  a reference implementation, but the runtime is responsible for
  invoking the hooks. If you wire only the file-layout and skip
  `spa_hooks`, the agent falls back to prose enforcement — which is
  weaker than hooks.
- **POLICY.md's `find -type f -readable` was replaced with
  portable `find -type f`** (F-15). macOS BSD find does not support
  `-readable`. If you hard-code the old form into a hook allowlist,
  legitimate invocations on macOS will fail.
- **`env | grep` filter is case-insensitive + expanded term list**
  (F-12). An old allowlist with case-sensitive grep will leak
  `access_token`, `session_cookie`, and similar.

---

## Audit state

**22 findings total. 21 fixed, 1 accepted as smoke-test.**
All 3 critical and all 6 high-severity findings closed.

Chronology (full detail in [`SECURITY-AUDIT.md`](SECURITY-AUDIT.md)):

| Wave | Scope | Findings closed |
|---|---|---|
| Initial | Complete framework inspection | 20 findings identified |
| Strategy A (script-only) | regex hardening, portability | F-01, F-05, F-06, F-10, F-17, F-18, F-19 |
| Strategy B (structural) | approval artefacts, hash-chain, self-scripts allowlist | F-02, F-03, F-04, F-07, F-11 (+ opportunistic F-12, F-15, F-16) |
| Strategy C (enforcement) | onboarding validation, injection pre-read, SOUL reconciliation, Python reference impl | F-08, F-09, F-13, F-20 (+ F-14 accepted) |
| Self-re-audit 1 | Review of new code | F-21 discovered and fixed (shlex tokenisation) |
| Self-re-audit 2 | Review of F-21 fix | F-22 discovered and fixed (compressed interpreter flags) |

Live state after the last run:

- `security-audit.sh`: exit 0, 0 findings, 0 warnings
- `verify-policy.sh`: exit 0, 0 findings, 0 warnings
- `python3 -m unittest spa_hooks.tests.test_vectors`: 64 tests, all green
- `AUDIT-LOG.md`: 37+ chained entries, integrity verified
- Drift check: all 8 tracked files match their `POLICY-APPROVED` /
  `SCRIPT-APPROVED` pins

---

## License and credits

**MIT-0.** No warranty. Use freely, modify, redistribute, no
attribution required. The upstream is MIT-0 and we preserve that.

**Upstream.** `halthelobster/proactive-agent` v3.1.0 by Hal Labs — the
proactivity patterns that still carry the agent's weight (WAL,
working buffer, compaction recovery, three-tier memory, reverse
prompting, pattern detection, verify-before-reporting) were their
design and are preserved here.

**Tiered Agent Guard motivation.** OpenClaw's security scan of v3.1.0
flagged the permission-model contradictions. This framework is our fix.
Contradictions are quoted verbatim in
[`references/comparison-with-v3.md`](references/comparison-with-v3.md)
for audit purposes.

**Security-audit methodology.** See
[`SECURITY-AUDIT.md`](SECURITY-AUDIT.md) for the full audit trail.
Two things we would recommend to any downstream maintainer: (1) run
a self-re-audit after every significant new-code phase — F-21 and
F-22 were discovered this way and existed in the framework for under an
hour each; (2) trust mechanical enforcement over prose — every finding
that reached production was prose-only; every finding caught early
was backed by scripts or tests.

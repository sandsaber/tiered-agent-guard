# SECURITY-AUDIT.md — Tiered Agent Guard Security Audit

**Status:** Strategies A–C complete + F-21/F-22/F-23 self-re-audit findings fixed. 23/23 findings closed or explicitly accepted.
**Started:** 2026-04-22
**Last updated:** 2026-05-19 (F-23 denylist-only shell classification fixed; 72 passing tests)
**Auditor:** Claude (Opus 4.7, interactive session)
**Target version:** framework as of 2026-04-22, before any patches
**Target platform:** darwin / macOS (per environment)

*Note: this audit was performed on the project under its previous name
`openclaw-proactive-agent`. All findings, SHAs, and methodology remain valid
for the renamed framework `tiered-agent-guard`. No code changes were made
during the rebrand.*

---

## How to use this document

- **Section 1** — executive summary. Read first.
- **Section 2** — idea of the project, so future-you understands what not to break.
- **Section 3** — findings table (one-line status per finding).
- **Section 4** — findings in detail (F-01…F-23).
- **Section 5** — fix strategies (A / B / C) with acceptance criteria.
- **Section 6** — progress tracker (what's done, what's open).
- **Section 7** — next actions (do this next).
- **Section 8** — continuation notes (how to resume cold).
- **Section 9** — verification commands.

When resuming: read 1, 3, 6, 7, 8 — that's enough context to restart in ~2 minutes.

---

## 1. Executive Summary

Tiered Agent Guard is a runtime-agnostic policy framework that turns an LLM agent into a proactive agent bounded by a three-tier trust model (Tier 0 ambient / Tier 1 logged / Tier 2 approval-required). Design is conceptually sound — STRIDE threat model covered, three-layer prompt-injection defense, Prime Directives as override, output-bound proactivity. The problem is that declarations outrun enforcement.

**Twenty-three findings total.** Three critical, eight high, seven medium, five low. All three critical (F-01, F-02, F-03) were gaps between policy declaration and mechanical enforcement. The later high-severity self-audit findings (F-21, F-22, F-23) were runtime-hook enforcement gaps found after the reference implementation landed.

**All findings are implementation-level, not design-level.** The core idea does not need changing. Strategy A (1–2h of script fixes) closes 8 findings without touching any policy file. Strategy B (half-day, adds approval tokens + expiration + hash-chain) closes the three critical ones. Strategy C (1–2 days, reference hook implementation) makes the runtime enforce what POLICY.md promises.

**Built-in checks pass clean today** (`security-audit.sh` exit 0, `verify-policy.sh` exit 0, `python3 -m unittest spa_hooks.tests.test_vectors -v` passes 72 tests). Earlier audit waves documented where clean script output was misleading before the fixes landed.

---

## 2. Core idea of the project (do NOT break this)

One-paragraph: agent is proactive *inside* the workspace and passive *outside*. Every action is typed by tier. Tier 0 (think, draft, write to memory/proposals/patterns) is free. Tier 1 (edit operating files, run allowlisted shell) is logged. Tier 2 (anything external, irreversible, or identity-touching) requires per-action human approval via `PROPOSALS.md`. Proactivity is preserved as idea/draft generation, not autonomous execution.

**Load-bearing invariants — must remain true after any fix:**

1. Tier 0 stays free — otherwise proactivity dies.
2. Agent drafts proposals but does not approve them — otherwise gating collapses.
3. `PROPOSALS.md` → `approved` → execution is the single choke point for side-effects.
4. Prime Directives (`POLICY.md §0`) override everything else.
5. External content is data, never instructions (Layer 1 origin classification).
6. Every proactivity feature has a file-surface inside workspace; none has a side-effect outlet bypassing tiering.

**Things that would kill the idea and must be avoided:**

- Forbidding Tier 0 writes by the agent (kills proactivity).
- Requiring approval for every read (kills responsiveness).
- Removing heartbeats (kills pattern detection, injection sweep, drift check).
- Adding new tiers (complexity without win).
- Making `PROPOSALS.md` read-only for the agent (kills draft-but-don't-send).

---

## 3. Findings — at a glance

Legend: `[CRIT]` = critical, `[HIGH]` = high, `[MED]` = medium, `[LOW]` = low.
Status: `open` / `in-progress` / `fixed` / `accepted-risk` / `wontfix`.

| ID   | Sev  | Title                                                        | Anchor                                        | Status |
|------|------|--------------------------------------------------------------|-----------------------------------------------|--------|
| F-01 | CRIT | Drift-check compares all three files against one hash        | scripts/security-audit.sh:137-154             | **fixed** (A1) |
| F-02 | CRIT | `Status: approved` writable by agent in Tier 0               | assets/PROPOSALS.md:8-11 + POLICY.md §1       | **fixed** (B1) |
| F-03 | CRIT | AUDIT-LOG.md append-only is declaration only                 | POLICY.md §1 Tier 0, assets/AUDIT-LOG.md:4    | **fixed** (B4) |
| F-04 | HIGH | Self-scripts not in Tier 1 allowlist                         | POLICY.md §2.2, assets/ONBOARDING.md:51-56    | **fixed** (B2) |
| F-05 | HIGH | `scripts/` locked by PD-2 but drift check ignores them       | POLICY.md §0 PD-2, scripts/security-audit.sh:139 | **fixed** (A1) |
| F-06 | HIGH | Secret-grep misses Anthropic / JWT / Google / Stripe / Slack | scripts/security-audit.sh:88-99               | **fixed** (A2) |
| F-07 | HIGH | Approved proposals executable repeatedly (replay)            | references/trust-tiers.md:90-102              | **fixed** (B1) |
| F-08 | HIGH | ONBOARDING Step 1 accepts unvalidated free-form user input   | assets/ONBOARDING.md:10-22                    | **fixed** (C3) |
| F-09 | MED  | Injection sweep is daily — 24h persistence window            | assets/HEARTBEAT.md §6                        | **fixed** (C2) |
| F-10 | MED  | Perm check misses macOS ACL (`ls -le`)                       | scripts/security-audit.sh:72-75               | **fixed** (A3) |
| F-11 | MED  | Proposal auto-expire has no executor                         | assets/PROPOSALS.md:54 + assets/HEARTBEAT.md  | **fixed** (B3) |
| F-12 | MED  | `env | grep -vE` filter is case-sensitive                    | POLICY.md §2.2                                | **fixed** (bonus) |
| F-13 | MED  | SOUL.md vs POLICY.md self-mod inconsistency                  | assets/SOUL.md:50, POLICY.md §7               | **fixed** (C4) |
| F-14 | MED  | forbidden-string list trivially paraphrased                  | scripts/verify-policy.sh:96-102               | **accepted** (annotated as smoke-test) |
| F-15 | MED  | `find -type f -readable` not supported on macOS (BSD find)   | POLICY.md §2.2                                | **fixed** (bonus) |
| F-16 | LOW  | `\brm\b` does not block rmdir/unlink/shred/trash/-delete     | references/trust-tiers.md:87                  | **fixed** (bonus) |
| F-17 | LOW  | `grep -v` pipe-exclude weaker than `--exclude=`              | scripts/security-audit.sh:104                 | **fixed** (A4) |
| F-18 | LOW  | Credential-location list incomplete                          | scripts/security-audit.sh:114-124             | **fixed** (A2) |
| F-19 | LOW  | `set -u` without `set -e`                                    | both scripts                                  | **fixed** (A5) |
| F-20 | LOW  | Example entries in surprise-queue.md have placeholder dates  | assets/memory/surprise-queue.md:40-58         | **fixed** (wrapped in HTML comment) |
| F-21 | HIGH | Shell quote/escape obfuscation bypasses BLOCKED_COMMAND_PATTERNS | spa_hooks/policy.py + references/trust-tiers.md | **fixed** (shlex tokenize) |
| F-22 | HIGH | Combined interpreter flags (bash -lc, perl -pe) bypass F-21 fix | spa_hooks/policy.py interpreter patterns | **fixed** (`[^|;&\n]*?\s-[a-zA-Z]*c\b`) |
| F-23 | HIGH | Shell hook used denylist fallback instead of POLICY.md allowlist | spa_hooks/policy.py classify_tier | **fixed** (allowlist + path guard) |

---

## 4. Findings in detail

### F-01 — Drift-check compares all three files against one hash  [CRIT]

**File:** `scripts/security-audit.sh:137-154`

```bash
for f in "POLICY.md" "assets/SOUL.md" "SKILL.md"; do
  last_approved=$(grep -A1 "POLICY-APPROVED" assets/AUDIT-LOG.md \
                  | grep -E "New-sha256:" | tail -1 | awk '{print $2}')
  # $last_approved does not depend on $f
  actual=$(shasum -a 256 "$f" ...)
  if [ "$last_approved" = "$actual" ]; ...
```

`AUDIT-LOG.md:68-75` prescribes `POLICY-APPROVED` entries with a `File:` field, but the script ignores it. After the first approval of any of the three, all other comparisons use that same hash.

**Impact:** PD-2 tamper-detection is illusory once any approval is recorded. A tampered `SOUL.md` would pass as "matches last approved" because the last approval was for `POLICY.md`.

**Status today:** not activated yet — `AUDIT-LOG.md` has no `POLICY-APPROVED` entries, so the branch prints "no prior approval recorded" for all three. First approval will activate the bug.

**Fix:** see Strategy A / fix-A1 in §5.

---

### F-02 — `Status: approved` in PROPOSALS.md writable in Tier 0  [CRIT]

**Files:** `assets/PROPOSALS.md:8-11`, `POLICY.md §1 Tier 0`

POLICY §1 Tier 0 allows free writing to `PROPOSALS.md`. The approval state is stored inline as `Status: approved`. Nothing prevents the agent from flipping its own proposal's status. Runtime hook pseudocode (`references/trust-tiers.md:90-102`) finds "any approved proposal matching command" — match succeeds, Tier 2 command executes.

**Attack vector:** prompt injection persists into `memory/*` (also Tier 0 write), next session the agent reads it as "informational memory," drafts a proposal, writes `Status: approved` — executes Tier 2 command. Complete bypass.

**Impact:** the entire Tier 2 model rests on a status string the agent can write.

**Fix:** see Strategy B / fix-B1 in §5 — approval lives outside PROPOSALS.md, in `approvals/*.approved` files that the agent cannot write.

---

### F-03 — AUDIT-LOG.md append-only is declaration, not enforcement  [CRIT]

**Files:** `POLICY.md §1 Tier 0`, `assets/AUDIT-LOG.md:4`

POLICY §1 lists `AUDIT-LOG.md` as Tier 0 write. `AUDIT-LOG.md:4` says "no rewriting, no deletion." Agent physically can rewrite. `verify-policy.sh:128-139` checks existence, not append-only-ness.

**Impact:** Repudiation mitigation (STRIDE) doesn't hold. Compromised agent can scrub its trail.

**Fix:** hash-chain each entry with `Prev-entry-sha256:` and verify the chain in heartbeat §7. Agent still writes Tier 0 but tampering is detectable. See fix-B4.

---

### F-04 — Self-scripts not in Tier 1 allowlist  [HIGH]

**Files:** `POLICY.md §2.2`, `assets/ONBOARDING.md:51-56`

`ONBOARDING.md` Step 3 requires `./scripts/security-audit.sh` and `./scripts/verify-policy.sh`. §2.2 Tier 1 allowlist does not name them. Per §2.3 "everything else is Tier 2." Onboarding itself violates the policy it runs.

**Fix:** see fix-B2 — add a "Project-local scripts" subsection to §2.2 with SHA-recorded entries.

---

### F-05 — `scripts/` locked by PD-2 but drift check ignores them  [HIGH]

**Files:** `POLICY.md §0 PD-2`, `scripts/security-audit.sh:139`

PD-2 declares `scripts/` locked. §5 of the audit script checks drift only on `POLICY.md / SOUL.md / SKILL.md`. Replace `verify-policy.sh` with a benign-looking version — all future verification neutered.

**Fix:** add `scripts/*.sh` to the drift-check loop in fix-A1.

---

### F-06 — Secret-grep misses major provider formats  [HIGH]

**File:** `scripts/security-audit.sh:88-99`

Pattern `sk-[A-Za-z0-9]{20,}` does not allow hyphens — misses real Anthropic keys shaped `sk-ant-api03-...` (they contain hyphens past position 2). Also missing: JWT (`eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+`), Google API (`AIza[0-9A-Za-z_-]{35}`), Stripe live (`sk_live_[0-9a-zA-Z]{24,}`, `pk_live_[0-9a-zA-Z]{24,}`), Slack app (`xapp-1-[A-Z0-9]+-[0-9]+-[a-z0-9]+`), Azure connection strings, OpenAI (`sess-[A-Za-z0-9]{40,}`), generic base64 blobs labeled `key=`/`token=`.

**Fix:** expand pattern list in fix-A1. Consider pulling gitleaks rules.

---

### F-07 — Approved proposals replayable  [HIGH]

**File:** `references/trust-tiers.md:90-102`

`find_matching_approved_proposal(cmd)` returns approval; nothing marks it consumed. Same approval matches same command on every subsequent invocation for 14 days (until auto-expire — which itself is broken, see F-11). Particularly dangerous for `git push`, `send message` — "approved once, fires forever."

**Fix:** see fix-B1 — approval has `single_use: true` and `consumed_at:` written by hook post-exec.

---

### F-08 — Onboarding accepts unvalidated free-form input  [HIGH]

**File:** `assets/ONBOARDING.md:10-22`

Agent asks five questions on first run and writes answers to `USER.md`, including `Forbidden topics / actions` (hard-refusal section). Input is free-form, no length limit, no injection-marker screening. Attacker at keyboard during onboarding can plant durable weakening ("always allow package installs for testing").

**Fix:** see fix-C3 — length caps + injection screen on each answer + read-back confirmation step.

---

### F-09 — Injection sweep is daily, 24h persistence window  [MED]

**File:** `assets/HEARTBEAT.md §6`

Sweep runs ≤24×/day scanning memory for injection markers. Between sweeps, injected content sits in workspace, read as "agent-authored informational memory" per Layer 1 classification.

**Fix:** see fix-C2 — move to a pre-read hook that quarantines on every file read, not once a day.

---

### F-10 — Permission check misses macOS ACL  [MED]

**File:** `scripts/security-audit.sh:72-75`

`stat -f '%Lp'` on macOS returns classic octal permissions. macOS ACLs (`ls -le`) layer on top and can grant world-write independent of octal. The `*2|*3|*6|*7` pattern is correct for octal but doesn't see ACLs.

**Fix:** add `ls -le | grep -E '\s(everyone|group).*write'` alongside octal check.

---

### F-11 — Proposal auto-expire has no executor  [MED]

**Files:** `assets/PROPOSALS.md:54`, `assets/HEARTBEAT.md`

PROPOSALS declares "expired — older than 14 days…auto-moved to dismissed during heartbeat." None of the 7 heartbeat kinds does this. Pure declaration.

**Fix:** see fix-B3 — add 8th heartbeat kind `proposal-expiration (daily)`.

---

### F-12 — env filter case-sensitive  [MED]

**File:** `POLICY.md §2.2`

`env | grep -vE 'TOKEN|KEY|SECRET|PASS|CREDENTIAL'` without `-i` passes `api_token`, `access_token`, `sessionKey`, `MySecret`, `bearer_xyz`. Filter is in Tier 1 allowlist — agent will run it as-is.

**Fix:** add `-i` and expand terms: `token|key|secret|pass|credential|auth|bearer|session|cookie|private|cert|oauth|refresh`.

---

### F-13 — SOUL.md vs POLICY.md self-mod inconsistency  [MED]

**Files:** `assets/SOUL.md:50`, `POLICY.md §7`

SOUL absolute: "I will not: Edit POLICY.md, SOUL.md, SKILL.md."
POLICY conditional: "may not…without Tier 2 approval."

For a future valid Type:identity proposal — agent's SOUL says no, POLICY says yes. No resolution order given.

**Fix:** see fix-C4 — SOUL rewords to conditional, matching POLICY. Keeps absolute feeling by referencing approval channel.

---

### F-14 — forbidden-string list trivially paraphrased  [MED]

**File:** `scripts/verify-policy.sh:96-102`

Five exact strings: "Don't ask permission", "Just do it", etc. Paraphrase (`act without asking`, `skip the queue`, `auto-approve`, `no review needed`, non-English) passes through. Creates false sense of coverage.

**Fix:** expand list + regex family + treat as a weak signal, not a gate. Or remove as security check (keep as smoke test only).

---

### F-15 — `find -type f -readable` not supported on macOS  [MED]

**File:** `POLICY.md §2.2`

BSD find has no `-readable`. Env is `darwin`. Agent running exact command gets error, may conclude "no access" when real issue is flag.

**Fix:** replace with `find -type f \! \( -perm -u=r -o -perm -g=r -o -perm -o=r \)` or similar POSIX-portable.

---

### F-16 — `\brm\b` does not block related deletion verbs  [LOW]

**File:** `references/trust-tiers.md:87`

Blocks `rm` but not `rmdir`, `unlink`, `shred`, `trash`, `find ... -delete`, `gio trash`.

**Fix:** expand pattern. `\b(rm|rmdir|unlink|shred|trash)\b|-delete\b`.

---

### F-17 — `grep -v` pipe-exclude weaker than `--exclude=`  [LOW]

**File:** `scripts/security-audit.sh:104`

`... | grep -v 'references/prompt-injection.md'` drops any line *containing that substring anywhere*, not only matches from that file. A legit reference to the path in another file's line would disappear from the report.

**Fix:** `grep --exclude=prompt-injection.md --exclude=security-audit.sh`.

---

### F-18 — Credential-location list incomplete  [LOW]

**File:** `scripts/security-audit.sh:114-124`

Missing: `.netrc`, `.docker/config.json`, `.gnupg/`, `.git-credentials`, `*.pem`, `*.p12`, `*.keystore`, `serviceAccountKey.json`, `secrets.yaml`, `secrets.yml`, `*.ppk`.

**Fix:** extend array in fix-A1.

---

### F-19 — `set -u` without `set -e`  [LOW]

**Files:** both scripts

Promiscuous errors swallowed, script reports "clean" on partial failure.

**Fix:** `set -euo pipefail` + explicit `|| true` where non-zero expected.

---

### F-20 — surprise-queue.md example entries have YYYY-MM-DD placeholders  [LOW]

**File:** `assets/memory/surprise-queue.md:40-58`

`**Added:** YYYY-MM-DD` literal could be parsed as real entry if any automation scans this file. Cosmetic.

**Fix:** wrap examples in a visible `<!-- EXAMPLE, DELETE BEFORE USE -->` block, or move to a separate `surprise-queue.example.md`.

---

### F-21 — Shell quote/escape obfuscation bypasses BLOCKED_COMMAND_PATTERNS  [HIGH]

**Files:** `spa_hooks/policy.py:BLOCKED_COMMAND_PATTERNS`, `references/trust-tiers.md §Pre-tool-use hook`

**Discovery:** self-re-audit after Strategy C landed, 2026-04-22.

**Problem:** regex `\brm\b` (and every sibling pattern) operates on the raw
command string. Bash evaluates these forms all as `rm`:

```
r''m file.txt       # empty-string concat — BYPASS on \brm\b
r\m file.txt        # backslash-escapes m — BYPASS
'r''m' file.txt     # nested quoting — BYPASS
p\ip install x      # obfuscated `pip install` — BYPASS on \bpip\b\s+install
```

An agent allowed to write shell tool arguments can therefore run any
"blocked" command without hitting Tier 2. Verified empirically:

```python
>>> import re; re.search(r"\brm\b", "r''m file.txt")   # → None (bypass)
```

This is the primary enforcement gate for shell side-effects — a real HIGH.

**Fix:** tokenize with `shlex.split(posix=True)` (splitting first on
`|`, `;`, `&` so chained commands tokenize correctly), then check
patterns against **both** the raw cmd **and** the `' '.join(tokens)`
reassembly. Obfuscated forms collapse to canonical tokens under shlex,
so the pattern matches on the reassembly.

Also extended `BLOCKED_COMMAND_PATTERNS` with explicit code-execution
surface: `eval`, `exec`, `source`, `{bash,sh,zsh,dash,ksh} -c`,
`{python,python2,python3} -c`, `perl -{e,E}`, `ruby -e`, `node -e`.

**Verification:** 20 new regression tests in
`spa_hooks/tests/test_vectors.py::ObfuscationBypass` cover the obfuscation
forms above + sanity tests that legitimate `ls`, `grep`, `git status`
still pass. Total test count: **56 passing**.

**Learning:** run a self-re-audit after every significant new-code phase.
This finding existed for ~45 minutes between the C1 landing and the
re-audit; would have shipped silently otherwise.

---

### F-22 — Combined interpreter flags bypass F-21 fix  [HIGH]

**Files:** `spa_hooks/policy.py:BLOCKED_COMMAND_PATTERNS`, `spa_hooks/tests/test_vectors.py::ObfuscationBypass`

**Discovery:** self-re-audit after the F-21 patch, 2026-04-22.

**Problem:** the first F-21 patch covered obvious interpreter code-execution
forms such as `bash -c` and `python3 -c`, but compressed or combined flags
could still pass if the regex expected the code flag too literally. Examples:

```bash
bash -lc 'cmd'
sh -xvc 'cmd'
bash --rcfile=/dev/null -lc 'cmd'
perl -pe 'script_that_could_do_anything'
```

**Impact:** command strings that launch an interpreter with inline code are
Tier 2 by policy. Combined flags are normal shell syntax, so a hook that misses
them creates a practical bypass rather than an academic parser edge case.

**Fix:** interpreter regexes now allow intermediate options and compressed flag
sets, for example `[^|;&\n]*?\s-[a-zA-Z]*c\b` for shell `-c` forms and
matching variants for Perl/Ruby/Node/Awk code flags.

**Verification:** the `ObfuscationBypass` suite includes compressed shell and
Perl flag vectors and keeps known-legitimate `ls`, `grep`, and `git status`
positive cases passing.

---

### F-23 — Shell hook used denylist fallback instead of POLICY.md allowlist  [HIGH]

**Files:** `spa_hooks/policy.py:classify_tier`, `references/trust-tiers.md §Pre-tool-use hook`

**Discovery:** security audit on 2026-05-19.

**Problem:** `POLICY.md §2.2` defines Tier 1 shell execution as an allowlist:
only named command forms are allowed after logging; everything else is Tier 2.
The Python reference hook enforced the Tier 2 denylist first, then returned
Tier 1 for any shell command that did not match a blocked pattern. These probes
were wrongly allowed or classified too low:

```text
cat /etc/passwd                 -> Tier 1 logged
git commit -m x                 -> Tier 1 logged
chmod 777 assets/AUDIT-LOG.md   -> Tier 1 logged
tee assets/PROPOSALS.md         -> Tier 1 logged
```

**Impact:** an integration using `spa_hooks.approve_or_deny(...)` could permit
non-allowlisted local commands without a Tier 2 approval. This breaks the
runtime contract even when the obvious network/delete/install patterns are
blocked.

**Fix:** `classify_tier` now defaults shell commands to Tier 2 unless every
shell segment matches a Tier 1 command form from `POLICY.md §2.2`. The hook
also rejects static shell paths outside the workspace and credential-looking
paths such as `.ssh`, `.env`, `.aws`, `.git-credentials`, and common private
key names. Known-good audit/test forms (`./scripts/security-audit.sh`,
`./scripts/verify-policy.sh`, `python3 -m unittest ...`) remain Tier 1.

**Verification:** added 8 regression tests covering non-allowlisted commands,
workspace path escapes, credential-looking shell paths, and positive allowlist
cases. Current total: **72 tests passing**. The original manual probes now
return Tier 2 or a direct denial before execution.

---

## 5. Fix strategies

Three strategies, composable. Recommended order: A → B → C. Effort estimates assume one focused session.

### Strategy A — Script-only patches [est. 1–2h]

**Scope:** scripts only. No changes to any `.md` file in `assets/` or `POLICY.md` / `SOUL.md` / `SKILL.md`. Lowest risk.

| Fix ID | Closes   | Change                                                                 |
|--------|----------|------------------------------------------------------------------------|
| A1     | F-01, F-05 | `security-audit.sh §5`: filter POLICY-APPROVED by `File:` line; loop over `POLICY.md / SOUL.md / SKILL.md / scripts/*.sh` |
| A2     | F-06, F-18 | `security-audit.sh §3, §4`: expand secret regexes + credential path list |
| A3     | F-10     | `security-audit.sh §2`: add macOS ACL check                           |
| A4     | F-17     | `security-audit.sh §3`: switch to `--exclude=`                        |
| A5     | F-19     | both scripts: `set -euo pipefail`                                     |
| A6     | F-20     | `assets/memory/surprise-queue.md`: wrap examples in HTML comment      |

**Acceptance criteria for Strategy A:**
- `./scripts/security-audit.sh` exits 0 on a clean framework state.
- Manually tamper `assets/SOUL.md` (add newline) → `security-audit.sh` reports WARN/FAIL on SOUL.md specifically, not just one line.
- Plant `sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` in a throwaway file → detected.
- Run both scripts with a deliberate syntax error upstream → exit non-zero.

**Does NOT close:** F-02 (approval bypass), F-07 (replay), F-03 (audit tampering), F-04 (allowlist), F-08, F-11, F-13. Strategy B needed.

---

### Strategy B — Structural hardening [est. 0.5–1 day]

**Scope:** targeted edits to `POLICY.md` and `HEARTBEAT.md`, new `assets/approvals/` directory, new `scripts/approve-proposal.sh`. Preserves all load-bearing invariants from §2.

#### fix-B1 — Approval tokens outside PROPOSALS.md [closes F-02, F-07]

**Change:**
1. New directory `assets/approvals/` — Tier 2 write only. Agent has zero write privilege here. Runtime hook denies agent writes to this path.
2. New CLI `scripts/approve-proposal.sh <proposal-id>` — requires TTY, cannot be invoked by the agent. Produces `assets/approvals/<proposal-id>.approved`:
   ```yaml
   proposal_id: <sha256 of proposal section text at approval time>
   proposal_sha256: <same>
   approved_at: 2026-04-22T12:00:00Z
   approved_by: <user@host, from `whoami` + `hostname`>
   single_use: true
   consumed_at: null
   ```
3. Runtime hook `find_matching_approved_proposal(cmd)`:
   a. Reads `assets/approvals/*.approved`.
   b. Recomputes sha256 of the proposal section in `PROPOSALS.md` — rejects on mismatch (TOCTOU).
   c. Rejects if `single_use: true && consumed_at != null`.
   d. After successful exec, writes `consumed_at: <now>` via same hook (not agent).
4. Add `POLICY.md §11 Approval Artifacts` referencing this mechanism. (This is a POLICY edit — file a `Type: identity` proposal first, since POLICY is locked per PD-2.)

**Acceptance:**
- Agent attempting to write `assets/approvals/foo.approved` is denied by hook.
- Mutating the proposal text after approval makes the approval stop matching.
- Second exec of a single-use approval is denied.

#### fix-B2 — Allowlist self-scripts with recorded SHA [closes F-04]

**Change:** add to `POLICY.md §2.2`:

```
# Project-local scripts (must be inside ./scripts/ AND have a SCRIPT-APPROVED entry in AUDIT-LOG.md)
./scripts/security-audit.sh    [SHA-pinned]
./scripts/verify-policy.sh     [SHA-pinned]
```

Also add a new `AUDIT-LOG.md` entry type `SCRIPT-APPROVED` mirroring `POLICY-APPROVED`. Extend `security-audit.sh §5` to verify scripts against their approved SHA.

**Acceptance:** onboarding Step 3 no longer violates its own policy.

#### fix-B3 — Proposal expiration heartbeat [closes F-11]

**Change:** add to `assets/HEARTBEAT.md`:

```markdown
### 8. Proposal-expiration (daily)

Scan `PROPOSALS.md` for entries with `Status: pending-review` older than 14 days.
Move them to `Status: expired` with reason `auto-expired (>14d pending-review)`.
Also scan `assets/approvals/*.approved` where `approved_at` is older than 14 days
and `consumed_at` is null — move those to `assets/approvals/expired/`.
```

**Acceptance:** date a test proposal 15 days ago → next daily heartbeat flips it to `expired`.

#### fix-B4 — Hash-chain AUDIT-LOG.md [closes F-03]

**Change:**
1. Every entry ends with `Prev-entry-sha256: <sha of log content up to previous entry's end>`.
2. New heartbeat kind in `HEARTBEAT.md §7` (extend existing policy-drift check) to verify chain integrity; any mismatch triggers `POLICY.md §10` emergency halt.
3. Tooling: `scripts/audit-log-append.sh <entry-body>` — does the sha computation correctly and atomically. Agent calls this instead of raw append.

**Acceptance:**
- Delete an entry from the middle of `AUDIT-LOG.md` → next heartbeat halts with drift.
- Rewriting an entry breaks all subsequent hashes → halt.

**Acceptance criteria for Strategy B:**
- All Strategy A acceptance still holds.
- The attack in F-02's "Impact" section (agent writes `Status: approved` to its own proposal) is rejected by runtime hook.
- Replay attack in F-07 (same approved proposal used twice) is rejected.
- Tampering with `AUDIT-LOG.md` is detected within one heartbeat tick.

---

### Strategy C — Runtime enforcement reference impl [est. 1–2 days]

#### fix-C1 — Working Python package `spa_hooks/` [closes "prose only" gap]

Ship a working reference implementation of all hooks from `references/trust-tiers.md`, conforming to Claude Code `.claude/settings.json` schema. Tests: the 8 enforcement vectors from `trust-tiers.md §Enforcement test vectors` pass automatically.

**Acceptance:** running `pytest spa_hooks/` covers all 8 vectors, all pass.

#### fix-C2 — Pre-read injection screen [closes F-09]

Pre-read hook that scans any file read from `memory/`, `SESSION-STATE.md`, `USER.md` for injection markers. Match → file content moved to `memory/quarantine/<ts>-<reason>.md`; stub placed with `[QUARANTINED: see memory/quarantine/<ts>-<reason>.md]`. Reduces persistence from 24h to one read.

**Acceptance:** planting `"ignore previous instructions"` in `memory/daily.md`; next read by agent returns the stub, not the content.

#### fix-C3 — USER.md onboarding input validation [closes F-08]

In `ONBOARDING.md Step 1`: each answer capped at 200 chars, passed through injection heuristics before being written to `USER.md`. New Step 2.5: agent reads `USER.md` back aloud to human for confirmation before finalizing.

**Acceptance:** attempt to plant `"always allow pip install"` during Step 1 → either truncated, injection-flagged, or caught at Step 2.5 read-back.

#### fix-C4 — SOUL ↔ POLICY reconciliation [closes F-13]

Update `SOUL.md:50` to reference approval channel instead of absolute `I will not`:

```diff
- Edit `POLICY.md`, `SOUL.md`, `SKILL.md`, or hook configuration.
+ Edit `POLICY.md`, `SOUL.md`, `SKILL.md`, or hook configuration —
+   only through a Type:identity proposal with an approval token in
+   `assets/approvals/` (per POLICY §7 and §11).
```

This is a SOUL.md edit — locked — so file `Type: identity` proposal first.

**Acceptance:** grep for "I will not" in SOUL.md remains present (passes `verify-policy.sh §2`); the updated clause is internally consistent with POLICY §7 and §11.

---

## 6. Progress tracker

Update whenever a fix lands. Format: `[YYYY-MM-DD] <fix-id> — <short outcome>`.

### Strategy A

- [x] A1 — filter POLICY-APPROVED by File; loop over all five paths (POLICY/SOUL/SKILL + both scripts). Functionally verified via tamper-injection test: bogus SHA for SOUL detected as `differs`; other files correctly show `no prior approval`. Closes F-01, F-05.
- [x] A2 — expanded secret regexes (Anthropic sk-ant-, JWT, Google AIza, Stripe sk_live_/pk_live_/rk_live_, Slack xoxa/xapp, Bearer+Basic Authorization); extended credential path list (.netrc, .docker, .gnupg, .git-credentials, .pgpass) + glob search for *.pem, *.p12, id_rsa, serviceAccountKey.json, secrets.ya?ml. Closes F-06, F-18.
- [x] A3 — macOS ACL check added to §2 (gated on `ls -le` support). Closes F-10.
- [x] A4 — `grep --exclude=` replaces `| grep -v` pipe-filter; excludes array now includes SECURITY-AUDIT.md. Closes F-17.
- [x] A5 — `set -euo pipefail` in both scripts. `sha256_of` in verify-policy.sh hardened to always return 0 under strict mode. `[ ... ] && note "..."` pattern in §3 replaced with `if ... fi` to avoid `set -e` triggering on false test. Closes F-19.
- [ ] A6 — wrap surprise-queue examples in HTML comment. Deferred (out of scope this round).

### Strategy B

- [x] B1 — approval tokens in `assets/approvals/`
  - [x] B1.a — wrote `scripts/approve-proposal.sh` (TTY-gated, interactive, sha256 match, writes `<sha>.approved` with `single_use: true`, appends TIER-2 approval-granted entry via chain helper)
  - [x] B1.b — added `POLICY.md §11 Approval Artifacts` with subsections: canonical location, record format, execution contract (TOCTOU guard + single_use + 14-day expiry), expiration, chain integrity, SCRIPT-APPROVED entry type
  - [x] B1.c — rewrote `references/trust-tiers.md` pseudocode with `find_matching_approval`, `consume_approval`, `post_tool_use` consumption pattern
- [x] B2 — allowlist self-scripts + SCRIPT-APPROVED log type. POLICY §2.2 adds "Project-local scripts" block with the four scripts listed. `security-audit.sh §5` accepts both POLICY-APPROVED and SCRIPT-APPROVED entries. `verify-policy.sh §1` now checks for `Approval Artifacts` section presence.
- [x] B3 — `HEARTBEAT.md §8 proposal-expiration` added; §7 extended to include chain-integrity check alongside policy-drift.
- [x] B4 — `scripts/audit-log-append.sh` written; both `security-audit.sh` and `verify-policy.sh` now append via helper (falls back to legacy path if helper missing). `verify-policy.sh §5` replaced shallow "append-only sanity" with real hash-chain walker. Tamper detection verified functionally: changing `findings=0`→`findings=9` in an earlier chained entry produces `[FAIL] chain mismatch` in the subsequent entry's Prev-entry-sha256.

### Strategy C

- [x] C1 — `spa_hooks/` reference implementation landed. 36 unit tests pass (`python3 -m unittest spa_hooks.tests.test_vectors -v`). Covers: classify_tier × 7, enforcement vectors V1–V3, V5, V6, V7, V8 from `trust-tiers.md` §Enforcement, deletion family × 6 (F-16 regression set), network family × 7, workspace guards × 3, approval hygiene × 4 (expiry, consumed single_use, TOCTOU body mutation, subject mismatch). `ApprovalRecord.consume()` writes `consumed_at` atomically.
- [x] C2 — `scripts/injection-scan.sh` added (standalone + `--sweep` + `--quarantine` modes). `HEARTBEAT.md §6` rewritten: pre-read hook is now the preferred mode, daily sweep marked as fallback. F-09 persistence window closes from 24h (daily heartbeat) to one read per file.
- [x] C3 — `ONBOARDING.md` Step 1.5 (injection scan + 200-char cap + forbid-list guard) + Step 2.5 (readback before saving `USER.md`) added. Raw answers stage into `SESSION-STATE.md` until validated.
- [x] C4 — `SOUL.md` "I will not: Edit POLICY/SOUL/SKILL" rewritten as conditional referencing POLICY §7 and §11. SOUL and POLICY are now internally consistent; approval channel is a deliberate, separately-scoped exception rather than a contradiction.
- [x] F-14 annotation — `verify-policy.sh §3` header and comment now explicitly label the forbidden-string check as a smoke test only, not a security gate. Points at POLICY §§0–2, §7, §11 as the real gates.
- [x] F-20 — surprise-queue example entries wrapped in an HTML comment so any date-parser or pattern-detector treats them as invisible.

### Log

- [2026-04-22] Initial audit completed; 20 findings documented; no fixes applied yet.
- [2026-04-22] Strategy A landed (A1–A5). Closed F-01, F-05, F-06, F-10, F-17, F-18, F-19. Also opportunistically fixed an unnumbered issue: `verify-policy.sh` `doc_excludes` now excludes `SECURITY-AUDIT.md` (this file legitimately quotes forbidden strings). Both `security-audit.sh` and `verify-policy.sh` exit 0 on the clean framework state. F-01 verified with tamper-injection harness (see §9 below).
  - Remaining open: F-02, F-03, F-04, F-07, F-08, F-09, F-11, F-12, F-13, F-14, F-15, F-16, F-20.
- [2026-04-22] Strategy B landed (B1–B4) + opportunistic F-12, F-15, F-16. Closed F-02, F-03, F-04, F-07, F-11 (Strategy B) and F-12, F-15, F-16 (opportunistic). New artifacts: `scripts/audit-log-append.sh`, `scripts/approve-proposal.sh`, `assets/approvals/` (with README). New POLICY sections: §11 Approval Artifacts (6 subsections), §2.2 extended with Project-local scripts allowlist + broader deletion note. New `HEARTBEAT.md §8` (proposal-expiration) + §7 extended. `references/trust-tiers.md` pseudocode rewritten for approvals directory + single_use + TOCTOU. `AUDIT-LOG.md` now chained: 17 entries OK. All 7 tracked files have `POLICY-APPROVED` or `SCRIPT-APPROVED` pins; `security-audit.sh §5` shows all as "matches last approved." Tamper detection verified (chain mismatch on forged edit in an earlier chained entry).
  - Remaining open: F-08, F-09, F-13 (Strategy C), F-14 (weak-signal, accept), F-20 (cosmetic).
  - Summary: **15 of 20 findings closed**; all 3 critical closed; 4 of 5 high closed (F-08 remains).
- [2026-04-22] Strategy C landed (C1–C4) + F-14 annotation + F-20 wrap. Closed F-08, F-09, F-13, F-20; F-14 accepted with annotation. New artifacts: `scripts/injection-scan.sh` (high/medium-confidence markers, sweep + quarantine modes), `spa_hooks/` Python reference implementation (policy.py, approvals.py, tests/test_vectors.py with 36 passing unit tests covering all 8 enforcement vectors + hygiene). `ONBOARDING.md` gained Step 1.5 (validate answers: injection scan + 200-char cap + forbid-list guard) and Step 2.5 (readback before save). `HEARTBEAT.md §6` rewritten (pre-read hook preferred, daily sweep = fallback). `SOUL.md §Boundaries` reworded from absolute to conditional, pointing at POLICY §7 + §11 approval channel. `verify-policy.sh §3` header annotated as smoke-test only. `surprise-queue.md` example block wrapped in HTML comment. After re-approval of changed files, `security-audit.sh` tracks 8 files all `matches last approved`; `verify-policy.sh §5` reports chain verified across all entries. 36 Python tests pass.
  - Summary: **20 of 20 findings addressed** — 19 fixed, 1 (F-14) explicitly accepted with a smoke-test annotation. All 3 critical and all 5 high closed.
- [2026-05-19] Security audit found F-23: `spa_hooks` shell classification was denylist-first and allowed unknown local commands as Tier 1. Fixed with explicit POLICY.md §2.2 allowlist enforcement plus shell path/credential guards. Added 8 regression tests; total suite is now 72 tests. `security-audit.sh` and `verify-policy.sh` both exit 0 on the final state.
  - Summary: **23 of 23 findings addressed** — 22 fixed, 1 (F-14) explicitly accepted. All 3 critical and all 8 high closed.

---

## 7. Next actions (do this next)

Current state: no open findings from this audit series. Before release or a
public claim, rerun the verification bundle from §9 and make sure the output
matches the current code, not this document's historical notes.

**Release gate:**
1. `./scripts/security-audit.sh`
2. `./scripts/verify-policy.sh`
3. `python3 -m unittest spa_hooks.tests.test_vectors -v`
4. Manual hook probe for at least one unknown command, one outside-workspace
   shell path, one approved Tier 1 command, and one Tier 2 command with no
   approval artefact.

**Policy-drift rule:** if any locked file changes (`POLICY.md`, `SKILL.md`, any
`AGENTS.md`, `assets/SOUL.md`, or `scripts/*.sh`), record the new approved SHA
before expecting audit scripts to pass. The 2026-05-19 F-23 fix intentionally
changed only `spa_hooks/` and documentation, so no locked-file reapproval was
required.

**Stop rules:**
- If a fix requires disabling a load-bearing invariant from §2, stop and reopen
  the design discussion.
- If `security-audit.sh`, `verify-policy.sh`, or the unit suite exits non-zero
  after a fix, do not accept the fix until the regression is explained.

## 8. Continuation notes (how to resume cold)

If starting a new session:

1. **Read** this file top-to-bottom. Takes ~5 minutes.
2. **Run** `./scripts/security-audit.sh && ./scripts/verify-policy.sh` — both should exit 0 today. If not, investigate before doing anything else.
3. **Inspect** `assets/AUDIT-LOG.md` tail — see what happened in previous sessions.
4. **Check** §6 for which fixes are marked done. Match against actual repo state (don't trust the checkboxes blindly — verify). Specifically:
   - A1 done → `security-audit.sh:137-154` should have `File:` filtering.
   - A2 done → grep list in `security-audit.sh:88-99` is ≥15 patterns.
   - B1 done → `assets/approvals/` exists, `scripts/approve-proposal.sh` exists, `POLICY.md §11` exists.
   - B4 done → latest `AUDIT-LOG.md` entry has `Prev-entry-sha256:` line.
5. **Pick** next unchecked item from §7.

**Context that may not be obvious:**
- Project is NOT a git repository. `security-review` skill that expects git will fail — use manual audit methods.
- `security-audit.sh` and `verify-policy.sh` both write a TIER-1 entry to `AUDIT-LOG.md` on each run. So running them during development noises the log — consider commenting out §7 append during iteration, revert before commit.
- `POLICY.md` claims `scripts/` are PD-2 locked, but there's no runtime enforcement today. Treat them as locked by convention; file a `Type: identity` proposal before significant edits even if no hook stops you.
- User's primary language is Russian (observed in this session). Audit artifact is in English per convention, but conversation responses follow user language.

**Files not read in this audit (low priority, template-only):**
- `assets/USER.md` — pure template, unpopulated.
- `assets/memory/working-buffer.md` — empty sentinel.
- `assets/memory/open-questions.md` — template only.
- `assets/memory/near-misses.md` — template only.

If any of these get populated during ongoing agent use, they become in-scope for future sweeps (per fix-C2 rationale).

**Memory:** a reference memory entry points to this file. Search memory for "openclaw-proactive-agent" or "tiered-agent-guard" if the path is forgotten.

---

## 9. Verification commands

Run after any fix to confirm no regression.

```bash
# Full built-in audit chain
./scripts/security-audit.sh && ./scripts/verify-policy.sh

# Drift check (targeted — should report status per-file, not shared)
for f in POLICY.md assets/SOUL.md SKILL.md scripts/*.sh; do
  printf "%s  " "$f"; shasum -a 256 "$f" | awk '{print $1}'
done

# Secret scan (broader than built-in)
grep -RInE 'sk-(ant|live|test)[_-][A-Za-z0-9_-]{10,}|AIza[0-9A-Za-z_-]{35}|ghp_[0-9A-Za-z]{36}|xoxb-[0-9A-Za-z-]{10,}|BEGIN [A-Z]+ PRIVATE KEY' . --exclude-dir=.git

# Credential-path check (extended)
for p in .credentials .aws .ssh .kube .config/gcloud .env .npmrc .pypirc \
         .netrc .docker .gnupg .git-credentials \
         'serviceAccountKey.json' 'secrets.yml' 'secrets.yaml'; do
  [ -e "$p" ] && echo "FOUND: $p"
done

# Append-only smoke test (once B4 lands)
tail -n 5 assets/AUDIT-LOG.md | grep -c 'Prev-entry-sha256:'  # expect ≥1

# ACL check (macOS)
ls -leR . 2>/dev/null | grep -E 'everyone.*allow.*write' && echo "ACL issue"

# Approval isolation (once B1 lands)
touch assets/approvals/test-deny 2>&1  # should be denied by runtime hook
```

### F-01 tamper-injection harness (verifies A1 fix)

Appends fake POLICY-APPROVED entries to the audit log, runs the script, checks
that per-file matching works, then restores the backup. Run from repo root:

```bash
set -euo pipefail
cp assets/AUDIT-LOG.md /tmp/audit-backup-$$.md

POLICY_SHA=$(shasum -a 256 POLICY.md | awk '{print $1}')
{
  echo
  echo "[2099-01-01T00:00:00Z] POLICY-APPROVED"
  echo "File: POLICY.md"
  echo "New-sha256: $POLICY_SHA"
  echo "Approved-by: test-harness"
  echo "Diff-summary: testing F-01 fix"
} >> assets/AUDIT-LOG.md

echo "=== Test A: only POLICY.md has approval ==="
bash scripts/security-audit.sh 2>&1 | grep -E '(matches|no prior|differs)'
# Expected: POLICY.md matches; SOUL/SKILL/scripts show 'no prior approval'

{
  echo
  echo "[2099-01-01T00:00:01Z] POLICY-APPROVED"
  echo "File: assets/SOUL.md"
  echo "New-sha256: 0000000000000000000000000000000000000000000000000000000000000000"
  echo "Approved-by: test-harness"
  echo "Diff-summary: testing F-01 detection"
} >> assets/AUDIT-LOG.md
echo "=== Test B: wrong SHA for SOUL.md ==="
bash scripts/security-audit.sh 2>&1 | grep -E '(matches|no prior|differs)'
# Expected: POLICY.md matches; SOUL.md 'differs from last approved'; others 'no prior'

cp /tmp/audit-backup-$$.md assets/AUDIT-LOG.md
rm /tmp/audit-backup-$$.md
```

### F-03 chain-tamper harness (verifies B4 fix)

Modifies a chained entry that has a chained successor and confirms
`verify-policy.sh §5` reports `chain mismatch`. Modifying the LAST
chained entry does not trigger detection (the last entry has no
successor whose `Prev-entry-sha256` could mismatch) — that is
by-design of any append-only hash-chain.

```bash
set -euo pipefail
cp assets/AUDIT-LOG.md /tmp/audit-backup-$$.md

# Pick the first chained entry (it has successors, so tamper will chain-fail)
first_prev=$(grep -n '^Prev-entry-sha256:' assets/AUDIT-LOG.md | head -1 | cut -d: -f1)
entry_start=$(awk -v up="$first_prev" 'NR<=up && /^\[/ {ls=NR} END{print ls}' assets/AUDIT-LOG.md)
outcome_line=$(awk -v s="$entry_start" -v e="$first_prev" \
  'NR>=s && NR<=e && /^Outcome:/ {print NR; exit}' assets/AUDIT-LOG.md)

# Surgical edit
sed -i.bak "${outcome_line} s/findings=0/findings=9/" assets/AUDIT-LOG.md
rm -f assets/AUDIT-LOG.md.bak

echo "=== After tamper — expect chain mismatch ==="
bash scripts/verify-policy.sh 2>&1 | grep -E '(chain mismatch|\[FAIL\]|chain verified)' | head

cp /tmp/audit-backup-$$.md assets/AUDIT-LOG.md
rm /tmp/audit-backup-$$.md
```

### End-to-end approval dry-run (verifies B1)

Demonstrates the approval path without executing any action. Not
automated — requires a TTY (by design).

```bash
# 1. Agent drafts a proposal in PROPOSALS.md with Status: pending-review.
# 2. Human runs:
./scripts/approve-proposal.sh
#    (list → pick number → type 'yes')
# 3. Result: assets/approvals/<sha>.approved created; TIER-2
#    approval-granted entry appended to AUDIT-LOG.md (chained).
# 4. Re-run verify-policy.sh §7 — should report:
#    "$n approval(s) structurally valid"
# 5. Executor (external to this script) then:
#    - recomputes sha of proposal body
#    - matches against proposal_sha256 in .approved file
#    - runs action
#    - flips consumed_at in .approved
#    - appends TIER-2 executed entry to AUDIT-LOG.md
```

---

## 10. Codex Compatibility Addendum

On 2026-05-19 the rebrand pass added a Codex compatibility audit. See
[`references/codex-compatibility-audit.md`](references/codex-compatibility-audit.md).

Result:

- Added repo-root `AGENTS.md`, because OpenAI Codex CLI loads repository
  guidance from that path and did not automatically load `assets/AGENTS.md`.
- Reframed `SKILL.md` as a universal integration entrypoint while preserving
  OpenClaw-compatible front matter.
- Documented the key Codex boundary: Markdown guidance is discoverability and
  prompt-level steering, not mechanical pre-tool enforcement. Hard enforcement
  still requires Codex sandbox approvals or a proxy that calls `spa_hooks`.
- Added root `AGENTS.md` to `scripts/security-audit.sh` required-file checks.
- Locked all `AGENTS.md` instruction surfaces as Tier 2 in `POLICY.md`,
  `spa_hooks`, and the audit drift checks.

---

## 11. Changelog

- **2026-04-22 (v1)** — Initial audit: 20 findings, 3 strategies, 0 fixes applied. Handoff complete.
- **2026-04-22 (v2)** — Strategy A patches applied to `scripts/security-audit.sh` and `scripts/verify-policy.sh`; opportunistic `doc_excludes` entry for `SECURITY-AUDIT.md`. 7 findings closed: F-01, F-05, F-06, F-10, F-17, F-18, F-19. F-01 verified functionally via tamper-injection harness. 13 findings remain open for Strategies B/C.
- **2026-04-22 (v3)** — Strategy B landed. New artifacts: `scripts/audit-log-append.sh` (hash-chain helper, F-03), `scripts/approve-proposal.sh` (TTY-gated approval, F-02/F-07), `assets/approvals/` (Tier-2-only write directory, F-02), `assets/approvals/README.md`. POLICY.md extended: §2.2 "Project-local scripts" (F-04), §11 "Approval Artifacts" (full approval-token mechanism). HEARTBEAT.md §7 extended + §8 proposal-expiration added (F-11). trust-tiers.md pseudocode rewritten for directory-based approvals with TOCTOU guard and single_use consumption. Opportunistic fixes: F-12 (env grep case-insensitive), F-15 (find -readable → portable `find -type f`), F-16 (rm family expanded to cover rmdir/unlink/shred/trash/-delete). All tracked files pinned via POLICY-APPROVED / SCRIPT-APPROVED entries; audit log now chained (17 entries OK); tamper detection functionally verified. **15 of 20 findings closed (3/3 critical, 4/5 high).** Remaining: F-08, F-09, F-13 (Strategy C), F-14 (accept as smoke-test), F-20 (cosmetic).
- **2026-04-22 (v4)** — Strategy C landed. Closed F-08 (ONBOARDING Step 1.5 validate + Step 2.5 readback), F-09 (pre-read injection hook via `scripts/injection-scan.sh` + HEARTBEAT §6 rewrite), F-13 (SOUL.md conditional edit pointing at POLICY §7/§11), F-20 (surprise-queue example wrap). F-14 accepted with explicit smoke-test annotation in `verify-policy.sh §3`. **C1 reference implementation landed**: `spa_hooks/` (policy.py, approvals.py, tests/test_vectors.py, README.md) — 36 unit tests pass covering all enforcement vectors from `trust-tiers.md` + deletion/network families + workspace guards + approval hygiene (expiry/consumed/TOCTOU/subject). **20 of 20 findings addressed — 19 fixed, 1 accepted.** All 3 critical, all 5 high closed.
- **2026-04-22 (v5)** — Self-re-audit of v4 new code surface discovered **F-21** (HIGH): `\brm\b`-style regex trivially bypassed by shell-quote obfuscation (`r''m`, `r\m`, `"rm"`, `p\ip install`). Fixed with shlex tokenization in `spa_hooks/policy.py::_tokenize_command` — patterns now match against both raw cmd and `' '.join(tokens)`. Extended `BLOCKED_COMMAND_PATTERNS` with code-execution surface (eval, exec, source, interpreter `-c/-e` forms). `references/trust-tiers.md` pseudocode updated to match. Added 20 regression tests (`ObfuscationBypass` class) covering obfuscated forms of rm/pip/npm + eval/exec/source/bash-c/python-c/perl-e + sanity tests that legit commands still pass. **Total: 56 tests passing, 21/21 findings addressed (20 fixed, 1 accepted).**

- **2026-04-22 (v5b)** — Self-re-audit of the F-21 patch discovered **F-22** (HIGH): combined interpreter flags (`bash -lc`, `sh -xvc`, `perl -pe`, etc.) bypassed the initial interpreter patterns. Fixed by allowing intermediate options and compressed flag sets in interpreter regexes. Regression tests added for compressed shell and Perl forms.
- **2026-05-19 (v6)** — Security audit discovered **F-23** (HIGH): `spa_hooks` shell classification treated any command not matching `BLOCKED_COMMAND_PATTERNS` as Tier 1, instead of enforcing POLICY.md §2.2 as an allowlist. Fixed with explicit shell allowlist logic, static shell path guards for outside-workspace and credential-looking paths, and documentation updates to the runtime hook template. Added 8 regression tests for unknown commands (`git commit`, `chmod`, `tee`, `sed -i`, bare `env`), outside-workspace shell paths, credential-looking paths, and positive allowlist cases. **Total: 72 tests passing, 23/23 findings addressed (22 fixed, 1 accepted).**

---

*End of SECURITY-AUDIT.md.*

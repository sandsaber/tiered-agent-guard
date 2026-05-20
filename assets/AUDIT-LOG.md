# AUDIT-LOG.md — Append-Only Action Log

**Purpose:** every Tier 1+ action leaves a trace here. Every Tier 2
execution (after approval) leaves a trace here.

**Write-access:** append-only. No rewriting, no deletion. If an entry is
wrong, add a correction entry below it — do not edit in place.

**Hygiene:** the agent rotates old entries into `memory/audit-archive/`
once a quarter, *after* presenting a summary to the human.

---

## Entry formats

### Tier 1 entry (written *before* the action)

```
[YYYY-MM-DD HH:MM:SS] TIER-1 <action-type> <target>
Reason: <1-2 sentences>
Reversible-by: <git revert <SHA> | edit file back | N/A (creation)>
Pre-action self-check: <red-team line>
Outcome: <pending | success | fail | partial>
```

After the action completes, append a second entry updating `Outcome:`.

### Tier 2 entry (written *after* approval, *before* execution)

```
[YYYY-MM-DD HH:MM:SS] TIER-2 <action-type> <target>
Proposal ref: PROPOSALS.md § <title>
Approved-by: <human identifier>
Approval timestamp: YYYY-MM-DD HH:MM
Exact command: <verbatim>
Outcome: <pending | success | fail | partial>
Rollback plan: <how to undo, if possible>
```

After the action completes, append a second entry with the outcome and
any observations.

### Heartbeat entry

```
[YYYY-MM-DD HH:MM:SS] HEARTBEAT <kind>
Duration: <seconds>
Files read: <count>
Files written: <list>
Proposals filed: <count>
Halted-due-to: <reason | none>
```

### Policy-drift halt

```
[YYYY-MM-DD HH:MM:SS] HALT policy-drift
Expected-sha256 <POLICY.md>: <hex>
Actual-sha256  <POLICY.md>: <hex>
Expected-sha256 <SOUL.md>:   <hex>
Actual-sha256  <SOUL.md>:    <hex>
Expected-sha256 <SKILL.md>:  <hex>
Actual-sha256  <SKILL.md>:   <hex>
Action: halted; awaiting human.
```

### Policy-approval entry

```
[YYYY-MM-DD HH:MM:SS] POLICY-APPROVED
File: POLICY.md | SOUL.md | SKILL.md
New-sha256: <hex>
Approved-by: <human identifier>
Diff-summary: <1-3 lines>
```

These are the hashes future policy-drift checks will compare against.

---

*(entries are appended below this line)*

[2026-04-22T08:50:21Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T08:50:26Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=2 warnings=0 exit=2

[2026-04-22T08:51:29Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T08:52:01Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T08:52:01Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:05:40Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:05:47Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:32:31Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:35:01Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:35:01Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=2 warnings=0 exit=2

[2026-04-22T09:35:44Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:35:44Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:36:20Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:38:11Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:38:11Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0

[2026-04-22T09:54:50Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 88a0916f8d5dbdb80f8a9252c02c9c0b31a7cffd97fc2f35ffa32c8abbc40087

[2026-04-22T09:54:50Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 8a1efb786ab67c3290925416662a2334b0783a8af2d49120ae081b5e1e2f1b7b

[2026-04-22T09:55:25Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: a23927a62a0b598072f1ff6d9c1f36bd529d12ada86fbea2cdecc9897c3baece

[2026-04-22T09:56:39Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 9536033e7fc697caa6d72c392721638c1cc8fb7bb286638dc7eff69f84a7270a

[2026-04-22T09:59:18Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 27ecc924cdf047a947dcb27215e0e56ad8f3b570e1d37419a39de2b24d7e5353

[2026-04-22T09:59:18Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: ab4b92b9be7f15c511cac6f6684a6c72598c343f47365b3b91456daa6dec1365

[2026-04-22T09:59:49Z] POLICY-APPROVED
File: POLICY.md
New-sha256: 41e18e11d964ee50e05853902a349a3af44c0be84983684cb017f1c41f782df7
Approved-by: michael@onoffapp.com
Diff-summary: Strategy B landing: §2.2 extended with Project-local scripts allowlist; §11 Approval Artifacts added (F-02, F-04, F-07, F-16 closed)
Prev-entry-sha256: a6aeec4bf75f541544594a3729d1bd1d6247c0e813c4f93319abaa0fc02afdf4

[2026-04-22T09:59:49Z] POLICY-APPROVED
File: assets/SOUL.md
New-sha256: b89413d320d33eba31ef38e546ebc556b354f044458d636e60793cb0c270e9eb
Approved-by: michael@onoffapp.com
Diff-summary: Strategy B landing: unchanged (content baseline pin)
Prev-entry-sha256: 95f0a1b27421c587b19241475e6fab1645468ad8b2de176b8cd0f0655ad32e5b

[2026-04-22T09:59:49Z] POLICY-APPROVED
File: SKILL.md
New-sha256: f90605bcf9268dcc1bdff845c7185ccb459adfd5c42abae7e7bf1e87534a0768
Approved-by: michael@onoffapp.com
Diff-summary: Strategy B landing: unchanged (content baseline pin)
Prev-entry-sha256: 4aab445363ed4343e0719b6ec07987e5380b1916b7b6b12fdd13c520e5e0050c

[2026-04-22T09:59:49Z] SCRIPT-APPROVED
File: scripts/security-audit.sh
New-sha256: ff011d7a6e596dfa30e6f62c9e460ff3225ae598bc6e9044e1829635131d23a7
Approved-by: michael@onoffapp.com
Diff-summary: Strategy A+B: §2 ACL, §3 secrets expanded, §4 cred paths expanded, §5 per-file drift + SCRIPT-APPROVED support, chain helper integration
Prev-entry-sha256: 38de2ebd5a909cebd84010f36fd353fc5ee2ffa3493b37b0d0e23136dcba5703

[2026-04-22T09:59:49Z] SCRIPT-APPROVED
File: scripts/verify-policy.sh
New-sha256: b9d3debf6aae412045c091c239c88da44faf6e82bf5aeb70b4756256010908e4
Approved-by: michael@onoffapp.com
Diff-summary: Strategy A+B: set -euo pipefail + robust sha256_of; §5 hash-chain verifier; §7 approvals consistency; Approval Artifacts section check
Prev-entry-sha256: f040e7a18e32d2d4657df5aef1ed6bb08a855b621da1076084032a6f2a9c2d8a

[2026-04-22T09:59:49Z] SCRIPT-APPROVED
File: scripts/audit-log-append.sh
New-sha256: 00731cefc3016a154e7bd1117325252e13bcb3e7de650161918f336faac9dcf7
Approved-by: michael@onoffapp.com
Diff-summary: Strategy B (new script): hash-chain append helper for AUDIT-LOG.md (F-03)
Prev-entry-sha256: 86a4bd14b6f88c2f1734fd9c1f23165cfd00294cfa976f0ca6bbb23fc3e79301

[2026-04-22T09:59:49Z] SCRIPT-APPROVED
File: scripts/approve-proposal.sh
New-sha256: 6729b8d6563ad45acc0954284aa47dace1486a50230ebed06fa2abc26795f10e
Approved-by: michael@onoffapp.com
Diff-summary: Strategy B (new script): human-gated approval creating assets/approvals/<sha>.approved with single_use semantics (F-02, F-07)
Prev-entry-sha256: 38c3843eb263d6d03f093772159e67e8db271ec5c3a1cc62c9783723962b1257

[2026-04-22T09:59:59Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: a6094bc946165263d66a425e8188861f22677d113e4869baa4b42dc9a88f5c08

[2026-04-22T09:59:59Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: da8448f5ccdca519e50b632ebeb09a37f26b409ffbe1c4c05d53fc8424fabf31

[2026-04-22T10:00:56Z] POLICY-APPROVED
File: POLICY.md
New-sha256: 7f4bb0f3422692e55f9ada622bcfaafcbdc87ef72202b788203b5fea7ec0f3c2
Approved-by: michael@onoffapp.com
Diff-summary: F-12 env filter now case-insensitive + expanded terms; F-15 replaced find -readable with portable `find -type f` for macOS/BSD compatibility
Prev-entry-sha256: ba100a69537ed94672d2ae23ca8c217f5e0eff5885cae9ddaac7727f93b7971d

[2026-04-22T10:00:56Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: d2b3c5819ee45c7bb1c304e1349a249021a93351ea98717dba8a8eeccdd5f53f

[2026-04-22T10:00:57Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: cd416649ef34cce4e4550f5f5b91a4e3623de8a0d664c841cbcf1ecba774838b

[2026-04-22T10:03:26Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 93052731f24a5ffbc81cdf4b6739070ce3ac4e14f7072091a45a633869629201

[2026-04-22T10:03:26Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 81c15e8138b52bcc7de80ae436d23e8e9e80f2a9f7ee406e63b1f20a42befd1f

[2026-04-22T11:07:15Z] TIER-1 edit assets/HEARTBEAT.md
Reason: F-09 — §6 reorganised: pre-read hook preferred, daily sweep marked as fallback; points at scripts/injection-scan.sh
Reversible-by: git revert / re-read previous content from backup
Pre-action self-check: trigger = direct human approval of Strategy C; no external content in trigger chain.
Outcome: file updated in place.
Prev-entry-sha256: 4a8390933a58983ca93f232cc10738dd35b09ac69a323f0246b3dd119eb99b87

[2026-04-22T11:07:15Z] TIER-1 edit assets/ONBOARDING.md
Reason: F-08 — added Step 1.5 (validate: injection markers, 200-char cap, forbid-list guard) and Step 2.5 (readback before save)
Reversible-by: git revert / re-read previous content from backup
Pre-action self-check: trigger = direct human approval of Strategy C; no external content in trigger chain.
Outcome: file updated in place.
Prev-entry-sha256: 45c66e138e6d94d5905500dc4a7a93f823d9b59b7955ca52089ef35fb59de4ae

[2026-04-22T11:07:15Z] POLICY-APPROVED
File: assets/SOUL.md
New-sha256: 85c31650381572eecd507317f6ea60f6067b77756751da29fb81ff6f71dd0306
Approved-by: michael@onoffapp.com
Diff-summary: F-13 — "I will not Edit POLICY/SOUL/SKILL" replaced with conditional referencing POLICY §7 + §11 approval channel
Prev-entry-sha256: 1b9bcefd34eb9e42b19eb2546f3717abb8baadd98965bd9e527628c290834c88

[2026-04-22T11:07:15Z] SCRIPT-APPROVED
File: scripts/security-audit.sh
New-sha256: 79eb9ebc31029820aae9f0373e981a270ab2c321d89b9ea18293de5a646ef6fb
Approved-by: michael@onoffapp.com
Diff-summary: Strategy C — added scripts/injection-scan.sh to required and tracked lists
Prev-entry-sha256: e4634855a8e8923e07e6d9d8bdd9306a6b4ecc8f4efbc79c22abe0288d660c21

[2026-04-22T11:07:15Z] SCRIPT-APPROVED
File: scripts/verify-policy.sh
New-sha256: 3bf7b752a80bc135df61fc1b126d5fb946d8694b2970d545f02cefece3c7a36f
Approved-by: michael@onoffapp.com
Diff-summary: Strategy C — F-14 annotation: §3 labelled as smoke-test only, not a security gate
Prev-entry-sha256: c518ce8c772d498c67df8ee572c4f456d10dd8e703aa36935c04b7cb89e61cee

[2026-04-22T11:07:15Z] SCRIPT-APPROVED
File: scripts/injection-scan.sh
New-sha256: 87b1fa0907e5d76b0fe2be59318dfbe952d817d1ffa1c12c631743dda636c0d1
Approved-by: michael@onoffapp.com
Diff-summary: Strategy C (new) — pre-read / sweep injection scanner with --quarantine auto-mode (F-09)
Prev-entry-sha256: 24362dbcee8045aa3c0cd69c631be8f0e3a829b824d23cfd22355ac02b18217d

[2026-04-22T11:07:15Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: a3fe2c50e28db47b9bb4870a6ceb6d537220a09c27fa2ea3506a1f37f49ca744

[2026-04-22T11:07:16Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: faa38457965eee17296f634da28e8b13c14b32fb71f38a8f42f3e3bff6efaddc

[2026-04-22T11:13:41Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: e3036b40f2fd35012ed97aa908bc9da51e94567599ac6dfb3f23a2d93bf3e318

[2026-04-22T11:13:41Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 4d2e084f80e8aebfa436f481a3cdc72a5c2e23d8848c2e108d42254f543d8bb4

[2026-04-22T11:25:56Z] TIER-1 edit spa_hooks/policy.py
Reason: F-21 fix — added _tokenize_command (shlex) and extended BLOCKED_COMMAND_PATTERNS (eval/exec/source + interpreter -c/-e forms); classify_tier now checks both raw and tokenized command
Reversible-by: git revert; tests pass under `python3 -m unittest spa_hooks.tests.test_vectors`
Pre-action self-check: trigger = self-re-audit finding F-21; no external content in trigger chain.
Outcome: fix applied; 56 unit tests pass.
Prev-entry-sha256: 459f1ee6b39c1c8eb282ea2f635818ce9b233a0b7a8796f3a703d7a46980875b

[2026-04-22T11:25:56Z] TIER-1 edit spa_hooks/tests/test_vectors.py
Reason: F-21 regression — added ObfuscationBypass class with 20 tests covering quote/escape bypass, interpreter -c, chained commands, and sanity cases
Reversible-by: git revert; tests pass under `python3 -m unittest spa_hooks.tests.test_vectors`
Pre-action self-check: trigger = self-re-audit finding F-21; no external content in trigger chain.
Outcome: fix applied; 56 unit tests pass.
Prev-entry-sha256: d018a94252de09e7239528a6ddfffcd26d1d969374fc4ba905d44691b408daf5

[2026-04-22T11:25:56Z] TIER-1 edit references/trust-tiers.md
Reason: F-21 — pseudocode updated with tokenize_command helper + dual-check in pre_tool_use; BLOCKED_COMMAND_PATTERNS extended
Reversible-by: git revert; tests pass under `python3 -m unittest spa_hooks.tests.test_vectors`
Pre-action self-check: trigger = self-re-audit finding F-21; no external content in trigger chain.
Outcome: fix applied; 56 unit tests pass.
Prev-entry-sha256: c35e7135e4b7776ae437294d34f8cc2a0d9ad18be04aa792d506b224305efcd0

[2026-04-22T11:25:56Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 422ce662be1a298a6c6cffb840903aa4d74f02435dfb65c92b1d9f984cf04b1e

[2026-04-22T11:25:57Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 1fabc2f95e00c42f2bd381f9d1844964c74a044ca234dbbe6cfcfe4679c00af3

[2026-04-22T11:32:42Z] TIER-1 edit F-22 fix
Reason: Second re-audit round found F-22 — compressed interpreter flags (bash -lc, perl -pe) bypassed F-21 interpreter patterns. Fixed by replacing \s+-c\b with [^|;&\n]*?\s-[a-zA-Z]*c\b in spa_hooks/policy.py + references/trust-tiers.md. Added awk -e to patterns. Added 7 regression tests.
Reversible-by: git revert
Pre-action self-check: trigger = self-re-audit; no external content in trigger chain.
Outcome: 63 unit tests pass (was 56).
Prev-entry-sha256: cdfef0f2558931fce282ea83d36954859fb0b0a46eb4eed046c0aaebf9b98b7d

[2026-04-22T11:32:42Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: de085829f03558230d19bf218c403f8932494eaf7b22a32079e82cab3af67c00

[2026-04-22T11:32:42Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 0e94516e9187eb782b8d3edd5f8e2776e20adcc352f3699c271ad70130286410

[2026-04-22T11:35:57Z] TIER-1 edit README.md
Reason: Comprehensive English rewrite for OpenClaw distribution — adds Architecture, Daily workflow, Security model sections covering approval artefacts + hash-chain + 3-layer injection defence; Components reference (5 scripts + spa_hooks); Known limitations (F-21/F-22 regex bounds); Integration notes for Claude Code / Anthropic SDK / generic proxy; Audit chronology (22 findings closed).
Reversible-by: git revert; prior version of README.md preserved in git history
Pre-action self-check: trigger = direct human request; no external content in trigger chain.
Outcome: README.md replaced, ~400 lines.
Prev-entry-sha256: 97cd233ec033e5dcd7f8beb2fcba2f8b7bc7e314a5e30f6548838df4ce405d55

[2026-04-22T11:35:57Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 25f8268bf9cb1c8c7f2845c8da624158128e14b6139bfdf8f73545b1754c115c

[2026-04-22T11:35:58Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=2 warnings=0 exit=2
Prev-entry-sha256: 7bbc0122a2af506621c84aac2f31368af5a8ac388db2fc80918162c85dd7b22e

[2026-04-22T11:36:22Z] SCRIPT-APPROVED
File: scripts/verify-policy.sh
New-sha256: a94aaa2b1f5552173835f5cf6791e9b778c0e2e13d855d0c867ff0169b246477
Approved-by: michael@onoffapp.com
Diff-summary: doc_excludes extended to include README.md (comprehensive OpenClaw README quotes forbidden strings from upstream contradictions for documentation purposes, same class as comparison-with-v3.md and SECURITY-AUDIT.md)
Prev-entry-sha256: 270ff2f7a3ea3a2136f00d3161fde81ba62f366e4288b2ce8ad5961524e3e1d8

[2026-04-22T11:36:23Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: cc3eac20a9ffa7106ceb3859379edaf8ef98a5b3f2b3988b67cb3943b803bf87

[2026-04-22T11:36:24Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: b64167a88f19de461c6c2e4af05f70ded545989faf5a2f0919723fc7cd287d51

[2026-04-22T12:00:29Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 23168f627be5dcda4c6d11f42473cd49ba651345205a6a7124dae24526f2cf44

[2026-04-22T12:00:30Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 84cb41ada741611401b8f911baf7a609b0db521cefc270be975547cd0ca66695

[2026-04-22T12:01:54Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: e95874f56f6fbba8ad8b9fb952d47d4ce24b88990ad32fefebf75cadd8f76977

[2026-04-22T12:01:54Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 23ec5a74003302dff9f784fee257efa8512deee80ac2726d814465e6fb205afd

[2026-05-19T16:42:02Z] POLICY-APPROVED
File: POLICY.md
New-sha256: 572e469b9b167a6ac4fac67cf0ba243af810102078f8bb7903d988a8bcebbfe0
Approved-by: direct human request in Codex session
Diff-summary: Rebrand header from Safe Proactive Agent to Tiered Agent Guard; policy rules unchanged.
Prev-entry-sha256: b99cc684736210b95222430bd62eddb1b4730d5f0dbaa7b87e455c3085f788c0

[2026-05-19T16:42:03Z] POLICY-APPROVED
File: SKILL.md
New-sha256: 4ab5addc881a360c50ffd9f42c2b4897abc48d0d0dd20e766624ff4afdcb8592
Approved-by: direct human request in Codex session
Diff-summary: Rebrand OpenClaw entrypoint to Tiered Agent Guard while keeping SKILL.md filename and integration semantics.
Prev-entry-sha256: c3e25fad83310c42f3b659673a9ebd8eb88432993cc0e863e6e59ffab9296529

[2026-05-19T16:42:04Z] SCRIPT-APPROVED
File: scripts/security-audit.sh
New-sha256: 259d43fda3aa053094ec891e260a26a085b56f9727d33a0afc0ea9c4ed959b81
Approved-by: direct human request in Codex session
Diff-summary: Rebrand user-visible audit banner/comment only; enforcement logic unchanged.
Prev-entry-sha256: 514c3e2c009bc0856ae067fd0cc17ddcddb3eadc56c57ca34abd1a507863f060

[2026-05-19T16:42:05Z] SCRIPT-APPROVED
File: scripts/verify-policy.sh
New-sha256: 79d5c7722f886eb9d8e8134e56c84977c614a37991107cedf2e265606d16370e
Approved-by: direct human request in Codex session
Diff-summary: Rebrand user-visible policy compliance banner/comment only; enforcement logic unchanged.
Prev-entry-sha256: 31405b03618ee24e5089adf56238bffd1c083441c5164cc37147ce8d9373f950

[2026-05-19T16:42:31Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 5022dd1e1d8d94faf59387b2232807e2f7666f1e3ae77545f2c47a6aa12fbe06

[2026-05-19T16:42:34Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 0d89e4f2c0f854d153e76eac58fcaefaedfda746e7919b64f0b96befee703539

[2026-05-19T16:42:42Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: c64d1ca40be4e9c4d88fa11639ea2e6cd2a702b37ece0cbb87bd978771477686

[2026-05-19T16:43:22Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: c605052b4671b543844db46e3cc24232e28ddf0379730fe1f80bf51b37c7c5df

[2026-05-19T16:43:25Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 46a3f5f996c89eb94fd808adeb752544e839ff0a54137819a52de85f0f3a53ad

[2026-05-19T16:55:21Z] POLICY-APPROVED
File: POLICY.md
New-sha256: ba3d4beab8f26be625dd0f0679e4a562b4fe353512a2e5d47ebd7431e237ae0a
Approved-by: direct human request in Codex session
Diff-summary: Codex compatibility hardening: version 1.1.0, approval artifacts clarified, AGENTS.md instruction surfaces locked as Tier 2.
Prev-entry-sha256: 321057f9dae1f31787377611ceea62ca95de374d9c6fb58ef50f84b9bbd39059

[2026-05-19T16:55:22Z] POLICY-APPROVED
File: SKILL.md
New-sha256: 5d68796c6019836bcd87042353a4b751641e4d247dc4f0c99874ef1b938546f4
Approved-by: direct human request in Codex session
Diff-summary: Reframed OpenClaw skill file as universal integration entrypoint while preserving OpenClaw-compatible front matter.
Prev-entry-sha256: d6f479ce39d085ba6a195b004cde4d18714a52ceef448dca779cbf21617979ad

[2026-05-19T16:55:23Z] POLICY-APPROVED
File: AGENTS.md
New-sha256: d0dad50fb4d839dc9d4cfbe6ce216b73c08d3c13cf98147690ad4980522367ec
Approved-by: direct human request in Codex session
Diff-summary: Added repo-root Codex/universal adapter that loads POLICY, README, trust tiers, and spa_hooks guidance.
Prev-entry-sha256: 2ae04681bd51415ab9c821959b24ff34c9e9654d79d45b413adb4d7e3baa70ef

[2026-05-19T16:55:24Z] POLICY-APPROVED
File: assets/AGENTS.md
New-sha256: ab9faf87a8e2a013632e146993ba5b390fd13599b34e7c95aea127a3ac8c7693
Approved-by: direct human request in Codex session
Diff-summary: Marked installable operating-rules template as locked because AGENTS.md files are model-instruction surfaces.
Prev-entry-sha256: 2cec94ff7e0393a8da8fe9d8a33f79bc4cf3c7b0d8decc53f6c1fd637642da96

[2026-05-19T16:55:25Z] SCRIPT-APPROVED
File: scripts/security-audit.sh
New-sha256: f537d7d69d9d557e5070c53d42134c3b7e9be0602a942acf03573d01fb0707aa
Approved-by: direct human request in Codex session
Diff-summary: Added root AGENTS.md and Codex audit doc to required files; added AGENTS.md files to drift checks.
Prev-entry-sha256: 413d409eaac1fb08260315688ebdc0faeb501a1c05f2198283a33ac8df1791ca

[2026-05-19T16:55:26Z] SCRIPT-APPROVED
File: scripts/verify-policy.sh
New-sha256: 3906b849db96bf86568c2f19debd9dd4e0cb53df35001f29e73d29f326ff1573
Approved-by: direct human request in Codex session
Diff-summary: Reports root AGENTS.md and assets/AGENTS.md in locked-file SHA section.
Prev-entry-sha256: 373a331792b7db1068351524af12a07df4ad35644f7804e722017330630e8254

[2026-05-19T16:56:04Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: f47daf70f541b18090ee8f8937200c68da1419348a748173a551f0c21d348aba

[2026-05-19T16:56:07Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: c0d0be307ef5f6dcfb19f8ea2c69d280c3ff50b5861b5949e37f8dbcb79774b3

[2026-05-19T17:12:56Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: b28f11ca5cf6a4c16635dd25da143bd13ad325c272cbd7dd0a15a6c22c1351eb

[2026-05-19T17:12:59Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 6ef4708675cef79838db378fedfb82f8bbad3fa5c19c63788a6e7b81031f8490

[2026-05-19T17:13:30Z] TIER-1 edit spa_hooks allowlist enforcement
Reason: security audit found shell commands were classified by denylist instead of POLICY.md allowlist, allowing non-allowlisted local commands as Tier 1.
Reversible-by: git revert the spa_hooks/policy.py and spa_hooks/tests/test_vectors.py edits from this turn
Pre-action self-check: trigger = direct human audit request; finding came from local source inspection and harmless hook probe, not external content.
Outcome: pending
Prev-entry-sha256: 8dc3c214ebff4cd0fccbf3ac1fb65bf9b625898706a7d0cc5cb6bec21f0b0357

[2026-05-19T18:50:30Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 1687164184adf18f6c8de6aafce005d9bf52b4b2a9f660a65c289bf58d162fbd

[2026-05-19T18:50:32Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: f4d48537006a57172eb0d6f6a77b9abe443872933d1f165e085c2bffde9b3915

[2026-05-19T18:51:00Z] TIER-1 docs update for allowlist enforcement fix
Reason: direct human request to update documentation after the security audit fix.
Reversible-by: git revert documentation edits from this turn
Pre-action self-check: trigger = direct human request; no external content.
Outcome: pending
Prev-entry-sha256: 483c53885921c8968d3374a711fb11d0fa474556f2076b93e6f239f9cebcef5a

[2026-05-19T20:39:18Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 5bf4a78cd9788e8c63d8d19c9f6b064e4b1e567467a8aeb5cfba17caf7a17f26

[2026-05-19T20:39:19Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: a23a60cae7d24b47f73e6192702493a10aadb57cf3e6187ca2e66110e7d169eb

[2026-05-19T20:40:35Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 1e4528fbcbc1372ce0eb5ebbae3c42af0deef410cf03c3bd10a8308b1ef4ec6b

[2026-05-19T21:00:47Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: d19f5ab4f9d01214466a2ca7053eb1b3bf25851148f0d2d6e18c22711f8e57dd

[2026-05-19T21:10:28Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 5d3ec0155b2774a8efda899caa51f8b528fc65a310447568b2c30f71fb024e8b

[2026-05-19T21:10:29Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: e5016178001b7da376256cc9a508b4357e87e6a621b45c7b4da8ca8432997d10

[2026-05-20T00:00:00Z] TIER-1 audit-log truncation Codex self-application residue
Reason: Removed 50 malformed entries (former lines 711-760) left by a Codex session that applied this framework to itself. The removed entries had missing Prev-entry-sha256 lines (broken chain), placeholder timestamps `2026-05-20 00:00:00`, non-monotonic ordering, and Outcome: pending never closed.
Reversible-by: git revert of the truncation commit; the malformed content is preserved in git history (commit prior to this entry).
Pre-action self-check: trigger = direct human request to clean the log; the malformed entries are local repo state, not external content; user explicitly chose "truncate + add note" with full awareness that this violates strict append-only.
Pre-trunc-sha256: 808457728bd33ad87394cc9834983c10cd08d0f76ddf6f5ff04048c3d80bdc01
Outcome: success
Prev-entry-sha256: 99f34c7531a185aa9d5f5665d3877622230fc557c3077253c2b7cd7a6b1a9bba

[2026-05-20T09:04:02Z] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 625d7e1d8efcc0904c5ef2bc0a0464203b18d89c89db62179ef9e3ebb814a96a

[2026-05-20T09:04:03Z] TIER-1 security-audit.sh
Reason: routine audit
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=0 warnings=0 exit=0
Prev-entry-sha256: 2546b4e8a00fcc1760ec509a58d6b153c460f6bbf8938bfdebddef122debe4fe

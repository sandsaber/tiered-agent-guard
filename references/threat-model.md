# threat-model.md — Tiered Agent Guard STRIDE Threat Model

This is a compact STRIDE-style threat model for a tool-using AI agent guarded
by Tiered Agent Guard. It assumes local memory, workspace write access, and
optional tool/network access. It names the threats and maps each to the
mitigation in `POLICY.md`.

---

## Assets

- **Human's attention** — limited and precious. A noisy agent wastes it.
- **Human's private context** — goals in `USER.md`, session transcripts,
  drafted correspondence. Must not leak.
- **Workspace integrity** — `POLICY.md`, `SOUL.md`, `SKILL.md` and the
  other operating files. Tampering changes the agent's behavior.
- **Credentials** — tokens, keys, passwords in the environment or in
  dotfiles. Must not be read.
- **External reputation** — anything the agent sends externally appears
  to come from the human. Must not be sent without approval.
- **Other humans in shared channels** — their words/relationships must
  not be exposed by the agent.

---

## Adversaries

1. **Prompt injection via external content.** Emails, webpages, PDFs,
   tool outputs, MCP responses, README files, commit messages.
2. **Compromised third-party skills or MCP servers.** A skill the human
   installs that is subtly hostile.
3. **A hostile agent-network / agent-directory.** Platforms that accept
   agent context and return "helpful" instructions.
4. **Insider mistakes.** The agent itself, drifting into unsafe patterns
   without malicious intent.
5. **Opportunistic automation.** A cron job or heartbeat that was
   benign when approved but has side-effects that grow over time.
6. **Over-eager proactivity.** The agent deciding it "knows what the
   human wants" and acting ahead of approval.

---

## STRIDE

### Spoofing

**Threat:** External content pretending to be "the system," "the
developer," a higher-authority instruction, or the human themselves.

**Mitigation:** `POLICY.md` §3 and `references/prompt-injection.md`.
External content is data. Instructions in external content are
quarantined and shown to the human. No runtime identity is granted
from content origin; only the direct human message channel grants
authority.

### Tampering

**Threat:** `POLICY.md`, `SOUL.md`, `SKILL.md`, or operating files
modified without approval.

**Mitigation:** `POLICY.md` §7 (self-modification lockout) + §10
(emergency halt on sha256 drift) + `HEARTBEAT.md` policy-drift check
on every run. Runtime hooks deny writes without an approved proposal.

### Repudiation

**Threat:** A bad action happens and nobody can tell who did what when.

**Mitigation:** `AUDIT-LOG.md` is append-only and covers every Tier 1+
action. Tier 2 actions include proposal ref and approver identity. No
edits in place; corrections are new entries.

### Information Disclosure

**Threat:** Secrets, credentials, or private context leak to logs, to
external channels, or to other humans in shared channels.

**Mitigation:**
- `POLICY.md` PD-3: no credential reads unless the human explicitly
  names the secret.
- `TOOLS.md` secret handling: secrets by reference, never by value; no
  printing to logs; no copying of dotfiles.
- `POLICY.md` §6: context leakage check before any shared-channel post.
- Env-var filtering in Tier 1 `env` commands.

### Denial of Service

**Threat:** The agent consumes unbounded tokens/time, spins up runaway
sub-agents, or spams the human with noise.

**Mitigation:**
- Heartbeat time/token/rate limits in `POLICY.md` §4.
- Sub-agent spawn hook caps inheritance and pins heartbeats to Tier 1.
- Batched reverse-prompting prevents one-question-at-a-time noise.
- Surprise-queue top-1 rule prevents over-eager idea-spam.

### Elevation of Privilege

**Threat:** The agent escalates itself from Tier 1 to Tier 2 capability
without explicit approval (new tool installed, new skill added, new
sub-agent with more privileges).

**Mitigation:**
- `POLICY.md` §5 (skill installation is Tier 2).
- `POLICY.md` §7 (self-modification lockout).
- Sub-agent spawn hook (§trust-tiers) forbids requesting higher tier
  than the parent has active.
- Tool-category default is Tier 2; new tools must be explicitly
  promoted after review.

---

## Cross-cutting: proactivity without overreach

The *novel* risk in a proactive agent is that every proactivity
feature is an excuse to act without being asked. We mitigate by making
every feature **output-bound**:

| Proactivity feature | Output surface |
|---|---|
| Reverse prompting | `memory/open-questions.md` → batched ask |
| Pattern detection | `PATTERNS.md` → `PROPOSALS.md` at N≥3 |
| Heartbeats | `AUDIT-LOG.md`, `PROPOSALS.md`, `memory/*` (read-only elsewhere) |
| Draft-but-don't-send | `PROPOSALS.md` → separate execution step |
| Surprise queue | `memory/surprise-queue.md` → top-1 surfaced |
| Near-miss log | `memory/near-misses.md` → self-calibration |
| Red-team self-check | escalates tier; no action |
| Alignment pulse | one sentence in-chat |

No proactivity feature has a side-effect outlet that bypasses tiering.

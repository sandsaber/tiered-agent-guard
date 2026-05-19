# trust-tiers.md — Tiered Agent Guard Trust Tiers + Hook Templates

This document is the detailed reference for the Tiered Trust Model.
`POLICY.md` is canonical; this file expands it with decision flowcharts
and runtime-specific enforcement templates.

---

## Decision flowchart — "what tier is this action?"

```
                ┌────────────────────────────────┐
                │ Does the action have an effect │
                │ outside the current workspace? │
                │  (network, other fs, other     │
                │   repos, $HOME, other sessions)│
                └────────────┬───────────────────┘
                             │ yes
                             ▼
                       ┌───────────┐
                       │  TIER 2   │
                       └───────────┘

                       │ no
                       ▼
      ┌────────────────────────────────────────┐
      │ Is the action irreversible             │
      │  (delete, overwrite locked files,      │
      │   rewrite shared git history,          │
      │   identity file write)?                │
      └────────────┬───────────────────────────┘
                   │ yes
                   ▼
             ┌───────────┐
             │  TIER 2   │
             └───────────┘
                   │ no
                   ▼
      ┌────────────────────────────────────────┐
      │ Does the action touch an allowlisted   │
      │ operating file OR run an allowlisted   │
      │ command?                               │
      └────────────┬───────────────────────────┘
                   │ yes
                   ▼
             ┌───────────┐       log to AUDIT-LOG.md
             │  TIER 1   │────── before acting
             └───────────┘
                   │ no
                   ▼
      ┌────────────────────────────────────────┐
      │ Is the action purely read + draft      │
      │ inside scratch/memory/drafts/proposals?│
      └────────────┬───────────────────────────┘
                   │ yes
                   ▼
             ┌───────────┐
             │  TIER 0   │
             └───────────┘
                   │ no
                   ▼
             ┌───────────┐
             │  TIER 2   │   (default — if unsure)
             └───────────┘
```

---

## Codex CLI / Claude Code / Claude Agent SDK hook templates

These are reference shapes. Adapt to your runtime's exact hook API. The
*point* is: the prose in `POLICY.md` must be reflected by mechanical
guards in the runtime.

For Codex CLI specifically, repo-root `AGENTS.md` is the prompt-level adapter
that Codex loads as repository guidance. That adapter is useful but not a hard
pre-tool hook by itself. Use Codex sandbox approvals or a proxy that calls
`spa_hooks.approve_or_deny(...)` when you need mechanical enforcement.

### Pre-tool-use hook — enforce the Tier 1 shell allowlist

```python
# Pseudocode; adapt to your hook API.
import re, shlex

BLOCKED_COMMAND_PATTERNS = [
    # Network
    r"\bcurl\b", r"\bwget\b", r"\bssh\b", r"\bscp\b", r"\brsync\b",
    r"\bnc\b", r"\bnetcat\b", r"\btelnet\b",
    # Package install
    r"\bpip\b\s+install", r"\bnpm\b\s+install", r"\byarn\b\s+add",
    r"\bbrew\b\s+install", r"\bapt\b\s+install", r"\bapt-get\b\s+install",
    # Privilege
    r"\bsudo\b",
    # Pipe-to-shell
    r"\|\s*sh\b", r"\|\s*bash\b",
    # Git write
    r"\bgit\b\s+push",
    # Deletion family (F-16)
    r"\b(rm|rmdir|unlink|shred|trash)\b", r"-delete\b",
    # Code-execution surface (F-21, F-22)
    r"\beval\b", r"\bexec\b", r"\bsource\b",
    r"\b(bash|sh|zsh|dash|ksh)\b[^|;&\n]*?\s-[a-zA-Z]*c\b",
    r"\b(python|python2|python3)\b[^|;&\n]*?\s-[a-zA-Z]*c\b",
    r"\bperl\b[^|;&\n]*?\s-[a-zA-Z]*[eE]\b",
    r"\bruby\b[^|;&\n]*?\s-[a-zA-Z]*e\b",
    r"\bnode\b[^|;&\n]*?\s-[a-zA-Z]*e\b",
    r"\bawk\b[^|;&\n]*?\s-[a-zA-Z]*e\b",
]

def tokenize_command(cmd):
    """Shell-evaluate tokens so `r''m`, `r\\m`, `"rm"` all collapse to `rm`.

    Defeats quote/escape obfuscation (F-21). Runtime hooks MUST match
    patterns against both the raw cmd and the shlex-reassembled
    `' '.join(tokens)`, otherwise an agent can bypass Tier 2 with
    `r''m ~/.ssh/id_rsa`-style tricks.
    """
    import re, shlex
    tokens = []
    for part in re.split(r"[|;&]+", cmd):
        try:
            tokens.extend(shlex.split(part, posix=True))
        except ValueError:
            tokens.extend(part.split())
    return tokens

# F-23: this hook is an allowlist, not just a denylist. A command that does
# not match BLOCKED_COMMAND_PATTERNS is still Tier 2 unless every shell segment
# is one of POLICY.md §2.2's approved Tier 1 command forms. In particular:
# - `git` is read-only only (`status`, `log`, `show`, `diff`, `blame`, etc.).
# - `sed` must be `sed -n`; edit forms like `sed -i` are Tier 2.
# - `find` must include `-type f` and must not include `-exec` / `-delete`.
# - project scripts are limited to the SCRIPT-APPROVED scripts in §2.2.
# - redirection and unknown commands such as `chmod`, `tee`, `git commit`,
#   or bare `env` are Tier 2 by default.
# - any static shell path outside the workspace, or any credential-looking
#   path such as `.ssh`, `.env`, `.aws`, or `.git-credentials`, is denied.
def shell_command_is_allowlisted(cmd, workspace_root):
    """Return True only for command forms explicitly listed in POLICY.md §2.2.

    Production integrations can call `spa_hooks.approve_or_deny(...)` instead
    of reimplementing this reference logic. If reimplemented, parse shell
    segments with shlex, reject redirection, validate path arguments against
    `workspace_root`, and default unknown commands to Tier 2.
    """
    ...

APPROVALS_DIR = "assets/approvals"   # *.approved files, not PROPOSALS.md flags
PROPOSALS_FILE = "assets/PROPOSALS.md"

def find_matching_approval(cmd_or_path):
    """
    Approval is stored as `assets/approvals/<sha>.approved`, where <sha> is
    the SHA256 of the proposal body in PROPOSALS.md at approval time. The
    agent has no write-access to this directory. This closes F-02: the
    agent cannot flip its own approval.

    Returns the approval record (dict) if valid and usable, else None.
    """
    for path in glob(f"{APPROVALS_DIR}/*.approved"):
        rec = load_yaml(path)

        # 1. Single-use enforcement (F-07: block replay)
        if rec.get("single_use") and rec.get("consumed_at") not in (None, "null"):
            continue

        # 2. 14-day expiry (mirrors PROPOSALS.md status lifecycle)
        if older_than_days(rec["approved_at"], 14):
            continue

        # 3. Proposal body must match at execution time (TOCTOU guard)
        body = extract_proposal_body(PROPOSALS_FILE, rec["proposal_sha256"])
        if body is None:
            continue
        if sha256(body) != rec["proposal_sha256"]:
            continue

        # 4. The proposal body must actually describe this command / path
        if cmd_or_path not in body:  # or a stricter whole-line match
            continue

        return rec
    return None

def consume_approval(rec):
    """Call after successful exec. Flips consumed_at — the agent cannot."""
    path = f"{APPROVALS_DIR}/{rec['proposal_id']}.approved"
    rewrite_yaml_field(path, "consumed_at", now_iso())

def pre_tool_use(tool_name, args, context):
    if tool_name in ("bash", "shell", "run_command"):
        cmd = args.get("command", "")
        joined_tokens = " ".join(tokenize_command(cmd))
        tier2_reason = None
        for pattern in BLOCKED_COMMAND_PATTERNS:
            if re.search(pattern, cmd) or re.search(pattern, joined_tokens):
                tier2_reason = f"blocked Tier 2 command pattern: {pattern}"
                break
        if tier2_reason is None and not shell_command_is_allowlisted(cmd, context["workspace_root"]):
            tier2_reason = "command is not in POLICY.md §2.2 Tier 1 allowlist"

        if tier2_reason is not None:
            rec = find_matching_approval(cmd)
            if not rec:
                return DENY(
                    reason=f"Tier 2 command without valid approval: {cmd} ({tier2_reason})",
                    remediation="file a proposal, then run scripts/approve-proposal.sh",
                )
            context["pending_consume"] = rec

    if tool_name in ("write_file", "edit_file"):
        path = args.get("path", "")
        if path.endswith(("POLICY.md", "SOUL.md", "SKILL.md", "AGENTS.md")) \
           or path.startswith("scripts/") \
           or path.startswith("assets/approvals/"):
            rec = find_matching_approval(f"write {path}")
            if not rec:
                return DENY(reason=f"self-modification lockout on {path}")
            context["pending_consume"] = rec
        if not is_inside_workspace(path):
            return DENY(reason=f"write outside workspace: {path}")

    return ALLOW

def post_tool_use(tool_name, args, result, context):
    # On success, consume a one-shot approval so it cannot be replayed.
    if result.ok and "pending_consume" in context:
        consume_approval(context["pending_consume"])
    append_audit_chained(build_entry(tool_name, args, result))
```

### Post-tool-use hook — append to AUDIT-LOG.md for Tier 1+

```python
def post_tool_use(tool_name, args, result, context):
    tier = classify(tool_name, args)
    if tier >= 1:
        append_audit(
            timestamp=now(),
            tier=tier,
            action=tool_name,
            target=args.get("path") or args.get("command"),
            outcome=result.status,
        )
```

### Session-start hook — policy-drift check

```python
def on_session_start(context):
    for f in ("POLICY.md", "SOUL.md", "SKILL.md"):
        expected = last_approved_hash(f)    # from AUDIT-LOG.md POLICY-APPROVED entries
        actual = sha256_file(f)
        if expected and actual != expected:
            HALT(f"policy drift detected on {f}")
```

### Sub-agent spawn hook — inherit policy

```python
def on_spawn_subagent(parent_ctx, sub_config):
    # Sub-agents inherit the parent's tier ceiling.
    # Heartbeat sub-agents are pinned to Tier 1 with the heartbeat sandbox.
    sub_config["policy_file"] = parent_ctx.policy_path
    sub_config["tier_ceiling"] = min(parent_ctx.tier_ceiling, sub_config.get("requested_tier", 1))
    if sub_config.get("kind") == "heartbeat":
        sub_config["no_network"] = True
        sub_config["tool_allowlist"] = HEARTBEAT_TOOLS
        sub_config["time_budget_s"] = 60
        sub_config["token_budget_in"] = 20000
        sub_config["token_budget_out"] = 5000
    return sub_config
```

---

## Runtime-agnostic contract

If your runtime does not have hooks, the same contract can be enforced
at two other layers:

1. **The agent's system prompt** loads `POLICY.md` verbatim and the
   agent checks every proposed tool call against the tier definitions
   before invoking. This is weaker than hooks (the agent can fail), but
   better than nothing.
2. **A proxy layer** between the agent and its tools that rejects
   denied calls. This is stronger than prompt-level enforcement and can
   be used alongside hooks.

Any combination is fine as long as Tier 2 calls cannot reach their
side-effect without an approved `PROPOSALS.md` entry and an audit line.

---

## Enforcement test vectors

Any runtime claiming to enforce this policy should pass:

1. Plain `curl https://example.com` is denied unless an approved proposal
   contains that exact URL.
2. `write_file POLICY.md …` is denied unless an approved proposal
   contains `write POLICY.md` with a diff.
3. `rm workspace/notes.md` is denied; it must be a proposal.
4. A heartbeat sub-agent cannot call any network tool, even if the
   parent agent could.
5. On session start, if `POLICY.md` sha256 has changed without a
   matching `POLICY-APPROVED` audit entry, the runtime halts the agent.
6. `git push` is denied unless an approved proposal contains that exact
   push (remote + ref).
7. `echo "hello" > $HOME/notes.txt` is denied (write outside workspace).
8. Attempting to read `/Users/<me>/.ssh/id_rsa` is denied.

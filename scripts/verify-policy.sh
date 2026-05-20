#!/usr/bin/env bash
# verify-policy.sh — Tiered Agent Guard policy compliance check
#
# Verifies that the workspace state matches POLICY.md expectations.
# Read-only; appends a run summary to AUDIT-LOG.md.
#
# Exit codes:
#   0 — compliant
#   1 — compliance warnings
#   2 — compliance failures (agent must halt until resolved)
#   3 — script error
set -euo pipefail

SELF="$(basename "$0")"

# Split-layout flags. Defaults preserve single-root behaviour:
#   POLICY_ROOT = repo root (where this script lives)
#   STATE_ROOT  = POLICY_ROOT (legacy)
POLICY_ROOT_FLAG=""
STATE_ROOT_FLAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --policy-root) POLICY_ROOT_FLAG="$2"; shift 2 ;;
    --state-root)  STATE_ROOT_FLAG="$2";  shift 2 ;;
    *) shift ;;
  esac
done
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLICY_ROOT="${POLICY_ROOT_FLAG:-$ROOT}"
STATE_ROOT="${STATE_ROOT_FLAG:-$ROOT}"
cd "$POLICY_ROOT" || { echo "[$SELF] cannot cd to $POLICY_ROOT"; exit 3; }

findings=0
warnings=0
note() { printf '  %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; warnings=$((warnings+1)); }
fail() { printf '[FAIL] %s\n' "$*"; findings=$((findings+1)); }

sha256_of() {
  { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; } \
    || { sha256sum "$1" 2>/dev/null | awk '{print $1}'; } \
    || echo ""
}

echo "==== Tiered Agent Guard — policy compliance ===="
echo "Policy root: $POLICY_ROOT"
echo "State  root: $STATE_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

# ------------------------------------------------------------------
# 1. POLICY.md declares the right sections
# ------------------------------------------------------------------
echo "[1/7] POLICY.md structure"
if [ -f "POLICY.md" ]; then
  required_sections=(
    "Prime Directives"
    "The Tiered Trust Model"
    "Tier 0"
    "Tier 1"
    "Tier 2"
    "Command Allowlists"
    "Prompt Injection Defenses"
    "Autonomous Cron / Heartbeat Restrictions"
    "Tool Migration & Skill Installation"
    "Context Leakage"
    "Self-Modification Lockout"
    "Evolution"
    "Enforcement"
    "Emergency Stop"
    "Approval Artifacts"
  )
  for s in "${required_sections[@]}"; do
    if grep -Fq "$s" POLICY.md; then
      note "present: $s"
    else
      fail "POLICY.md missing section: $s"
    fi
  done
else
  fail "POLICY.md not found"
fi
echo

# ------------------------------------------------------------------
# 2. SOUL.md declares the boundaries
# ------------------------------------------------------------------
echo "[2/7] SOUL.md boundary clause"
if [ -f "assets/SOUL.md" ]; then
  if grep -Eq 'I will not:' assets/SOUL.md && grep -Eq 'I will:' assets/SOUL.md; then
    note "boundary clauses present"
  else
    fail "SOUL.md missing 'I will' / 'I will not' clauses"
  fi
else
  fail "SOUL.md not found"
fi
echo

# ------------------------------------------------------------------
# 3. No contradictory directives surviving from v3.1.0
# ------------------------------------------------------------------
#
# SMOKE TEST ONLY — not a security gate (see SECURITY-AUDIT.md F-14).
# This is exact-string matching against a small list of phrases from the
# upstream v3.1.0 skill. A paraphrase trivially bypasses it (e.g.,
# "skip the queue", "auto-approve", non-English rewording). Treat a pass
# as "no trivial regression to the old framing" — not as "the policy is
# safe." Real enforcement is per-tier via POLICY.md §§0–2, §7, §11.
#
echo "[3/7] Forbidden directives (smoke test — exact strings from v3.1.0)"
# Note: we exclude documentation files that intentionally *quote* the old text
# when explaining what changed.
doc_excludes=(
  "--exclude-dir=.git"
  "--exclude=comparison-with-v3.md"
  "--exclude=prompt-injection.md"
  "--exclude=verify-policy.sh"
  "--exclude=security-audit.sh"
  "--exclude=SECURITY-AUDIT.md"
  "--exclude=README.md"
)
forbidden_strings=(
  "Don't ask permission"
  "Just do it"
  "Ask forgiveness, not permission"
  "act without approval"
  "no approval needed"
)
for s in "${forbidden_strings[@]}"; do
  if grep -R -I -n "${doc_excludes[@]}" -F "$s" . >/dev/null 2>&1; then
    fail "forbidden directive found in operating files: $s"
    grep -R -I -n "${doc_excludes[@]}" -F "$s" . | head -3 | sed 's/^/    /'
  else
    note "absent: \"$s\""
  fi
done
echo

# ------------------------------------------------------------------
# 4. Locked files: SOUL.md, POLICY.md, SKILL.md, AGENTS.md
# ------------------------------------------------------------------
echo "[4/7] Locked-file sha256 (informational; runtime should enforce)"
for f in POLICY.md assets/SOUL.md SKILL.md AGENTS.md assets/AGENTS.md; do
  if [ -f "$f" ]; then
    h=$(sha256_of "$f")
    note "$f  sha256: $h"
  fi
done
echo

# ------------------------------------------------------------------
# 5. AUDIT-LOG.md hash-chain integrity (B4)
# ------------------------------------------------------------------
echo "[5/7] AUDIT-LOG chain integrity"
if [ ! -f "$STATE_ROOT/assets/AUDIT-LOG.md" ]; then
  warn "AUDIT-LOG.md not present yet (first run?)"
else
  sha_cmd() { { shasum -a 256 2>/dev/null; } || { sha256sum; }; }
  chain_count=0
  chain_bad=0
  while IFS= read -r pln; do
    [ -z "$pln" ] && continue
    chain_count=$((chain_count + 1))
    claimed=$(awk -v ln="$pln" 'NR==ln {sub(/^Prev-entry-sha256:[[:space:]]*/, ""); print; exit}' "$STATE_ROOT/assets/AUDIT-LOG.md")
    entry_start=$(awk -v up="$pln" 'NR<=up && /^\[/ {ls=NR} END{print ls}' "$STATE_ROOT/assets/AUDIT-LOG.md")
    if [ -z "$entry_start" ]; then
      fail "chain: cannot locate entry start for Prev-entry-sha256 at line $pln"
      chain_bad=$((chain_bad + 1)); continue
    fi
    content_end=$((entry_start - 2))
    if [ "$content_end" -lt 1 ]; then
      expected=$(printf '' | sha_cmd | awk '{print $1}')
    else
      expected=$(head -n "$content_end" "$STATE_ROOT/assets/AUDIT-LOG.md" | sha_cmd | awk '{print $1}')
    fi
    if [ "$expected" != "$claimed" ]; then
      fail "chain mismatch at entry starting line $entry_start: expected $expected, got $claimed"
      chain_bad=$((chain_bad + 1))
    fi
  done < <(grep -nE '^Prev-entry-sha256:' "$STATE_ROOT/assets/AUDIT-LOG.md" | cut -d: -f1 || true)
  if [ "$chain_count" -eq 0 ]; then
    note "no chained entries yet (pre-B4 log; will chain on next append)"
  elif [ "$chain_bad" -eq 0 ]; then
    note "chain verified: $chain_count entries OK"
  fi
fi
echo

# ------------------------------------------------------------------
# 6. Heartbeat sandbox declared
# ------------------------------------------------------------------
echo "[6/7] Heartbeat sandbox"
if [ -f "$STATE_ROOT/assets/HEARTBEAT.md" ]; then
  for k in "Sandbox rules" "tool allowlist" "time" "tokens" "Rate"; do
    if grep -iq "$k" "$STATE_ROOT/assets/HEARTBEAT.md"; then
      note "sandbox clause: $k"
    else
      warn "HEARTBEAT.md missing clause: $k"
    fi
  done
else
  fail "HEARTBEAT.md not found"
fi
echo

# ------------------------------------------------------------------
# 7. Approvals directory consistency (B1)
# ------------------------------------------------------------------
echo "[7/7] Approvals consistency"
APPROVALS_DIR="$STATE_ROOT/assets/approvals"
if [ ! -d "$APPROVALS_DIR" ]; then
  note "no approvals/ directory (pre-B1 bundle)"
else
  n_approvals=0
  bad_approvals=0
  for f in "$APPROVALS_DIR"/*.approved; do
    [ -e "$f" ] || continue
    n_approvals=$((n_approvals + 1))
    for field in proposal_sha256 approved_at approved_by single_use consumed_at; do
      if ! grep -qE "^${field}:" "$f"; then
        fail "approval $f missing field: $field"
        bad_approvals=$((bad_approvals + 1))
      fi
    done
    consumed_at=$(awk -F': ' '/^consumed_at:/ {print $2; exit}' "$f")
    if [ "$consumed_at" != "null" ] && ! [[ "$consumed_at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T ]]; then
      warn "approval $f: consumed_at is neither null nor ISO timestamp: '$consumed_at'"
    fi
  done
  if [ "$n_approvals" -eq 0 ]; then
    note "no approval artifacts yet"
  elif [ "$bad_approvals" -eq 0 ]; then
    note "$n_approvals approval(s) structurally valid"
  fi
fi
echo

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "Summary"
echo "Findings: $findings"
echo "Warnings: $warnings"

exit_code=0
if [ "$findings" -gt 0 ]; then exit_code=2
elif [ "$warnings" -gt 0 ]; then exit_code=1; fi

if [ -f "$STATE_ROOT/assets/AUDIT-LOG.md" ]; then
  entry=$(cat <<ENTRY
[$(date -u +%Y-%m-%dT%H:%M:%SZ)] TIER-1 verify-policy.sh
Reason: routine compliance check
Reversible-by: N/A (read-only + append)
Pre-action self-check: trigger = human or onboarding; no external content.
Outcome: findings=$findings warnings=$warnings exit=$exit_code
ENTRY
)
  if [ "$STATE_ROOT" = "$POLICY_ROOT" ] && [ -x "$POLICY_ROOT/scripts/audit-log-append.sh" ]; then
    printf '%s\n' "$entry" | "$POLICY_ROOT/scripts/audit-log-append.sh"
  else
    {
      printf '\n'
      printf '%s\n' "$entry"
    } >> "$STATE_ROOT/assets/AUDIT-LOG.md"
  fi
fi

exit "$exit_code"

#!/usr/bin/env bash
# security-audit.sh — Tiered Agent Guard security audit
#
# Read-only. Appends a run summary to AUDIT-LOG.md.
# Does not modify any operating file except AUDIT-LOG.md (append-only).
#
# Exit codes:
#   0 — clean
#   1 — warnings (human should review)
#   2 — findings (halt-worthy; agent must stop until human reviews)
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

echo "==== Tiered Agent Guard — security audit ===="
echo "Policy root: $POLICY_ROOT"
echo "State  root: $STATE_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

# ------------------------------------------------------------------
# 1. Required files present
# ------------------------------------------------------------------
echo "[1/7] Required files"
# Canonical policy + scripts + locked-asset templates live under POLICY_ROOT.
required_policy=(
  "AGENTS.md"
  "SKILL.md"
  "POLICY.md"
  "assets/SOUL.md"
  "assets/AGENTS.md"
  "references/trust-tiers.md"
  "references/threat-model.md"
  "references/prompt-injection.md"
  "references/comparison-with-v3.md"
  "references/codex-compatibility-audit.md"
  "scripts/security-audit.sh"
  "scripts/verify-policy.sh"
  "scripts/audit-log-append.sh"
  "scripts/approve-proposal.sh"
  "scripts/injection-scan.sh"
)
# Mutable / per-project state files live under STATE_ROOT.
required_state=(
  "assets/USER.md"
  "assets/ONBOARDING.md"
  "assets/SESSION-STATE.md"
  "assets/MEMORY.md"
  "assets/HEARTBEAT.md"
  "assets/TOOLS.md"
  "assets/PROPOSALS.md"
  "assets/PATTERNS.md"
  "assets/AUDIT-LOG.md"
  "assets/memory/working-buffer.md"
  "assets/memory/open-questions.md"
  "assets/memory/near-misses.md"
  "assets/memory/surprise-queue.md"
  "assets/approvals/README.md"
)
for f in "${required_policy[@]}"; do
  if [ -f "$POLICY_ROOT/$f" ]; then
    note "found  $f"
  else
    fail "missing $f (policy)"
  fi
done
for f in "${required_state[@]}"; do
  if [ -f "$STATE_ROOT/$f" ]; then
    note "found  $f"
  else
    fail "missing $f (state)"
  fi
done
echo

# ------------------------------------------------------------------
# 2. File permissions
# ------------------------------------------------------------------
echo "[2/7] File permissions (no world-write, scripts executable)"
# Build the set of roots to scan: POLICY_ROOT, plus STATE_ROOT if different.
scan_roots=("$POLICY_ROOT")
if [ "$STATE_ROOT" != "$POLICY_ROOT" ]; then
  scan_roots+=("$STATE_ROOT")
fi
for scan_root in "${scan_roots[@]}"; do
  [ -d "$scan_root" ] || continue
  while IFS= read -r -d '' f; do
    # world-writable bit (POSIX mode)
    perms=$(stat -f '%Lp' "$f" 2>/dev/null || stat -c '%a' "$f" 2>/dev/null || echo "???")
    case "$perms" in
      *2|*3|*6|*7) warn "world-writable (mode): $f ($perms)" ;;
    esac
  done < <(find "$scan_root" -type f -not -path '*/.git/*' -print0)

  # macOS ACL layer — independent of POSIX mode; skip gracefully if -e unsupported.
  if ls -le / >/dev/null 2>&1; then
    acl_hits=$(ls -leR "$scan_root" 2>/dev/null | grep -E '^[[:space:]]*[0-9]+:[[:space:]]+(everyone|group:everyone).*allow.*(write|add|delete)' || true)
    if [ -n "$acl_hits" ]; then
      warn "macOS ACL grants write to 'everyone' on some file(s) under $scan_root:"
      echo "$acl_hits" | head -5 | sed 's/^/    /'
    fi
  fi
done

for s in "$POLICY_ROOT"/scripts/*.sh; do
  [ -e "$s" ] || continue
  if [ -x "$s" ]; then note "executable ${s#$POLICY_ROOT/}"; else warn "not executable ${s#$POLICY_ROOT/}"; fi
done
echo

# ------------------------------------------------------------------
# 3. Secret-leak grep
# ------------------------------------------------------------------
echo "[3/7] Secret-leak grep (patterns likely to indicate a committed secret)"
# Files that legitimately contain token-shaped strings as examples / test vectors.
grep_excludes=(
  --exclude-dir=.git
  --exclude-dir=node_modules
  --exclude=prompt-injection.md
  --exclude=security-audit.sh
  --exclude=SECURITY-AUDIT.md
)
patterns=(
  'aws_secret_access_key'
  'AKIA[0-9A-Z]{16}'
  'ASIA[0-9A-Z]{16}'
  'gh[pousr]_[0-9A-Za-z_]{30,}'
  'sk-[A-Za-z0-9_-]{20,}'
  'sk_live_[0-9a-zA-Z]{24,}'
  'pk_live_[0-9a-zA-Z]{24,}'
  'rk_live_[0-9a-zA-Z]{24,}'
  'AIza[0-9A-Za-z_-]{35}'
  'xoxb-[0-9A-Za-z-]{10,}'
  'xoxp-[0-9A-Za-z-]{10,}'
  'xoxa-[0-9A-Za-z-]{10,}'
  'xapp-[0-9]+-[A-Z0-9]+-[0-9]+-[a-f0-9]+'
  'eyJ[A-Za-z0-9_=-]{10,}\.[A-Za-z0-9_=-]{10,}\.[A-Za-z0-9_.+/=-]*'
  'BEGIN (RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY'
  'Authorization:[[:space:]]*(Bearer|Basic)[[:space:]]+[A-Za-z0-9._+/=-]{10,}'
  '\-\-password[[:space:]]+[^[:space:]]'
)
# Scan both POLICY_ROOT and STATE_ROOT (if distinct). The split layout means
# the per-project STATE_ROOT is where user data accumulates and is the most
# important place to keep secret-free; POLICY_ROOT is also scanned so the
# canonical files cannot quietly grow leaks upstream.
leak_hit=0
for scan_root in "${scan_roots[@]}"; do
  [ -d "$scan_root" ] || continue
  for p in "${patterns[@]}"; do
    if grep -R -I -n -E "$p" "$scan_root" "${grep_excludes[@]}" >/dev/null 2>&1; then
      fail "secret-like pattern matched in $scan_root: $p"
      grep -R -I -n -E "$p" "$scan_root" "${grep_excludes[@]}" 2>/dev/null | head -5 | sed 's/^/    /'
      leak_hit=$((leak_hit+1))
    fi
  done
done
if [ "$leak_hit" -eq 0 ]; then note "no secret-like patterns"; fi
echo

# ------------------------------------------------------------------
# 4. Credential directories / files that should not exist in workspace
# ------------------------------------------------------------------
echo "[4/7] Forbidden credential locations inside workspace"
forbidden=(
  ".credentials"
  ".aws"
  ".ssh"
  ".kube"
  ".config/gcloud"
  ".env"
  ".npmrc"
  ".pypirc"
  ".netrc"
  ".docker"
  ".gnupg"
  ".git-credentials"
  ".pgpass"
)
for scan_root in "${scan_roots[@]}"; do
  [ -d "$scan_root" ] || continue
  for p in "${forbidden[@]}"; do
    if [ -e "$scan_root/$p" ]; then
      fail "forbidden: $scan_root contains $p — credentials must live outside"
    fi
  done
done

# name-pattern check (anywhere in tree) for stray credential-like files
forbidden_names=(
  '*.pem'
  '*.p12'
  '*.pfx'
  '*.keystore'
  '*.jks'
  '*.ppk'
  'id_rsa'
  'id_ed25519'
  'id_ecdsa'
  'id_dsa'
  'serviceAccountKey.json'
  'secrets.yml'
  'secrets.yaml'
)
for scan_root in "${scan_roots[@]}"; do
  [ -d "$scan_root" ] || continue
  for pat in "${forbidden_names[@]}"; do
    matches=$(find "$scan_root" -type f -name "$pat" -not -path '*/.git/*' 2>/dev/null || true)
    if [ -n "$matches" ]; then
      fail "forbidden credential-like files matching '$pat' under $scan_root:"
      echo "$matches" | head -5 | sed 's/^/    /'
    fi
  done
done
note "scan complete"
echo

# ------------------------------------------------------------------
# 5. POLICY / SOUL / SKILL / AGENTS / scripts drift check
# ------------------------------------------------------------------
echo "[5/7] Policy drift"

# Fetch the most recent POLICY-APPROVED or SCRIPT-APPROVED New-sha256 for a
# given target file. Per-File matching — unrelated approvals no longer
# masquerade as this file's. Both entry types share the same schema
# (see POLICY.md §11.6).
last_approved_sha() {
  local target="$1"
  local log="$STATE_ROOT/assets/AUDIT-LOG.md"
  [ -f "$log" ] || { echo ""; return 0; }
  awk -v target="$target" '
    /^\[.*(POLICY-APPROVED|SCRIPT-APPROVED)/ {
      if (in_block && file == target && sha != "") matched=sha
      in_block=1; file=""; sha=""; next
    }
    /^\[/ {
      if (in_block && file == target && sha != "") matched=sha
      in_block=0; file=""; sha=""
    }
    in_block && /^File:/ {
      sub(/^File:[[:space:]]*/, "", $0); file=$0
    }
    in_block && /^New-sha256:/ {
      sub(/^New-sha256:[[:space:]]*/, "", $0); sha=$0
    }
    END {
      if (in_block && file == target && sha != "") matched=sha
      print matched
    }
  ' "$log"
}

sha256_of() {
  { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; } \
    || { sha256sum "$1" 2>/dev/null | awk '{print $1}'; } \
    || echo ""
}

if [ -f "$STATE_ROOT/assets/AUDIT-LOG.md" ]; then
  # PD-2 declares AGENTS.md and scripts/ locked alongside POLICY/SOUL/SKILL.
  # All tracked files are canonical and live under POLICY_ROOT (including
  # assets/SOUL.md and assets/AGENTS.md, which are policy-shaped templates
  # owned by the plugin install, not per-project state).
  tracked=(
    "POLICY.md"
    "assets/SOUL.md"
    "SKILL.md"
    "AGENTS.md"
    "assets/AGENTS.md"
    "scripts/security-audit.sh"
    "scripts/verify-policy.sh"
    "scripts/audit-log-append.sh"
    "scripts/approve-proposal.sh"
    "scripts/injection-scan.sh"
  )
  for f in "${tracked[@]}"; do
    if [ ! -f "$POLICY_ROOT/$f" ]; then
      warn "tracked file missing: $f"
      continue
    fi
    last_approved=$(last_approved_sha "$f")
    actual=$(sha256_of "$POLICY_ROOT/$f")
    if [ -z "$actual" ]; then
      warn "$f could not be hashed (shasum/sha256sum missing?)"
    elif [ -z "$last_approved" ]; then
      note "$f no prior approval recorded (first run?)"
    elif [ "$last_approved" = "$actual" ]; then
      note "$f sha256 matches last approved"
    else
      warn "$f sha256 differs from last approved — human must confirm"
    fi
  done
else
  note "AUDIT-LOG.md not present; skipping drift check"
fi
echo

# ------------------------------------------------------------------
# 6. Stray pending proposals older than 14 days
# ------------------------------------------------------------------
echo "[6/7] Stale proposals (>14 days in pending-review)"
if [ -f "$STATE_ROOT/assets/PROPOSALS.md" ]; then
  today_epoch=$(date +%s)
  # very loose: any line with "Status: pending-review" paired with a date in the prior heading
  old_n=$(awk '
    /^## \[([0-9]{4}-[0-9]{2}-[0-9]{2})/ { match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/); d=substr($0,RSTART,RLENGTH); date=d }
    /Status:[[:space:]]*pending-review/ && date != "" { print date }
  ' "$STATE_ROOT/assets/PROPOSALS.md" | while read -r d; do
    if [ -n "$d" ]; then
      # GNU date; macOS compatibility via fallback
      s=$(date -d "$d" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$d" +%s 2>/dev/null || echo 0)
      if [ "$s" -gt 0 ] && [ $((today_epoch - s)) -gt $((14*86400)) ]; then echo 1; fi
    fi
  done | wc -l | tr -d ' ')
  if [ "${old_n:-0}" -gt 0 ]; then
    warn "$old_n proposal(s) pending-review for >14 days (auto-expire rule fires)"
  else
    note "no stale proposals"
  fi
fi
echo

# ------------------------------------------------------------------
# 7. Summary
# ------------------------------------------------------------------
echo "[7/7] Summary"
echo "Findings: $findings"
echo "Warnings: $warnings"

exit_code=0
if [ "$findings" -gt 0 ]; then exit_code=2
elif [ "$warnings" -gt 0 ]; then exit_code=1; fi

# Append to audit log — via the chain-helper when available (B4); otherwise legacy.
# The helper script lives in POLICY_ROOT but currently writes to its own ROOT's
# assets/AUDIT-LOG.md. When STATE_ROOT differs from POLICY_ROOT, use direct
# append so the entry lands in the per-project state file. The split-root
# helper is wired up in a later task.
if [ -f "$STATE_ROOT/assets/AUDIT-LOG.md" ]; then
  entry=$(cat <<ENTRY
[$(date -u +%Y-%m-%dT%H:%M:%SZ)] TIER-1 security-audit.sh
Reason: routine audit
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

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

# Build a minimal split layout.
POLICY_ROOT="$ROOT"                           # the repo itself = canonical policy
STATE_ROOT="$TMP/.tiered-agent-guard"
mkdir -p "$STATE_ROOT/assets/approvals" "$STATE_ROOT/assets/memory"
cp "$ROOT/assets/AUDIT-LOG.md"       "$STATE_ROOT/assets/AUDIT-LOG.md"
cp "$ROOT/assets/PROPOSALS.md"       "$STATE_ROOT/assets/PROPOSALS.md"
cp "$ROOT/assets/SESSION-STATE.md"   "$STATE_ROOT/assets/SESSION-STATE.md"
cp "$ROOT/assets/MEMORY.md"          "$STATE_ROOT/assets/MEMORY.md"
cp "$ROOT/assets/HEARTBEAT.md"       "$STATE_ROOT/assets/HEARTBEAT.md"
cp "$ROOT/assets/USER.md"            "$STATE_ROOT/assets/USER.md"
cp "$ROOT/assets/TOOLS.md"           "$STATE_ROOT/assets/TOOLS.md"
cp "$ROOT/assets/PATTERNS.md"        "$STATE_ROOT/assets/PATTERNS.md"
cp "$ROOT/assets/SOUL.md"            "$STATE_ROOT/assets/SOUL.md"
cp "$ROOT/assets/AGENTS.md"          "$STATE_ROOT/assets/AGENTS.md"
cp "$ROOT/assets/ONBOARDING.md"      "$STATE_ROOT/assets/ONBOARDING.md"
cp -r "$ROOT/assets/memory/."        "$STATE_ROOT/assets/memory/"
cp -r "$ROOT/assets/approvals/."     "$STATE_ROOT/assets/approvals/"

# This invocation MUST exit 0 (clean) or 1 (warnings) after the flag is added.
# Exit 2 = findings (a real failure of the split-root contract).
# Exit 3 = script error.
# A drift warning against scripts/security-audit.sh is expected until the
# matching POLICY-APPROVED entry is recorded in a later phase, so warnings
# tier is treated as acceptance here.
set +e
"$POLICY_ROOT/scripts/security-audit.sh" \
    --policy-root "$POLICY_ROOT" \
    --state-root  "$STATE_ROOT" \
    > "$TMP/audit.out" 2>&1
rc=$?
set -e
if [ "$rc" -ge 2 ]; then
    echo "FAIL: security-audit.sh exit=$rc (findings or error)" >&2
    cat "$TMP/audit.out" >&2
    exit 1
fi

# Sanity: the script must have actually honoured --state-root by reading the
# state copy of AUDIT-LOG.md and appending a run summary to it.
if ! grep -q "security-audit.sh" "$STATE_ROOT/assets/AUDIT-LOG.md"; then
    echo "FAIL: state AUDIT-LOG.md was not touched by the audit run" >&2
    cat "$TMP/audit.out" >&2
    exit 1
fi

echo "PASS: security-audit.sh accepted split roots (exit=$rc)"

set +e
"$POLICY_ROOT/scripts/verify-policy.sh" \
    --policy-root "$POLICY_ROOT" \
    --state-root  "$STATE_ROOT" \
    > "$TMP/verify.out" 2>&1
VERIFY_RC=$?
set -e
case "$VERIFY_RC" in
  0|1) ;;
  *) echo "FAIL: verify-policy.sh exit=$VERIFY_RC" >&2; cat "$TMP/verify.out" >&2; exit 1 ;;
esac

# Sanity: verify-policy.sh must have honoured --state-root and appended its
# run summary to the state copy of AUDIT-LOG.md.
if ! grep -q "verify-policy.sh" "$STATE_ROOT/assets/AUDIT-LOG.md"; then
    echo "FAIL: state AUDIT-LOG.md was not touched by the verify run" >&2
    cat "$TMP/verify.out" >&2
    exit 1
fi

echo "PASS: verify-policy.sh accepted split roots (exit=$VERIFY_RC)"

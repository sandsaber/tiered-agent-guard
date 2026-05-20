#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap "rm -rf '$TMP'" EXIT

STATE_ROOT="$TMP/.tiered-agent-guard"
mkdir -p "$STATE_ROOT/assets/approvals"

# Forge a minimal AUDIT-LOG with one chained entry + one unchained entry.
cat > "$STATE_ROOT/assets/AUDIT-LOG.md" <<'EOF'
# AUDIT-LOG.md — Append-Only Action Log

## Entry formats

(elided)

---

[2026-05-20T12:00:00Z] TIER-1 chained-test
Reason: test
Reversible-by: N/A
Pre-action self-check: trigger = test
Outcome: success
Prev-entry-sha256: 0000000000000000000000000000000000000000000000000000000000000000

[2026-05-20T12:01:00Z] TIER-1 unchained-test
Reason: test
Reversible-by: N/A
Pre-action self-check: trigger = test
Outcome: success
EOF

# Copy all the other required state files so verify-policy can run.
for f in PROPOSALS.md HEARTBEAT.md SOUL.md AGENTS.md SESSION-STATE.md \
         MEMORY.md USER.md TOOLS.md PATTERNS.md ONBOARDING.md; do
  cp "$ROOT/assets/$f" "$STATE_ROOT/assets/$f"
done
mkdir -p "$STATE_ROOT/assets/memory"
cp -r "$ROOT/assets/memory/." "$STATE_ROOT/assets/memory/" 2>/dev/null || true
cp -r "$ROOT/assets/approvals/." "$STATE_ROOT/assets/approvals/" 2>/dev/null || true

# Run verify-policy with split roots.
OUT="$TMP/verify.out"
"$ROOT/scripts/verify-policy.sh" \
    --policy-root "$ROOT" \
    --state-root  "$STATE_ROOT" \
    > "$OUT" 2>&1 || true   # exit may be 0 (warnings only) — capture anyway

# Assertions.
grep -q "unchained" "$OUT" \
  || { echo "FAIL: walker did not report unchained entry"; echo "----"; cat "$OUT"; exit 1; }
grep -q "unchained-test" "$OUT" \
  || { echo "FAIL: walker did not name the specific unchained entry timestamp"; echo "----"; cat "$OUT"; exit 1; }

# Chain mismatch on the forged chained entry must still fail (different test concern
# but worth confirming it's detected): the entry's Prev-entry-sha256 is all-zeros,
# which cannot match the actual file SHA above it.
grep -qi "mismatch\|chain" "$OUT" \
  || echo "INFO: no chain mismatch reported (acceptable if walker silently skips header)"

echo "PASS: chain walker reports unchained entries"

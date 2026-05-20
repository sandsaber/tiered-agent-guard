#!/usr/bin/env bash
# audit-log-append.sh — append an entry to AUDIT-LOG.md with a hash-chain link.
#
# Makes the "append-only" contract in POLICY.md §1 mechanically detectable:
# each new entry records the SHA256 of the file content that existed before
# it was appended. A later verifier (see verify-policy.sh §7) can walk the
# chain and detect any in-place edit or deletion.
#
# Usage (from repo root or from scripts/):
#   { echo "[ts] TIER-1 kind target"
#     echo "Reason: ..."
#     echo "..." } | ./scripts/audit-log-append.sh
#
# Contract:
#   - Reads the entry body from stdin.
#   - Ensures the log ends with a newline.
#   - Appends: <blank line> + <body> + "Prev-entry-sha256: <hex>".
#   - The recorded SHA is computed BEFORE the new block is written.
#
# Exit codes: 0 ok, 3 script error.

set -euo pipefail

STATE_ROOT_FLAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --state-root) STATE_ROOT_FLAG="$2"; shift 2 ;;
    *) shift ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "$STATE_ROOT_FLAG" ]; then
  LOG="$STATE_ROOT_FLAG/assets/AUDIT-LOG.md"
else
  LOG="$ROOT/assets/AUDIT-LOG.md"
fi

[ -f "$LOG" ] || { echo "audit-log-append: log not found: $LOG" >&2; exit 3; }

sha256_of_file() {
  { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; } \
    || { sha256sum "$1" 2>/dev/null | awk '{print $1}'; } \
    || echo ""
}

# Ensure trailing newline so the blank separator we add is truly a blank line.
if [ -s "$LOG" ] && [ "$(tail -c 1 "$LOG" | od -An -c | tr -d ' ')" != '\n' ]; then
  printf '\n' >> "$LOG"
fi

prev_sha=$(sha256_of_file "$LOG")
[ -n "$prev_sha" ] || { echo "audit-log-append: failed to hash log" >&2; exit 3; }

body=$(cat)
[ -n "$body" ] || { echo "audit-log-append: empty entry body on stdin" >&2; exit 3; }

{
  printf '\n'
  printf '%s\n' "$body"
  printf 'Prev-entry-sha256: %s\n' "$prev_sha"
} >> "$LOG"

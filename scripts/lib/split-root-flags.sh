# scripts/lib/split-root-flags.sh
# Shared --policy-root / --state-root flag parser for audit-aware scripts.
#
# Contract:
#   - Caller must have $ROOT set before sourcing (typically:
#       ROOT="$(cd "$(dirname "$0")/.." && pwd)"
#     or for libs called from within scripts/, equivalent path resolution).
#   - Caller must have $@ still containing its argv when sourcing (scripts that
#     consume args before sourcing should save and restore them).
#   - Caller must source via `. "$(dirname "$0")/lib/split-root-flags.sh"` so
#     `$0` resolution still points at the caller, not the lib.
#
# After sourcing, these are exported in caller scope:
#   POLICY_ROOT  — where canonical policy + scripts live
#   STATE_ROOT   — where mutable per-project state lives
# Both default to $ROOT when no flags are passed (legacy single-root mode).
#
# Behaviour:
#   - Unknown flags are silently ignored (consistent with existing callers).
#   - If exactly one of --policy-root / --state-root is provided, exit 3 with
#     an error message naming the caller.

_POLICY_ROOT_FLAG=""
_STATE_ROOT_FLAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --policy-root) _POLICY_ROOT_FLAG="$2"; shift 2 ;;
    --state-root)  _STATE_ROOT_FLAG="$2";  shift 2 ;;
    *) shift ;;
  esac
done

POLICY_ROOT="${_POLICY_ROOT_FLAG:-$ROOT}"
STATE_ROOT="${_STATE_ROOT_FLAG:-$ROOT}"

if [ -n "$_POLICY_ROOT_FLAG$_STATE_ROOT_FLAG" ] && \
   { [ -z "$_POLICY_ROOT_FLAG" ] || [ -z "$_STATE_ROOT_FLAG" ]; }; then
  echo "$(basename "${BASH_SOURCE[1]:-$0}"): --policy-root and --state-root must be used together" >&2
  exit 3
fi

unset _POLICY_ROOT_FLAG _STATE_ROOT_FLAG

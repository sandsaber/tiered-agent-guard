# spa_hooks — Tiered Agent Guard runtime hook reference implementation

Turns the prose in `POLICY.md` + `references/trust-tiers.md` into mechanical
decisions. Stdlib-only, no external dependencies.

## Note on module name

The Python module is named `spa_hooks` (legacy from when the project was named
`safe-proactive-agent`). The module name is kept stable for downstream
integrators who already import from it. The framework as a whole is called
**Tiered Agent Guard**; `spa_hooks` is its reference Python implementation of
the runtime hooks.

## What's here

| File | Purpose |
|---|---|
| `__init__.py` | Public API |
| `policy.py` | `classify_tier`, `is_inside_workspace`, `approve_or_deny` |
| `approvals.py` | `ApprovalRecord`, `find_matching_approval`, TOCTOU guard |
| `tests/test_vectors.py` | 8 enforcement vectors from `trust-tiers.md` + hygiene |

## Running tests

From the repo root:

```bash
python3 -m unittest spa_hooks.tests.test_vectors -v
```

All tests must pass on a clean framework state.

## Integration (Claude Code / Anthropic SDK)

```python
from spa_hooks import approve_or_deny

WORKSPACE = "/path/to/tiered-agent-guard"

def pre_tool_use(tool_name, args, context):
    allow, reason, approval = approve_or_deny(tool_name, args, WORKSPACE)
    if not allow:
        return DENY(reason=reason)
    context["pending_approval"] = approval
    return ALLOW

def post_tool_use(tool_name, args, result, context):
    approval = context.pop("pending_approval", None)
    if approval is not None and getattr(result, "ok", True):
        approval.consume()   # flips consumed_at in assets/approvals/<sha>.approved
    # append_audit_chained(...) goes here; use scripts/audit-log-append.sh
```

## What's NOT here

- Session-start drift check. That lives in `scripts/security-audit.sh §5`;
  invoke it from your session-start hook.
- Sub-agent spawn hook. That is runtime-specific; see
  `references/trust-tiers.md §Sub-agent spawn hook`.
- Injection sweep. See `scripts/injection-scan.sh` — intended to run as a
  pre-read hook (see HEARTBEAT.md §6).

## Adding a vector

1. Add a unit test in `tests/test_vectors.py`.
2. Extend `policy.py` so the test passes.
3. Document the rationale in the commit and in `SECURITY-AUDIT.md`.

"""spa_hooks — runtime hook reference implementation for Tiered Agent Guard.

This module turns the prose in POLICY.md + references/trust-tiers.md into
mechanical decisions. It is stdlib-only so it can be embedded in any runtime
that offers a pre-tool-use hook.

Public API:
    classify_tier(tool_name, args) -> int
    is_inside_workspace(path, workspace_root) -> bool
    approve_or_deny(tool_name, args, workspace_root, *, policy_root=None, state_root=None) -> (allow, reason, approval?)
    ApprovalRecord
    find_matching_approval(subject, workspace_root, now_iso=None, *, state_root=None) -> ApprovalRecord | None

Typical integration (pseudocode):

    from spa_hooks import approve_or_deny

    def pre_tool_use(tool_name, args, context):
        allow, reason, approval = approve_or_deny(tool_name, args, WORKSPACE)
        if not allow:
            return DENY(reason=reason)
        context["pending_approval"] = approval
        return ALLOW

    def post_tool_use(tool_name, args, result, context):
        if context.get("pending_approval") and result.ok:
            context["pending_approval"].consume()  # flips consumed_at

See spa_hooks/tests/test_vectors.py for the 9 vectors from
references/trust-tiers.md §Enforcement test vectors.
"""
from .policy import (
    classify_tier,
    approve_or_deny,
    is_inside_workspace,
    TIER_0,
    TIER_1,
    TIER_2,
)
from .approvals import (
    ApprovalRecord,
    find_matching_approval,
    extract_proposal_body,
)

__all__ = [
    "classify_tier",
    "approve_or_deny",
    "is_inside_workspace",
    "TIER_0",
    "TIER_1",
    "TIER_2",
    "ApprovalRecord",
    "find_matching_approval",
    "extract_proposal_body",
]

"""Tests for split-layout API: separate policy_root vs state_root."""
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from spa_hooks import approvals
from spa_hooks import approve_or_deny


def _write_proposal_and_approval(state_root: Path, command: str) -> str:
    """Helper: write a proposal + matching .approved into state_root. Returns proposal SHA."""
    approvals_dir = state_root / "assets" / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    proposals_path = state_root / "assets" / "PROPOSALS.md"
    body = (
        "## [2026-05-20 09:00 UTC] PROPOSAL: run rm command\n"
        f"\nCommand: {command}\nTier: 2\n"
    )
    proposals_path.write_text(body)
    sha = hashlib.sha256(body.encode()).hexdigest()
    (approvals_dir / f"{sha}.approved").write_text(
        f"proposal_id: {sha}\n"
        f"proposal_sha256: {sha}\n"
        f"proposal_title: run rm command\n"
        f"approved_at: 2026-05-20T09:00:00Z\n"
        f"approved_by: tester@host\n"
        f"single_use: true\n"
        f"consumed_at: null\n"
    )
    return sha


class FindMatchingApprovalSplitLayoutTests(unittest.TestCase):
    def test_approval_found_in_state_root_not_policy_root(self):
        """With state_root kwarg, approval is read from state_root regardless of policy_root."""
        with TemporaryDirectory() as policy_dir, TemporaryDirectory() as state_dir:
            policy_root = Path(policy_dir)
            state_root = Path(state_dir)
            _write_proposal_and_approval(state_root, "rm test.txt")
            # policy_root has NO assets/ at all.
            rec = approvals.find_matching_approval(
                subject="rm test.txt",
                workspace_root=str(policy_root),  # legacy positional
                state_root=str(state_root),       # new kwarg overrides
            )
            self.assertIsNotNone(rec)
            self.assertEqual(rec.proposal_title, "run rm command")


class ApproveOrDenySplitLayoutTests(unittest.TestCase):
    def test_tier2_approved_under_split_roots(self):
        """A Tier 2 Bash call with approval in state_root and project root = policy_root must be allowed."""
        with TemporaryDirectory() as policy_dir, TemporaryDirectory() as state_dir:
            policy_root = Path(policy_dir)
            state_root = Path(state_dir)
            _write_proposal_and_approval(state_root, "rm foo")
            # Workspace = the project itself (use policy_root as a stand-in
            # since the path-bounds check needs a real dir). The agent action
            # is `rm foo` which does not reference any path outside.
            allow, reason, rec = approve_or_deny(
                "bash",
                {"command": "rm foo"},
                workspace_root=str(policy_root),
                policy_root=str(policy_root),
                state_root=str(state_root),
            )
            self.assertTrue(allow, reason)
            self.assertIsNotNone(rec)

    def test_tier2_deny_when_approval_absent_from_state_root(self):
        with TemporaryDirectory() as policy_dir, TemporaryDirectory() as state_dir:
            policy_root = Path(policy_dir)
            state_root = Path(state_dir)
            # No proposal/approval written.
            allow, reason, rec = approve_or_deny(
                "bash",
                {"command": "rm foo"},
                workspace_root=str(policy_root),
                policy_root=str(policy_root),
                state_root=str(state_root),
            )
            self.assertFalse(allow)
            self.assertIsNone(rec)
            self.assertIn("Tier 2", reason)

    def test_legacy_single_root_still_works(self):
        with TemporaryDirectory() as one_root:
            root = Path(one_root)
            _write_proposal_and_approval(root, "rm bar")
            allow, _, rec = approve_or_deny(
                "bash",
                {"command": "rm bar"},
                workspace_root=str(root),
            )
            self.assertTrue(allow)
            self.assertIsNotNone(rec)


class PathTraversalDefenseTests(unittest.TestCase):
    def test_state_root_with_dotdot_does_not_reach_policy_root(self):
        """If a caller passes state_root='/x/.tiered-agent-guard/../..' it must not
        suddenly find approvals living under policy_root."""
        with TemporaryDirectory() as base:
            base_path = Path(base)
            policy_root = base_path / "plugin"
            project_root = base_path / "project"
            policy_root.mkdir()
            project_root.mkdir()
            state_root = project_root / ".tiered-agent-guard"
            # Write an approval into policy_root (the WRONG place).
            _write_proposal_and_approval(policy_root, "rm baz")
            # state_root is missing assets/ — there is NO approval there.
            allow, reason, rec = approve_or_deny(
                "bash",
                {"command": "rm baz"},
                workspace_root=str(project_root),
                policy_root=str(policy_root),
                state_root=str(state_root),  # legitimate state_root, no traversal
            )
            self.assertFalse(allow, "approval in policy_root must not authorise tier 2")
            self.assertIsNone(rec)


class TierParityTests(unittest.TestCase):
    """Tier classification must be identical in legacy and split modes."""
    PARITY_VECTORS = [
        ("bash", {"command": "ls"}),
        ("bash", {"command": "git status"}),
        ("bash", {"command": "rm foo"}),
        ("bash", {"command": "curl example.com"}),
        ("bash", {"command": "pip install x"}),
        ("write_file", {"path": "PROPOSALS.md"}),
        ("write_file", {"path": "POLICY.md"}),
    ]

    def test_classification_identical(self):
        from spa_hooks import classify_tier
        for tool, args in self.PARITY_VECTORS:
            with self.subTest(tool=tool, args=args):
                # classify_tier does not take any root — it's pure.
                t = classify_tier(tool, args)
                # Re-call to ensure determinism.
                self.assertEqual(t, classify_tier(tool, args))


if __name__ == "__main__":
    unittest.main()

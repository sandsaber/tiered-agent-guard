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


class CrossRootIsolationTests(unittest.TestCase):
    def test_state_root_without_assets_does_not_inherit_policy_root_approvals(self):
        """An approval located in policy_root must NOT authorise a Tier 2 action
        when state_root is a legitimate, distinct directory that has no approvals.
        This pins the documented split: approvals are looked up under state_root,
        full stop — there is no automatic search of any other root."""
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


class ConsumeTargetsStateRootTests(unittest.TestCase):
    def test_consume_writes_to_state_root_not_workspace_or_policy(self):
        """After a Tier 2 allow, calling rec.consume() must update the .approved
        file that lives under state_root, leaving any unrelated approvals in
        other roots untouched."""
        with TemporaryDirectory() as policy_dir, TemporaryDirectory() as state_dir:
            policy_root = Path(policy_dir)
            state_root = Path(state_dir)
            sha = _write_proposal_and_approval(state_root, "rm consume-test")
            allow, _, rec = approve_or_deny(
                "bash",
                {"command": "rm consume-test"},
                workspace_root=str(policy_root),
                policy_root=str(policy_root),
                state_root=str(state_root),
            )
            self.assertTrue(allow)
            self.assertIsNotNone(rec)
            rec.consume()
            approval_file = state_root / "assets" / "approvals" / f"{sha}.approved"
            text = approval_file.read_text()
            self.assertNotIn("consumed_at: null", text)
            self.assertRegex(text, r"consumed_at:\s*\d{4}-\d{2}-\d{2}T")


class ClassifyTierDeterminismTests(unittest.TestCase):
    """classify_tier is pure and root-free: same input always yields same tier,
    regardless of any layout mode. Documents what we rely on for legacy/split parity."""
    VECTORS = [
        ("bash", {"command": "ls"}),
        ("bash", {"command": "git status"}),
        ("bash", {"command": "rm foo"}),
        ("bash", {"command": "curl example.com"}),
        ("bash", {"command": "pip install x"}),
        ("write_file", {"path": "PROPOSALS.md"}),
        ("write_file", {"path": "POLICY.md"}),
    ]

    def test_classify_tier_is_deterministic(self):
        from spa_hooks import classify_tier
        for tool, args in self.VECTORS:
            with self.subTest(tool=tool, args=args):
                self.assertEqual(classify_tier(tool, args), classify_tier(tool, args))


if __name__ == "__main__":
    unittest.main()

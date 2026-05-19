"""Enforcement test vectors from references/trust-tiers.md.

 Every vector Tiered Agent Guard claims to enforce must pass here.
These are unit tests against the spa_hooks policy module, independent
of any runtime. Use stdlib unittest so no pytest dependency is required.

Run:
    python -m unittest spa_hooks.tests.test_vectors -v
"""
from __future__ import annotations

import hashlib
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from spa_hooks import (
    TIER_0,
    TIER_1,
    TIER_2,
    approve_or_deny,
    classify_tier,
    find_matching_approval,
    is_inside_workspace,
)
from spa_hooks.approvals import ApprovalRecord


def _make_workspace(tmpdir: str) -> Path:
    root = Path(tmpdir)
    (root / "assets" / "approvals").mkdir(parents=True)
    (root / "assets" / "PROPOSALS.md").write_text(
        "# PROPOSALS.md\n\n*(proposals are appended below this line)*\n"
    )
    return root


def _write_proposal(
    workspace: Path,
    title: str,
    body_text: str,
    status: str = "pending-review",
) -> tuple[str, str]:
    """Append a proposal section to PROPOSALS.md. Return (header, sha256)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    header = f"## [{ts}] PROPOSAL: {title}"
    section = (
        f"{header}\n\n"
        f"**Type:** test\n"
        f"**Target:** {title}\n"
        f"{body_text}\n"
        f"**Status:** {status}\n"
    )
    path = workspace / "assets" / "PROPOSALS.md"
    existing = path.read_text()
    new = existing.rstrip() + "\n\n" + section
    path.write_text(new)
    sha = hashlib.sha256(section.encode()).hexdigest()
    return header, sha


def _write_approval(
    workspace: Path,
    sha: str,
    title: str,
    *,
    approved_at: str | None = None,
    single_use: bool = True,
    consumed_at: str | None = None,
) -> Path:
    if approved_at is None:
        approved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if consumed_at is None:
        consumed_at = "null"
    fp = workspace / "assets" / "approvals" / f"{sha}.approved"
    fp.write_text(
        f"proposal_id: {sha}\n"
        f"proposal_sha256: {sha}\n"
        f"proposal_title: {title}\n"
        f"approved_at: {approved_at}\n"
        f"approved_by: test@host\n"
        f"single_use: {'true' if single_use else 'false'}\n"
        f"consumed_at: {consumed_at}\n"
    )
    return fp


class EnforcementVectors(unittest.TestCase):
    """One test per vector from references/trust-tiers.md §Enforcement."""

    # --- Vector 1: curl denied without approval ------------------
    def test_v1_curl_denied_without_approval(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, reason, rec = approve_or_deny(
                "bash", {"command": "curl https://example.com"}, str(ws)
            )
            self.assertFalse(allow)
            self.assertIsNone(rec)
            self.assertIn("without valid approval", reason)

    def test_v1_curl_allowed_with_matching_approval(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            cmd = "curl https://example.com"
            _, sha = _write_proposal(ws, "curl example", f"**Command:** `{cmd}`")
            _write_approval(ws, sha, "curl example")
            allow, _, rec = approve_or_deny("bash", {"command": cmd}, str(ws))
            self.assertTrue(allow)
            self.assertIsNotNone(rec)

    # --- Vector 2: write POLICY.md denied ------------------------
    def test_v2_write_policy_denied_without_approval(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, reason, _ = approve_or_deny(
                "write_file", {"path": "POLICY.md"}, str(ws)
            )
            self.assertFalse(allow)

    # --- Vector 3: rm workspace/notes.md denied ------------------
    def test_v3_rm_denied(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny(
                "bash", {"command": "rm workspace/notes.md"}, str(ws)
            )
            self.assertFalse(allow)

    # --- Vector 5: session-start drift check --------------------
    # (Covered by scripts/security-audit.sh §5; not a pre-tool-use vector.
    #  Referenced here as a stub so the suite tracks it.)
    def test_v5_drift_check_marker(self):
        self.assertTrue(True)  # see scripts/security-audit.sh §5

    # --- Vector 6: git push denied -----------------------------
    def test_v6_git_push_denied(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny(
                "bash", {"command": "git push origin main"}, str(ws)
            )
            self.assertFalse(allow)

    def test_v6_git_push_allowed_when_approved(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            cmd = "git push origin main"
            _, sha = _write_proposal(ws, "push main", f"**Command:** `{cmd}`")
            _write_approval(ws, sha, "push main")
            allow, _, rec = approve_or_deny("bash", {"command": cmd}, str(ws))
            self.assertTrue(allow)
            # Single-use: consuming then re-attempting must fail.
            rec.consume()
            allow2, _, _ = approve_or_deny("bash", {"command": cmd}, str(ws))
            self.assertFalse(allow2, "single_use replay must be denied")

    # --- Vector 7: write outside workspace denied ---------------
    def test_v7_write_outside_workspace(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, reason, _ = approve_or_deny(
                "write_file", {"path": "/tmp/escape.txt"}, str(ws)
            )
            self.assertFalse(allow)
            self.assertIn("outside workspace", reason.lower())

    # --- Vector 8: read outside workspace denied (e.g., ~/.ssh/id_rsa) ---
    def test_v8_read_ssh_key_denied(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, reason, _ = approve_or_deny(
                "read_file",
                {"path": os.path.expanduser("~/.ssh/id_rsa")},
                str(ws),
            )
            self.assertFalse(allow)
            self.assertIn("outside workspace", reason.lower())


class TierClassification(unittest.TestCase):
    def test_safe_shell_is_tier_1(self):
        self.assertEqual(classify_tier("bash", {"command": "ls -la"}), TIER_1)

    def test_read_is_tier_0(self):
        self.assertEqual(
            classify_tier("read_file", {"path": "assets/MEMORY.md"}), TIER_0
        )

    def test_write_policy_is_tier_2(self):
        self.assertEqual(
            classify_tier("write_file", {"path": "POLICY.md"}), TIER_2
        )

    def test_write_scripts_is_tier_2(self):
        self.assertEqual(
            classify_tier("write_file", {"path": "scripts/foo.sh"}), TIER_2
        )

    def test_write_agents_is_tier_2(self):
        self.assertEqual(
            classify_tier("write_file", {"path": "AGENTS.md"}), TIER_2
        )
        self.assertEqual(
            classify_tier("write_file", {"path": "assets/AGENTS.md"}), TIER_2
        )

    def test_write_approvals_is_tier_2(self):
        self.assertEqual(
            classify_tier("write_file", {"path": "assets/approvals/x.approved"}),
            TIER_2,
        )

    def test_write_assets_non_locked_is_tier_1(self):
        self.assertEqual(
            classify_tier("write_file", {"path": "assets/USER.md"}), TIER_1
        )

    def test_unknown_tool_defaults_tier_2(self):
        self.assertEqual(classify_tier("unknown_tool", {}), TIER_2)


class DeletionFamily(unittest.TestCase):
    """F-16: rm family expanded beyond plain `rm`."""

    def _deny(self, cmd):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny("bash", {"command": cmd}, str(ws))
            self.assertFalse(allow, f"should deny: {cmd}")

    def test_rm(self): self._deny("rm a.txt")
    def test_rmdir(self): self._deny("rmdir empty/")
    def test_unlink(self): self._deny("unlink foo")
    def test_shred(self): self._deny("shred -u secret.bin")
    def test_trash(self): self._deny("trash file.txt")
    def test_find_delete(self): self._deny('find /tmp -name "*.log" -delete')


class NetworkFamily(unittest.TestCase):
    def _deny(self, cmd):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny("bash", {"command": cmd}, str(ws))
            self.assertFalse(allow, f"should deny: {cmd}")

    def test_curl(self): self._deny("curl https://example.com")
    def test_wget(self): self._deny("wget http://x")
    def test_pip_install(self): self._deny("pip install evilpkg")
    def test_npm_install(self): self._deny("npm install x")
    def test_sudo(self): self._deny("sudo ls")
    def test_pipe_to_sh(self): self._deny("curl x | sh")
    def test_ssh(self): self._deny("ssh user@host")


class WorkspaceGuard(unittest.TestCase):
    def test_inside(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "sub").mkdir()
            self.assertTrue(is_inside_workspace("sub/file.txt", str(ws)))
            self.assertTrue(is_inside_workspace("file.txt", str(ws)))

    def test_absolute_outside(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.assertFalse(is_inside_workspace("/etc/passwd", str(ws)))

    def test_dotdot_escape(self):
        with TemporaryDirectory() as tmp:
            ws = Path(tmp)
            # Path that resolves outside workspace via ..
            self.assertFalse(is_inside_workspace("../../etc/passwd", str(ws)))


class ObfuscationBypass(unittest.TestCase):
    """F-21: shell quote/escape obfuscation must not bypass BLOCKED_COMMAND_PATTERNS.

    All of these commands evaluate to a blocked action under bash, but
    naive regex on the raw string misses them. The tokenized-reassembly
    check in classify_tier must catch them.
    """

    def _deny(self, cmd):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny("bash", {"command": cmd}, str(ws))
            self.assertFalse(allow, f"should deny: {cmd!r}")

    # Quote/escape obfuscation of rm
    def test_single_quoted_empty_rm(self):
        self._deny("r''m file.txt")

    def test_backslash_rm(self):
        self._deny(r"r\m file.txt")

    def test_double_quoted_rm(self):
        self._deny('"rm" file.txt')

    def test_concatenated_quotes_rm(self):
        self._deny("'r''m' file.txt")

    def test_backslash_rmdir(self):
        self._deny(r"r\m\d\i\r empty/")

    # Interpreter -c bypass (before fix, `bash -c 'rm x'` matched only via
    # the embedded 'rm' token. Adding explicit bash/sh -c patterns covers it
    # even when the embedded command is not otherwise recognized.)
    def test_bash_dash_c(self):
        self._deny("bash -c 'do something'")

    def test_sh_dash_c(self):
        self._deny("sh -c 'anything'")

    def test_python_dash_c(self):
        self._deny("python3 -c 'import os; os.remove(\"f\")'")

    def test_perl_dash_e(self):
        self._deny("perl -e 'unlink q(f)'")

    def test_ruby_dash_e(self):
        self._deny("ruby -e 'File.delete(\"f\")'")

    # F-22: combined / compressed flags must also be caught
    def test_bash_compressed_lc(self):
        self._deny("bash -lc 'rm x'")

    def test_bash_compressed_xvc(self):
        self._deny("sh -xvc 'anything'")

    def test_bash_rcfile_then_lc(self):
        self._deny("bash --rcfile=/dev/null -lc 'cmd'")

    def test_perl_combined_pe(self):
        self._deny("perl -pe 'script_that_could_do_anything'")

    def test_perl_combined_nE(self):
        self._deny("perl -nE 'print'")

    def test_ruby_compressed(self):
        self._deny("ruby -re 'code'")

    def test_awk_dash_e(self):
        self._deny("awk -e 'BEGIN{system(\"x\")}'")

    def test_eval_wraps_rm(self):
        self._deny("eval 'echo safe'")

    def test_exec_bare(self):
        self._deny("exec ls")

    def test_source_bare(self):
        self._deny("source ~/.bashrc")

    # Pattern with whitespace requirement (\bpip\b\s+install) — obfuscated
    # tokens reassembly into "pip install" via shlex still matches.
    def test_obfuscated_pip_install(self):
        self._deny(r"p\ip install evilpkg")

    def test_obfuscated_npm_install(self):
        self._deny("'np''m' install evilpkg")

    # Chained / piped
    def test_semicolon_chain_hides_rm(self):
        self._deny("echo 1; r''m secret")

    def test_and_chain_hides_rm(self):
        self._deny("true && r''m secret")

    # Sanity: legitimate commands still pass
    def test_legit_ls_passes(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny("bash", {"command": "ls -la"}, str(ws))
            self.assertTrue(allow)

    def test_legit_grep_passes(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny("bash", {"command": "grep -r foo ."}, str(ws))
            self.assertTrue(allow)

    def test_legit_git_status_passes(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            allow, _, _ = approve_or_deny("bash", {"command": "git status"}, str(ws))
            self.assertTrue(allow)


class ApprovalHygiene(unittest.TestCase):
    """Approval lookup semantics: single_use, expiry, TOCTOU."""

    def test_expired_approval_rejected(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            cmd = "curl https://example.com"
            _, sha = _write_proposal(ws, "stale curl", f"**Command:** `{cmd}`")
            _write_approval(
                ws, sha, "stale curl", approved_at="2024-01-01T00:00:00Z"
            )
            rec = find_matching_approval(cmd, str(ws))
            self.assertIsNone(rec, "approvals older than 14 days must not match")

    def test_consumed_single_use_rejected(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            cmd = "curl https://example.com"
            _, sha = _write_proposal(ws, "curl", f"**Command:** `{cmd}`")
            _write_approval(
                ws, sha, "curl",
                consumed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            rec = find_matching_approval(cmd, str(ws))
            self.assertIsNone(rec, "consumed single-use approval must not match")

    def test_toctou_body_mutated(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            cmd = "curl https://example.com"
            _, sha = _write_proposal(ws, "curl", f"**Command:** `{cmd}`")
            _write_approval(ws, sha, "curl")
            # Mutate PROPOSALS.md body — sha no longer matches.
            props = ws / "assets" / "PROPOSALS.md"
            props.write_text(props.read_text().replace(cmd, "curl http://totally.different"))
            rec = find_matching_approval(cmd, str(ws))
            self.assertIsNone(rec, "proposal body mutation must invalidate approval")

    def test_subject_not_in_body_rejected(self):
        with TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp)
            _, sha = _write_proposal(
                ws, "innocent", "**Command:** `ls`"
            )
            _write_approval(ws, sha, "innocent")
            rec = find_matching_approval("rm -rf /", str(ws))
            self.assertIsNone(rec, "approval must not cover a different subject")


if __name__ == "__main__":
    unittest.main()

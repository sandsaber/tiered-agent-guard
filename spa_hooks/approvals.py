"""Approval record loading and proposal body matching.

Mirrors the file format written by scripts/approve-proposal.sh.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

APPROVAL_MAX_AGE_DAYS = 14


@dataclass
class ApprovalRecord:
    proposal_id: str
    proposal_sha256: str
    proposal_title: str
    approved_at: str
    approved_by: str
    single_use: bool
    consumed_at: Optional[str]
    path: Optional[Path] = field(default=None)

    @classmethod
    def from_file(cls, path: Path) -> "ApprovalRecord":
        kv: dict = {}
        for line in path.read_text().splitlines():
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            kv[k.strip()] = v.strip()
        consumed_raw = kv.get("consumed_at", "null")
        consumed = None if consumed_raw in ("null", "", "None") else consumed_raw
        return cls(
            proposal_id=kv.get("proposal_id", ""),
            proposal_sha256=kv.get("proposal_sha256", ""),
            proposal_title=kv.get("proposal_title", ""),
            approved_at=kv.get("approved_at", ""),
            approved_by=kv.get("approved_by", ""),
            single_use=kv.get("single_use", "false").lower() == "true",
            consumed_at=consumed,
            path=path,
        )

    def consume(self, now_iso: Optional[str] = None) -> None:
        """Flip consumed_at. Called by the executor after a successful run."""
        if self.path is None:
            raise ValueError("ApprovalRecord has no path; cannot consume")
        now_iso = now_iso or _utc_now()
        text = self.path.read_text()
        new_text = re.sub(
            r"^consumed_at:\s*.*$",
            f"consumed_at: {now_iso}",
            text,
            count=1,
            flags=re.M,
        )
        self.path.write_text(new_text)
        self.consumed_at = now_iso


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _older_than_days(iso: str, days: int, now_iso: Optional[str] = None) -> bool:
    try:
        when = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return True
    current = datetime.fromisoformat((now_iso or _utc_now()).replace("Z", "+00:00"))
    return (current - when).days > days


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_proposal_body(proposals_text: str, proposal_sha: str) -> Optional[str]:
    """Return the proposal block whose sha256 matches proposal_sha, or None."""
    pat = re.compile(r"^## \[[0-9]{4}-[0-9]{2}-[0-9]{2}.*PROPOSAL:.*$", re.M)
    starts = [m.start() for m in pat.finditer(proposals_text)]
    if not starts:
        return None
    starts.append(len(proposals_text))
    for i in range(len(starts) - 1):
        body = proposals_text[starts[i]:starts[i + 1]]
        if _sha256(body.encode()) == proposal_sha:
            return body
    return None


def find_matching_approval(
    subject: str,
    workspace_root: str,
    now_iso: Optional[str] = None,
    *,
    state_root: Optional[str] = None,
) -> Optional[ApprovalRecord]:
    """Locate a valid, unconsumed approval whose proposal body mentions subject.

    If state_root is provided, approvals/ and PROPOSALS.md are read from there
    (split-layout mode). Otherwise workspace_root is used for both (legacy).
    """
    root = Path(state_root) if state_root is not None else Path(workspace_root)
    approvals_dir = root / "assets" / "approvals"
    proposals_path = root / "assets" / "PROPOSALS.md"
    if not approvals_dir.is_dir() or not proposals_path.exists():
        return None
    proposals_text = proposals_path.read_text()

    for approval_file in sorted(approvals_dir.glob("*.approved")):
        rec = ApprovalRecord.from_file(approval_file)
        if rec.single_use and rec.consumed_at is not None:
            continue
        if _older_than_days(rec.approved_at, APPROVAL_MAX_AGE_DAYS, now_iso):
            continue
        body = extract_proposal_body(proposals_text, rec.proposal_sha256)
        if body is None:
            continue
        if subject not in body:
            continue
        return rec
    return None

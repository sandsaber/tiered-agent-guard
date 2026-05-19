"""Tier classification and approval decision logic."""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import List, Optional, Tuple

from .approvals import ApprovalRecord, find_matching_approval

TIER_0 = 0  # ambient — read, draft, think in-workspace
TIER_1 = 1  # logged + reversible
TIER_2 = 2  # approval required

# Tier 2 command patterns — mirror references/trust-tiers.md.
# Any match forces tier 2, requiring a matching approval artefact.
# Patterns are checked against BOTH the raw command AND the shlex-joined
# reassembly of its tokens, so obfuscation like `r''m` or `p\ip install`
# cannot bypass them (F-21).
BLOCKED_COMMAND_PATTERNS: Tuple[str, ...] = (
    # Network
    r"\bcurl\b",
    r"\bwget\b",
    r"\bssh\b",
    r"\bscp\b",
    r"\brsync\b",
    r"\bnc\b",
    r"\bnetcat\b",
    r"\btelnet\b",
    # Package install
    r"\bpip\b\s+install",
    r"\bnpm\b\s+install",
    r"\byarn\b\s+add",
    r"\bbrew\b\s+install",
    r"\bapt\b\s+install",
    r"\bapt-get\b\s+install",
    # Privilege
    r"\bsudo\b",
    # Pipe-to-shell
    r"\|\s*sh\b",
    r"\|\s*bash\b",
    # Git write
    r"\bgit\b\s+push",
    # Deletion family (F-16)
    r"\b(?:rm|rmdir|unlink|shred|trash)\b",
    r"-delete\b",
    # Code-execution surface (F-21, F-22).
    # Interpreter patterns use [^|;&\n]*? between command and flag so they
    # catch compressed/combined flags like `bash -lc`, `perl -pe`, and
    # intermediate flags like `bash --rcfile=/x -lc`. `[a-zA-Z]*[flag-letter]`
    # matches the exec/code flag even when fused with other flag letters.
    r"\beval\b",
    r"\bexec\b",
    r"\bsource\b",
    r"\b(?:bash|sh|zsh|dash|ksh)\b[^|;&\n]*?\s-[a-zA-Z]*c\b",
    r"\b(?:python|python2|python3)\b[^|;&\n]*?\s-[a-zA-Z]*c\b",
    r"\bperl\b[^|;&\n]*?\s-[a-zA-Z]*[eE]\b",
    r"\bruby\b[^|;&\n]*?\s-[a-zA-Z]*e\b",
    r"\bnode\b[^|;&\n]*?\s-[a-zA-Z]*e\b",
    r"\bawk\b[^|;&\n]*?\s-[a-zA-Z]*e\b",
)

LOCKED_WRITE_SUFFIXES: Tuple[str, ...] = (
    "POLICY.md",
    "SOUL.md",
    "SKILL.md",
    "AGENTS.md",
)
LOCKED_WRITE_PREFIXES: Tuple[str, ...] = (
    "scripts/",
    "assets/approvals/",
    ".git/hooks/",
)

READ_TOOLS = {"read_file", "list_files", "grep"}
WRITE_TOOLS = {"write_file", "edit_file"}
SHELL_TOOLS = {"bash", "shell", "run_command"}


def _tokenize_command(cmd: str) -> List[str]:
    """Return shell-evaluated tokens from cmd across separators.

    Defeats quote/escape obfuscation (F-21): `r''m`, `r\\m`, `"rm"` all
    collapse to the token `rm` under shlex, so pattern matching on the
    joined token string catches what raw-regex misses.

    Splits first on shell control chars (|, ;, &) so each sub-command is
    tokenized independently. Falls back to whitespace split on malformed
    quoting.
    """
    parts = re.split(r"[|;&]+", cmd)
    tokens: List[str] = []
    for part in parts:
        try:
            tokens.extend(shlex.split(part, posix=True))
        except ValueError:
            tokens.extend(part.split())
    return tokens


def classify_tier(tool_name: str, args: dict) -> int:
    """Map (tool, args) to a tier. Default Tier 2 when in doubt (PD-6)."""
    if tool_name in SHELL_TOOLS:
        cmd = args.get("command", "")
        joined_tokens = " ".join(_tokenize_command(cmd))
        for pat in BLOCKED_COMMAND_PATTERNS:
            if re.search(pat, cmd) or re.search(pat, joined_tokens):
                return TIER_2
        return TIER_1
    if tool_name in WRITE_TOOLS:
        path = args.get("path", "")
        if _is_locked_path(path):
            return TIER_2
        return TIER_1
    if tool_name in READ_TOOLS:
        return TIER_0
    return TIER_2


def _is_locked_path(path: str) -> bool:
    norm = path.replace("\\", "/")
    for suf in LOCKED_WRITE_SUFFIXES:
        if norm == suf or norm.endswith("/" + suf):
            return True
    for pre in LOCKED_WRITE_PREFIXES:
        if norm.startswith(pre):
            return True
    return False


def is_inside_workspace(path: str, workspace_root: str) -> bool:
    """Return True if path resolves to a location inside workspace_root."""
    wsp = Path(workspace_root).resolve()
    candidate = Path(path) if os.path.isabs(path) else wsp / path
    try:
        candidate.resolve().relative_to(wsp)
        return True
    except ValueError:
        return False


def approve_or_deny(
    tool_name: str,
    args: dict,
    workspace_root: str,
) -> Tuple[bool, str, Optional[ApprovalRecord]]:
    """Decide whether to allow a tool call.

    Returns:
        (allow, reason, approval): approval is non-None only on a Tier 2
        allow, and the caller is responsible for calling approval.consume()
        after a successful execution.
    """
    if tool_name in READ_TOOLS | WRITE_TOOLS:
        path = args.get("path", "")
        if path and not is_inside_workspace(path, workspace_root):
            return (False, f"path outside workspace: {path}", None)

    tier = classify_tier(tool_name, args)
    if tier == TIER_0:
        return (True, "Tier 0 ambient", None)
    if tier == TIER_1:
        return (True, "Tier 1 logged", None)

    if tool_name in SHELL_TOOLS:
        subject = args.get("command", "")
    elif tool_name in WRITE_TOOLS:
        subject = f"write {args.get('path', '')}"
    else:
        subject = tool_name

    rec = find_matching_approval(subject, workspace_root)
    if rec is None:
        return (False, f"Tier 2 {tool_name} without valid approval: {subject}", None)
    return (True, "Tier 2 with valid approval", rec)

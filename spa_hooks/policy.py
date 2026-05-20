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

SIMPLE_TIER1_COMMANDS = {
    "ls",
    "stat",
    "file",
    "wc",
    "head",
    "tail",
    "cat",
    "less",
    "cut",
    "awk",
    "grep",
    "rg",
    "fd",
    "tree",
    "column",
    "sort",
    "uniq",
    "tr",
    "date",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "diff",
    "comm",
    "md5sum",
    "sha256sum",
    "pwd",
    "whoami",
    "pytest",
    "jest",
    "vitest",
    "mocha",
    "mypy",
    "pylint",
    "shellcheck",
}

PROJECT_SCRIPT_COMMANDS = {
    "./scripts/security-audit.sh",
    "scripts/security-audit.sh",
    "./scripts/verify-policy.sh",
    "scripts/verify-policy.sh",
    "./scripts/audit-log-append.sh",
    "scripts/audit-log-append.sh",
    "./scripts/injection-scan.sh",
    "scripts/injection-scan.sh",
}

GIT_TIER1_SUBCOMMANDS = {
    "status",
    "log",
    "show",
    "diff",
    "blame",
    "rev-parse",
    "shortlog",
    "reflog",
}

SECRET_PATH_MARKERS = (
    ".credentials",
    ".ssh",
    ".aws",
    ".kube",
    ".config/gcloud",
    ".env",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".docker",
    ".gnupg",
    ".git-credentials",
    ".pgpass",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "serviceaccountkey.json",
    "secrets.yml",
    "secrets.yaml",
)


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


def _command_segments(cmd: str) -> List[List[str]]:
    segments: List[List[str]] = []
    for part in re.split(r"[|;&]+", cmd):
        if not part.strip():
            continue
        try:
            tokens = shlex.split(part, posix=True)
        except ValueError:
            tokens = part.split()
        if tokens:
            segments.append(tokens)
    return segments


def _has_redirection(tokens: List[str]) -> bool:
    for token in tokens:
        if token in {">", ">>", "<", "<<", "<>", "&>"}:
            return True
        if re.match(r"^[0-9]*(?:>>?|<<?|&>)", token):
            return True
    return False


def _is_filtered_env_pipeline(segments: List[List[str]]) -> bool:
    if len(segments) != 2:
        return False
    first, second = segments
    if first != ["env"] or not second or second[0] != "grep":
        return False
    joined = " ".join(second[1:]).lower()
    if "-ive" not in joined.replace(" ", ""):
        return False
    return any(
        word in joined
        for word in (
            "token",
            "key",
            "secret",
            "pass",
            "credential",
            "auth",
            "bearer",
            "session",
            "cookie",
            "private",
            "cert",
            "oauth",
            "refresh",
        )
    )


def _git_command_is_allowlisted(tokens: List[str]) -> bool:
    if len(tokens) < 2:
        return False
    subcommand = tokens[1]
    if subcommand in GIT_TIER1_SUBCOMMANDS:
        return True
    if subcommand == "branch":
        return "--list" in tokens[2:]
    if subcommand == "remote":
        return tokens[2:] == ["-v"]
    if subcommand == "config":
        return len(tokens) >= 4 and tokens[2] == "--get"
    if subcommand == "stash":
        return tokens[2:] == ["list"]
    if subcommand == "worktree":
        return tokens[2:] == ["list"]
    return False


def _shell_segment_is_allowlisted(tokens: List[str]) -> bool:
    if not tokens or _has_redirection(tokens):
        return False

    command = tokens[0]
    if (
        "/" in command
        and command not in PROJECT_SCRIPT_COMMANDS
        and command != "./gradlew"
    ):
        return False

    if command in PROJECT_SCRIPT_COMMANDS:
        return True
    if command in {"./scripts/approve-proposal.sh", "scripts/approve-proposal.sh"}:
        return False
    if command in SIMPLE_TIER1_COMMANDS:
        return True
    if command == "sed":
        return len(tokens) >= 2 and tokens[1] == "-n"
    if command == "find":
        return "-type" in tokens and "f" in tokens and "-exec" not in tokens
    if command == "git":
        return _git_command_is_allowlisted(tokens)
    if command in {"go", "cargo", "mvn"}:
        return len(tokens) >= 2 and tokens[1] == "test"
    if command in {"python", "python3"}:
        return len(tokens) >= 3 and tokens[1:3] == ["-m", "unittest"]
    if command == "./gradlew":
        return len(tokens) >= 2 and tokens[1] == "test"
    if command == "make":
        return True
    if command == "tsc":
        return "--noEmit" in tokens[1:]
    if command == "ruff":
        return "--fix" not in tokens[1:]
    if command == "eslint":
        return "--fix" not in tokens[1:]
    if command == "prettier":
        return "--check" in tokens[1:]
    if command == "gofmt":
        return "-l" in tokens[1:]
    if command in {"mkdir", "cp", "mv", "touch"}:
        if command == "mkdir":
            return "-p" in tokens[1:]
        return len(tokens) >= 2
    return False


def _shell_command_is_allowlisted(cmd: str) -> bool:
    segments = _command_segments(cmd)
    if not segments:
        return False
    if _is_filtered_env_pipeline(segments):
        return True
    return all(_shell_segment_is_allowlisted(segment) for segment in segments)


def _is_path_like_token(token: str) -> bool:
    return token.startswith(("/", "~", ".", "..")) or "/" in token


def _looks_like_secret_path(token: str) -> bool:
    lower = token.lower()
    return any(marker in lower for marker in SECRET_PATH_MARKERS)


def _shell_has_static_path_risk(cmd: str) -> bool:
    for tokens in _command_segments(cmd):
        for token in tokens:
            if token.startswith("-"):
                continue
            if _looks_like_secret_path(token):
                return True
            if token.startswith(("/", "~", "..")) or "/../" in token:
                return True
    return False


def _shell_paths_stay_inside_workspace(cmd: str, workspace_root: str) -> bool:
    for tokens in _command_segments(cmd):
        for token in tokens:
            if token.startswith("-"):
                continue
            if _looks_like_secret_path(token):
                return False
            if _is_path_like_token(token):
                expanded = os.path.expanduser(token)
                if not is_inside_workspace(expanded, workspace_root):
                    return False
    return True


def classify_tier(tool_name: str, args: dict) -> int:
    """Map (tool, args) to a tier. Default Tier 2 when in doubt (PD-6)."""
    if tool_name in SHELL_TOOLS:
        cmd = args.get("command", "")
        joined_tokens = " ".join(_tokenize_command(cmd))
        for pat in BLOCKED_COMMAND_PATTERNS:
            if re.search(pat, cmd) or re.search(pat, joined_tokens):
                return TIER_2
        if _shell_has_static_path_risk(cmd):
            return TIER_2
        if _shell_command_is_allowlisted(cmd):
            return TIER_1
        return TIER_2
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
    *,
    policy_root: Optional[str] = None,
    state_root: Optional[str] = None,
) -> Tuple[bool, str, Optional[ApprovalRecord]]:
    """Decide whether to allow a tool call.

    Path-bounds checks ("inside workspace?") always use workspace_root —
    that is the project root the agent operates in. Approval/proposal
    lookups use state_root when provided (split layout), else fall back
    to workspace_root (legacy single-root mode).

    policy_root is accepted for forward compatibility (future allowlist
    files may load from there); it is unused in this revision.

    Returns:
        (allow, reason, approval): approval is non-None only on a Tier 2
        allow, and the caller is responsible for calling approval.consume()
        after a successful execution.
    """
    if tool_name in READ_TOOLS | WRITE_TOOLS:
        path = args.get("path", "")
        if path and not is_inside_workspace(path, workspace_root):
            return (False, f"path outside workspace: {path}", None)
    if tool_name in SHELL_TOOLS:
        cmd = args.get("command", "")
        if not _shell_paths_stay_inside_workspace(cmd, workspace_root):
            return (
                False,
                f"shell command references path outside workspace or credential path: {cmd}",
                None,
            )

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

    rec = find_matching_approval(
        subject,
        workspace_root,
        state_root=state_root,
    )
    if rec is None:
        return (False, f"Tier 2 {tool_name} without valid approval: {subject}", None)
    return (True, "Tier 2 with valid approval", rec)

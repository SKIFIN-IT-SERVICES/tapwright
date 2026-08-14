# SPDX-License-Identifier: Apache-2.0

"""Guardrail: no security-bypass capability in the tree (C-10, DIAG-08).

Tapwright implements UDS service ``0x27`` (SecurityAccess) request/response
*mechanics* — send a request-seed, send back a key the caller supplies, read the
response. It does not, and will not, ship the part that turns a seed into a key:
no derivation algorithms, no OEM key tables, no brute-force helpers.

That line is a product decision, not squeamishness. A tool that computes keys is
an unlocking tool, and shipping one in a public Apache-2.0 repository puts every
downstream user in a different legal and ethical position than a diagnostic test
runner does. The distinction to hold in mind while reading the patterns below:
**transporting a key the user gives you is fine; producing one is not.**

This scan is a backstop for the rule in AGENTS.md §4, not the rule itself. It
catches the obvious cases; it cannot catch a determined attempt, and it is not
meant to. Its real job is making the boundary visible at the moment someone
crosses it by accident.

    python tools/check_forbidden.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Each pattern pairs with an explanation, because a guardrail that fires without
# saying why teaches nothing and gets worked around.
FORBIDDEN: list[tuple[str, str]] = [
    (
        r"\bseed[\s_-]*(?:to|2)[\s_-]*key\b",
        "seed-to-key derivation — Tapwright transports keys, it does not compute them (C-10)",
    ),
    (
        r"\bdef\s+(?:calculate|compute|derive|generate|solve|crack)_key\b",
        "key derivation function — the caller supplies the key; we only send it (C-10)",
    ),
    (
        r"\bdef\s+key_from_seed\b",
        "key derivation function (C-10)",
    ),
    (
        r"\b(?:KEY_TABLE|SEED_KEY_TABLE|SECURITY_KEYS|KEY_DATABASE)\b",
        "embedded key table — no key databases ship in this repo (C-10)",
    ),
    (
        r"\bbrute[\s_-]*force\b",
        "brute-force helper — out of scope for a diagnostic test runner (C-10)",
    ),
    (
        r"\bkey[\s_-]*space[\s_-]*search\b",
        "key-space search (C-10)",
    ),
    (
        r"\bbypass[\s_-]*(?:security|auth|access)\b",
        "security bypass helper (C-10)",
    ),
    # ADR-003/007: the open/commercial split is a repository boundary. L4/L5
    # code must never land here, even as a stub or an import.
    (
        r"\bfrom\s+tapwright[._](?:security|compliance|fuzz)\b",
        "L4/L5 import — those layers live in a separate repository (ADR-003, ADR-007)",
    ),
]

SCAN_SUFFIXES = {".py", ".pyi", ".md", ".yml", ".yaml", ".toml", ".sh"}

# This file names the patterns it forbids, and so does the contract that
# documents them. Excluding them is not a loophole: the exclusion list is itself
# owned by CODEOWNERS.
SELF_EXEMPT = {
    "tools/check_forbidden.py",
    "AGENTS.md",
    "SECURITY.md",
    "PROCESS.md",
    "LOOPS.md",
    "DEVELOPMENT-PLAN-L0-L3-AGENTIC.md",
    "tests/unit/test_guardrails.py",
}


def tracked_files(repo_root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [repo_root / line for line in out.splitlines() if line]


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """Return (line number, matched text, why it is forbidden) for each hit."""
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, reason in FORBIDDEN:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                hits.append((lineno, match.group(0), reason))
    return hits


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    failures: list[str] = []

    for path in tracked_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        if path.suffix not in SCAN_SUFFIXES or rel in SELF_EXEMPT or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, matched, reason in scan_text(text):
            failures.append(f"  {rel}:{lineno}: {matched!r}\n      {reason}")

    if failures:
        print("Forbidden capability detected (C-10 / ADR-003):\n", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print(
            "\nThis is a hard boundary, not a lint warning. If you believe the "
            "code is legitimate\nand the pattern is over-broad, escalate to a "
            "maintainer — do not edit this scanner\nto make the build pass "
            "(AGENTS.md §4).",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

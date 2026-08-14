# SPDX-License-Identifier: Apache-2.0

"""Blast-radius and fixture-change guardrail (plan §4.5).

Two checks over the changed files in a branch or PR:

**Fixture changes need a trailer.** Any modification under ``fixtures/`` or
``tests/differential/expected/`` must be accompanied by a ``fixture-change:``
trailer in one of the range's commit messages, explaining what was wrong and how
the new value was independently verified. CODEOWNERS supplies the human
approval; this supplies the explanation. Together they make an oracle edit a
deliberate, reviewed, documented act rather than a line in a large diff.

Adding a *new* fixture is normal and needs no trailer — it is changing an
existing one that has to be argued for.

**Declared blast radius is respected.** If the PR body (or ``BLAST_RADIUS``)
declares an allowed file set, changes outside it fail. A loop that wanders
outside its declared scope has usually misunderstood the task; catching it here
is cheaper than catching it in review, and much cheaper than not catching it.

Persistent violations mean the *scopes* are wrong, not that the rule is —
treat a pattern of them as a signal to re-scope, not to relax the check.

    python tools/check_blast_radius.py --base origin/main
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys

PROTECTED_PREFIXES = ("fixtures/", "tests/differential/expected/")

# Paths every loop may touch regardless of its declared radius: the paperwork
# that goes with any change.
ALWAYS_ALLOWED = ("CHANGELOG.md", "LOOPS.md")

TRAILER = "fixture-change:"


def run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def changed_files(base: str) -> list[tuple[str, str]]:
    """Return (status, path) pairs. Status is A(dded), M(odified), D(eleted)..."""
    out = run("git", "diff", "--name-status", f"{base}...HEAD")
    pairs = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        pairs.append((parts[0][0], parts[-1]))
    return pairs


def commit_messages(base: str) -> str:
    return run("git", "log", "--format=%B", f"{base}..HEAD")


def parse_blast_radius(text: str) -> list[str]:
    """Pull `Allowed:` globs out of a SPEC's Blast radius block (plan Appendix A)."""
    match = re.search(r"Allowed:\s*(.+?)(?:\n\s*\n|\nForbidden:|$)", text, re.DOTALL)
    if not match:
        return []
    return [
        pattern.strip().rstrip(",")
        for pattern in re.split(r"[,\n]", match.group(1))
        if pattern.strip().rstrip(",")
    ]


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(
        fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip("*").rstrip("/") + "/")
        for pattern in patterns
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="base ref to diff against")
    args = parser.parse_args()

    errors: list[str] = []

    try:
        changes = changed_files(args.base)
        messages = commit_messages(args.base)
    except subprocess.CalledProcessError as exc:
        print(f"Could not diff against {args.base}: {exc.stderr.strip()}", file=sys.stderr)
        return 1

    modified_protected = [
        path
        for status, path in changes
        if status in {"M", "D", "R"} and path.startswith(PROTECTED_PREFIXES)
    ]

    if modified_protected and TRAILER not in messages.lower():
        errors.append(
            "Existing fixture(s) or expected output(s) were modified without a "
            f"`{TRAILER}` trailer:\n"
            + "\n".join(f"      {path}" for path in modified_protected)
            + "\n\n"
            "    These files are oracles: they decide whether our output is correct, and "
            "they do\n"
            "    not change to accommodate an implementation. A failing differential test "
            "means the\n"
            "    implementation is wrong far more often than the fixture is — and editing "
            "the expected\n"
            "    value doesn't fix the bug, it deletes the only thing that would ever have "
            "caught it.\n\n"
            "    If the fixture really is wrong: escalate, get it confirmed by someone who "
            "didn't write\n"
            "    the code under test, then land the correction as its own commit with a\n"
            f"    `{TRAILER}` trailer recording what was wrong and how the new value was\n"
            "    independently verified. See AGENTS.md §3."
        )

    declared = os.environ.get("BLAST_RADIUS", "")
    patterns = parse_blast_radius(declared) if declared else []
    if patterns:
        allowed = patterns + list(ALWAYS_ALLOWED)
        outside = [path for _, path in changes if not matches_any(path, allowed)]
        if outside:
            errors.append(
                "Files changed outside the declared blast radius:\n"
                + "\n".join(f"      {path}" for path in outside)
                + "\n\n"
                f"    Declared: {', '.join(patterns)}\n\n"
                "    If the work genuinely cannot be done inside this radius, the loop was "
                "scoped wrong.\n"
                "    Escalate and have it re-scoped rather than widening it yourself "
                "(AGENTS.md §6)."
            )

    if errors:
        print("Guardrails failed:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}\n", file=sys.stderr)
        return 1

    print(f"Guardrails passed: {len(changes)} file(s) changed, all within bounds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

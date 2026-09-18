# SPDX-License-Identifier: Apache-2.0

"""Loop telemetry (INF-07, plan §8): the mechanically-derivable subset of
the plan's own metrics table.

Only two of the plan's six INF-07 metrics have a structured record
anywhere in git/GitHub history for any closed loop:

**Escape rate** (defects found after a loop closed, per closed loop) —
counted from issues labeled ``needs-rca`` (this project's own label for a
bug found post-merge, per ``PROCESS.md``'s labels table) against
``LOOPS.md``'s own closed-loop count.

**Fixture-tamper attempts** (guardrail blocks on fixture edits) —
counted from commits carrying a ``fixture-change:`` trailer (the same
convention ``tools/check_blast_radius.py`` already enforces), a proxy for
*confirmed* corrections; a genuinely blocked tampering attempt that never
merged leaves no trace in ``main``'s history to count.

Iterations-to-green, human-touch rate, oracle coverage, and blast-radius
violations are **not** computed here — none has a structured record for
any closed loop, this session's or earlier, and reporting a number for
them would be fabricating data rather than measuring it. See issue #61
for the scoping decision.

    python tools/loop_telemetry.py             # print report
    python tools/loop_telemetry.py --json      # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = "SKIFIN-IT-SERVICES/tapwright"
ESCAPE_RATE_TARGET = 0.2
NOT_COMPUTED = [
    "iterations_to_green",
    "human_touch_rate",
    "oracle_coverage",
    "blast_radius_violations",
]


def closed_loop_count(loops_md: Path) -> int:
    """Parse LOOPS.md's own `**N of M loops closed**` line. Raises rather
    than silently returning 0 if that line's format ever changes — a
    telemetry script reporting a wrong number quietly is worse than one
    that fails loudly.
    """
    text = loops_md.read_text(encoding="utf-8")
    match = re.search(r"\*\*(\d+) of \d+ loops closed\*\*", text)
    if not match:
        raise ValueError(
            f"{loops_md}: could not find a '**N of M loops closed**' line — "
            f"has LOOPS.md's own summary format changed?"
        )
    return int(match.group(1))


def fixture_tamper_attempt_count(repo_dir: Path) -> int:
    """Commits carrying a `fixture-change:` trailer — confirmed
    corrections only; see this module's own docstring for what this
    can't see.

    Matched as its own line (`^fixture-change:`), not a bare substring:
    a commit merely *discussing* the trailer convention in prose (found
    directly while writing this — two of this repo's own commits mention
    `fixture-change:` in explanatory text without actually carrying one)
    would otherwise be miscounted as a real tamper attempt.
    """
    out = subprocess.run(
        ["git", "log", "--all", "--format=%B%x00"],
        capture_output=True,
        text=True,
        check=True,
        cwd=repo_dir,
    ).stdout
    commits = out.split("\x00")
    trailer_line = re.compile(r"^fixture-change:", re.MULTILINE)
    return sum(1 for commit in commits if trailer_line.search(commit))


def needs_rca_issue_count(repo: str = REPO, token: str | None = None) -> int | None:
    """Issues labeled `needs-rca`, via GitHub's search API. Returns `None`
    (never raises) if no token is available or the network call fails —
    a metrics-reporting job must not fail the build over its own
    unavailability.
    """
    token = token if token is not None else os.environ.get("GITHUB_TOKEN")
    if not token:
        return None

    url = f"https://api.github.com/search/issues?q=repo:{repo}+label:needs-rca"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    return payload.get("total_count")


def build_report(repo_dir: Path, token: str | None = None) -> dict[str, Any]:
    closed = closed_loop_count(repo_dir / "LOOPS.md")
    rca_count = needs_rca_issue_count(token=token)
    escape_rate = round(rca_count / closed, 3) if rca_count is not None and closed else None

    return {
        "closed_loops": closed,
        "needs_rca_issues": rca_count,
        "escape_rate": escape_rate,
        "escape_rate_target": ESCAPE_RATE_TARGET,
        "fixture_tamper_attempts": fixture_tamper_attempt_count(repo_dir),
        "not_computed": NOT_COMPUTED,
    }


def format_report(report: dict[str, Any]) -> str:
    rca_count = report["needs_rca_issues"]
    escape_rate = report["escape_rate"]
    lines = [
        f"Closed loops: {report['closed_loops']}",
        f"needs-rca issues: {rca_count if rca_count is not None else 'unavailable'}",
        f"Escape rate: {escape_rate if escape_rate is not None else 'unavailable'} "
        f"(target < {report['escape_rate_target']})",
        f"Fixture-tamper attempts (confirmed corrections only): "
        f"{report['fixture_tamper_attempts']}",
        "Not computed (no structured record exists): " + ", ".join(report["not_computed"]),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    repo_dir = Path(__file__).resolve().parent.parent
    report = build_report(repo_dir)

    print(json.dumps(report, indent=2) if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

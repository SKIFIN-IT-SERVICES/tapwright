# SPDX-License-Identifier: Apache-2.0

"""Coverage ratchet for L0-L2 (INF-02; DECISIONS-RECORD §4, FW-REQ-032).

Floors: **85% line, 75% branch**, on ``hal``, ``buses``, ``dbc_arxml``,
``trace``, and ``diag`` only. No gate on L3 (``runner``, ``report``) — failures
there are loud, a test that doesn't run is obvious, and gating it would buy
nothing but ceremony.

A *ratchet*, not a threshold: the floor may rise and never falls. Coverage that
improves gets locked in, so the next change cannot quietly give it back.

The rule that matters more than the number, from AGENTS.md §5:

    Coverage is not a goal. Assertions are. A test that executes code without
    asserting on its behaviour will be rejected in review regardless of its
    effect on coverage.

A ratchet is easy to satisfy dishonestly — call every function, assert nothing,
watch the number climb. Only review catches that, which is why the human gate
sits above this one rather than being replaced by it. What the ratchet is
actually for is the *unnoticed* drift: a rushed change that leaves an error path
untested, which nobody would have approved deliberately.

    python tools/coverage_ratchet.py coverage.xml
    python tools/coverage_ratchet.py coverage.xml --update    # raise the stored floor
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# L0-L2 only. See module docstring for why L3 is absent.
GATED_PACKAGES = (
    "tapwright.hal",
    "tapwright.buses",
    "tapwright.dbc_arxml",
    "tapwright.trace",
    "tapwright.diag",
)

INITIAL_LINE_FLOOR = 85.0
INITIAL_BRANCH_FLOOR = 75.0

FLOOR_FILE = "coverage-floor.json"


def measure(coverage_xml: Path) -> tuple[float, float, int]:
    """Return (line %, branch %, statements) across the gated packages.

    Coverage.py's XML gives per-package hit/valid counts; we re-aggregate over
    just the gated packages rather than trusting the top-level totals, which
    include L3 and the ratchet deliberately does not.
    """
    root = ET.parse(coverage_xml).getroot()

    lines_valid = lines_covered = 0
    branches_valid = branches_covered = 0

    for package in root.iter("package"):
        name = package.get("name", "")
        # Coverage.py writes dotted or slashed names depending on version.
        normalised = name.replace("/", ".").replace("\\", ".")
        gated = any(normalised == pkg or normalised.startswith(f"{pkg}.") for pkg in GATED_PACKAGES)
        if not gated:
            continue

        for cls in package.iter("class"):
            for line in cls.iter("line"):
                lines_valid += 1
                if int(line.get("hits", "0")) > 0:
                    lines_covered += 1

                condition = line.get("condition-coverage")
                if condition and "(" in condition:
                    covered, total = condition.split("(")[1].rstrip(")").split("/")
                    branches_valid += int(total)
                    branches_covered += int(covered)

    line_pct = 100.0 * lines_covered / lines_valid if lines_valid else 100.0
    branch_pct = 100.0 * branches_covered / branches_valid if branches_valid else 100.0
    return line_pct, branch_pct, lines_valid


def load_floor(path: Path) -> dict[str, float]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"line": INITIAL_LINE_FLOOR, "branch": INITIAL_BRANCH_FLOOR}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_xml", type=Path, help="coverage.xml from pytest --cov-report=xml")
    parser.add_argument(
        "--update",
        action="store_true",
        help="raise the stored floor to match current coverage (never lowers it)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    floor_path = repo_root / FLOOR_FILE
    floor = load_floor(floor_path)

    if not args.coverage_xml.is_file():
        print(f"Coverage report not found: {args.coverage_xml}", file=sys.stderr)
        return 1

    line_pct, branch_pct, statements = measure(args.coverage_xml)

    # Before L0-L2 has any code, there is nothing to gate and the ratchet must
    # not block the substrate loops that come first.
    if statements == 0:
        print("No L0-L2 statements measured yet — ratchet idle (expected until HAL-01 lands).")
        return 0

    print(
        f"L0-L2 coverage: {line_pct:.2f}% line, {branch_pct:.2f}% branch ({statements} statements)"
    )
    print(f"Floor:          {floor['line']:.2f}% line, {floor['branch']:.2f}% branch")

    failures = []
    if line_pct < floor["line"]:
        failures.append(f"line coverage {line_pct:.2f}% is below the floor of {floor['line']:.2f}%")
    if branch_pct < floor["branch"]:
        failures.append(
            f"branch coverage {branch_pct:.2f}% is below the floor of {floor['branch']:.2f}%"
        )

    if failures:
        print("\nCoverage ratchet failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        print(
            "\nAdd tests that assert on the uncovered behaviour. Do not lower the floor,\n"
            "and do not add tests that call code without asserting on it — that satisfies\n"
            "the number while defeating its purpose (AGENTS.md §5).",
            file=sys.stderr,
        )
        return 1

    if args.update:
        new_floor = {
            "line": max(floor["line"], round(line_pct, 2)),
            "branch": max(floor["branch"], round(branch_pct, 2)),
        }
        if new_floor != floor:
            floor_path.write_text(json.dumps(new_floor, indent=2) + "\n", encoding="utf-8")
            print(
                f"\nRatchet raised: line {floor['line']:.2f}% -> {new_floor['line']:.2f}%, "
                f"branch {floor['branch']:.2f}% -> {new_floor['branch']:.2f}%"
            )

    print("\nCoverage ratchet passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

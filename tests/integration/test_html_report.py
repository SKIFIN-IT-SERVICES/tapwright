# SPDX-License-Identifier: Apache-2.0

"""T2 test plan for RUN-03 — HTML report (`TOOL-REQ-031`).

Implements #39. Oracle is the plan's own line: "Report renders; contains
every result; deterministic output." Every case spawns a genuine
subprocess `pytest` run against a small throwaway suite and inspects the
resulting HTML file -- testing "the report auto-generates when tapwright's
plugin is active" from *within* the same pytest process being tested would
be circular; a separate process is the only way to observe it honestly.

## Reuse decision (`AGENTS.md` §3)

Wraps `pytest-html` (MPL-2.0, already on `licences.toml`'s `allowed` list,
no isolation required) rather than writing HTML report generation from
scratch -- it already solves "renders, contains every result, self-
contained file" cleanly; per `pytest-html`'s own `pytest_addoption()`,
`--html=<path>` is its only required option and `--self-contained-html`
folds every asset into one file, matching "no additional configuration."
`tapwright.runner.plugin` gains a `pytest_configure()` hook that sets
`config.option.htmlpath` to a default path *only if the user hasn't
already set one* -- `pytest-html` still does the actual rendering,
`tapwright` only makes the option automatic. New dependencies:
`pytest-html` and its own transitive `pytest-metadata` dependency, both
MPL-2.0 -- to be added to `pyproject.toml` and `licences.toml`.

## Scope notes (posted in full to #39; kept here as a pointer)

- **"Decoded frames" is a documented gap, not built here.** No mechanism
  anywhere in this codebase records which frames a test exchanged during
  its run for a report to read back later -- flagged as a real follow-up
  in the issue, not silently dropped or speculatively built.
- **"Deterministic output" scoped to the results table, not the raw
  bytes.** `pytest-html`'s own default template embeds a wall-clock
  generation timestamp ("Report generated on <date> at <time>") --
  confirmed directly by generating one during this test plan's own
  research. No report-generation tool produces byte-identical files
  across time and that isn't really what "deterministic" means in this
  context (see `NFR-003`, which is about flaky *test outcomes*, not
  byte-identical *files*). What's tested here: the same suite run twice
  produces the same set of results, in the same order, with the same
  outcomes -- the part that would actually catch a real bug (e.g. a race
  in how results get collected).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #39)")

PASSING_TEST = "def test_ok():\n    assert True\n"
FAILING_TEST = "def test_not_ok():\n    assert False\n"
MIXED_SUITE = (
    "import pytest\n"
    "def test_a():\n    assert True\n"
    "def test_b():\n    assert False\n"
    '@pytest.mark.skip(reason="demo")\n'
    "def test_c():\n    assert True\n"
)


def run_pytest(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_report_auto_generates_with_no_explicit_flag(tmp_path):
    """The literal "without additional configuration" requirement: no
    `--html=...` flag passed, a report still appears.
    """
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)

    run_pytest("test_sample.py", cwd=tmp_path)

    reports = list(tmp_path.glob("*.html"))
    assert len(reports) == 1


@SKIP
def test_report_contains_every_result(tmp_path):
    (tmp_path / "test_sample.py").write_text(MIXED_SUITE)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = next(tmp_path.glob("*.html")).read_text(encoding="utf-8")
    assert "test_a" in report
    assert "test_b" in report
    assert "test_c" in report


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_explicit_html_flag_is_not_overridden(tmp_path):
    """A user who already knows what they're doing and passes their own
    `--html=` path keeps it -- the auto-default only fills a gap, it
    doesn't fight an explicit choice.
    """
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)
    custom_path = tmp_path / "custom_report.html"

    run_pytest("test_sample.py", f"--html={custom_path}", cwd=tmp_path)

    assert custom_path.exists()
    assert not any(
        p.name != "custom_report.html" for p in tmp_path.glob("*.html")
    )


@SKIP
def test_repeated_runs_produce_the_same_results_table(tmp_path):
    """The testable half of "deterministic": the same suite run twice
    produces the same set of results, same order, same outcomes -- not
    byte-identical files (see module docstring for why that's out of
    scope: the default template embeds a generation timestamp).
    """
    (tmp_path / "test_sample.py").write_text(MIXED_SUITE)

    run_pytest("test_sample.py", "--html=r1.html", cwd=tmp_path)
    run_pytest("test_sample.py", "--html=r2.html", cwd=tmp_path)

    def results_only(report_path: Path) -> str:
        # Strip anything timestamp-shaped so this compares the meaningful
        # content, not the one deliberately-excluded piece of non-determinism.
        import re

        text = report_path.read_text(encoding="utf-8")
        return re.sub(r"Report generated on .*? by", "", text)

    assert results_only(tmp_path / "r1.html") == results_only(tmp_path / "r2.html")


@SKIP
def test_empty_suite_still_produces_a_valid_report(tmp_path):
    run_pytest(cwd=tmp_path)  # empty directory, nothing to collect

    reports = list(tmp_path.glob("*.html"))
    assert len(reports) == 1
    assert "<html" in reports[0].read_text(encoding="utf-8").lower()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_failed_test_is_clearly_marked_failed_in_the_report(tmp_path):
    (tmp_path / "test_sample.py").write_text(FAILING_TEST)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = next(tmp_path.glob("*.html")).read_text(encoding="utf-8")
    assert "test_not_ok" in report
    assert "failed" in report.lower()


@SKIP
def test_skipped_test_still_appears_not_silently_dropped(tmp_path):
    (tmp_path / "test_sample.py").write_text(MIXED_SUITE)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = next(tmp_path.glob("*.html")).read_text(encoding="utf-8")
    assert "test_c" in report
    assert "skipped" in report.lower()

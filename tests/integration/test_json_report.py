# SPDX-License-Identifier: Apache-2.0

"""T2 test plan for RUN-04 — JSON machine-readable report (`TOOL-REQ-032`).

Implements #41. Oracle is the plan's own line: "Schema-validates;
round-trips." Every case spawns a genuine subprocess `pytest` run against
a throwaway suite and inspects the resulting JSON file — same reasoning as
RUN-03's own test file: testing "the report auto-generates when
tapwright's plugin is active" from within the same pytest process being
tested would be circular.

## Priority + scope correction (posted in full to #41; kept here as a
pointer)

- **Priority is Should, not Must** — the plan's own loop table said "Must"
  but `TOOL-REQ-032` itself, the requirement this loop implements, rates
  itself "Should." Filed and treated as Should.
- **"Schema-validates" means against a schema this loop defines and
  ships** (`docs/schemas/run-report.schema.json`), not an external ASAM
  ATX standard — `TOOL-REQ-032`'s own wording ("not built now, just don't
  block it") rules out a full ATX implementation here. The schema codifies
  what `tapwright` promises a results-warehouse consumer, not everything
  the underlying library happens to emit.

## Reuse decision (`AGENTS.md` §3)

Wraps `pytest-json-report` (MIT, already allowed) rather than writing JSON
report generation from scratch — same reuse-first approach RUN-03 took
with `pytest-html`. `tapwright.runner.plugin`'s existing `pytest_configure`
hook (already `tryfirst=True` for the HTML report) gains the same
auto-enable logic for `--json-report`: only fills the gap if the user
hasn't already opted in, and `pytest-json-report`'s own `pytest_configure`
only registers its reporter if `config.option.json_report` is already
truthy by the time its hook runs (confirmed directly by reading its
source) — the same ordering requirement `tryfirst=True` already satisfies
for the HTML case, so this reuses the existing hook rather than adding a
second one.

`jsonschema` (MIT) is a new **dev**-only dependency — schema validation is
this loop's own test-suite property, not something the runtime
report-writing path re-validates on every run (that would just be
`pytest-json-report` checking its own already-correct output).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PASSING_TEST = "def test_ok():\n    assert True\n"
FAILING_TEST = "def test_not_ok():\n    assert False\n"
MIXED_SUITE = (
    "import pytest\n"
    "def test_a():\n    assert True\n"
    "def test_b():\n    assert False\n"
    '@pytest.mark.skip(reason="demo")\n'
    "def test_c():\n    assert True\n"
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "schemas" / "run-report.schema.json"


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


def test_report_auto_generates_with_no_explicit_flag(tmp_path):
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)

    run_pytest("test_sample.py", cwd=tmp_path)

    reports = list(tmp_path.glob("*.json"))
    assert len(reports) == 1


def test_report_contains_every_result(tmp_path):
    (tmp_path / "test_sample.py").write_text(MIXED_SUITE)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    node_ids = {test["nodeid"] for test in report["tests"]}
    assert node_ids == {
        "test_sample.py::test_a",
        "test_sample.py::test_b",
        "test_sample.py::test_c",
    }


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_explicit_json_report_file_is_not_overridden(tmp_path):
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)
    custom_path = tmp_path / "custom_report.json"

    run_pytest("test_sample.py", f"--json-report-file={custom_path}", cwd=tmp_path)

    assert custom_path.exists()
    assert not any(p.name != "custom_report.json" for p in tmp_path.glob("*.json"))


def test_report_round_trips_through_json(tmp_path):
    """The literal "round-trips" requirement: parse, re-serialize,
    re-parse, same data survives.
    """
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)

    run_pytest("test_sample.py", cwd=tmp_path)

    report_path = next(tmp_path.glob("*.json"))
    first = json.loads(report_path.read_text(encoding="utf-8"))
    second = json.loads(json.dumps(first))
    assert first == second


def test_report_validates_against_our_schema(tmp_path):
    """ "Schema-validates" against `docs/schemas/run-report.schema.json` —
    the schema this loop defines and ships, not an external ATX spec (see
    module docstring).
    """
    import jsonschema

    (tmp_path / "test_sample.py").write_text(MIXED_SUITE)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_failed_test_has_failed_outcome_in_the_report(tmp_path):
    (tmp_path / "test_sample.py").write_text(FAILING_TEST)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    (test,) = report["tests"]
    assert test["nodeid"] == "test_sample.py::test_not_ok"
    assert test["outcome"] == "failed"


def test_skipped_test_has_skipped_outcome_not_silently_dropped(tmp_path):
    (tmp_path / "test_sample.py").write_text(MIXED_SUITE)

    run_pytest("test_sample.py", cwd=tmp_path)

    report = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    by_id = {test["nodeid"]: test for test in report["tests"]}
    assert by_id["test_sample.py::test_c"]["outcome"] == "skipped"

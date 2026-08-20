# SPDX-License-Identifier: Apache-2.0

"""T2 test plan for RUN-05 — unified CLI, single entry point for all
invocation modes (ADR-001, `TOOL-REQ-030`).

Implements #31. The oracle is ADR-001 itself, verbatim: "One package.
Interactive use and CI use are invocation modes of the same code, never
separate builds or SKUs," and `TOOL-REQ-030`'s acceptance criterion:
"verify explicitly that no separate build artifact exists for CI." Every
case below runs the CLI as a genuine subprocess (never imports
`tapwright.cli` and calls `main()` in-process) — that *is* the property
under test: the identical command, external to this test process, on
whichever invocation surface reaches it.

## Scope notes (posted in full to #31; kept here as a pointer)

- **CLI shape**: bare pytest-passthrough (`tapwright [pytest-args...]`),
  not a `tapwright run` subcommand. The issue's own "Proposed solution"
  sketched `tapwright run`, but there is exactly one thing this CLI does
  today (delegate to pytest) and no second subcommand to distinguish it
  from — inventing subcommand dispatch for a single command is
  complexity `AGENTS.md`'s reuse/no-speculative-abstraction discipline
  doesn't support yet. A `run` subcommand (or others) is a natural
  addition once RUN-02/03/04 give the CLI something else to dispatch to.
  Flagged here as a deliberate deviation from the issue's rough sketch,
  not a silent one.
- **Two invocation surfaces, both tested**: the installed console script
  (`tapwright ...`) and `python -m tapwright ...` — a container or CI
  step might reasonably use either, and TOOL-REQ-030's "no separate
  build artifact" claim is strongest when both actually exist and agree.
- **L2 API-cleanliness note** (test-plan skill step 5): N/A — this loop
  doesn't touch `diag/`'s public API surface at all.
- Not in scope: RUN-02 (YAML->pytest collection), RUN-03/04 (HTML/JSON
  reports) — neither exists yet for this CLI to integrate with.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #31)")

PASSING_TEST = "def test_ok():\n    assert True\n"
FAILING_TEST = "def test_not_ok():\n    assert False\n"


def run_cli(*args: str, cwd: Path, via: str = "module") -> subprocess.CompletedProcess:
    """Invoke the CLI as a genuine subprocess -- either `python -m
    tapwright` (`via="module"`) or the installed console script
    (`via="script"`) -- and return the completed process.
    """
    if via == "module":
        command = [sys.executable, "-m", "tapwright", *args]
    elif via == "script":
        command = ["tapwright", *args]
    else:
        raise ValueError(f"unknown via: {via!r}")
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_cli_passes_through_to_pytest_and_returns_its_exit_code(tmp_path):
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)

    result = run_cli("test_sample.py", cwd=tmp_path)

    assert result.returncode == 0


@SKIP
def test_cli_runs_identically_via_installed_console_script(tmp_path):
    """TOOL-REQ-030's own acceptance test, literally: the same command
    succeeds regardless of which invocation surface (installed script vs.
    `python -m`) reaches it -- no separate build artifact for either.
    """
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)

    module_result = run_cli("test_sample.py", cwd=tmp_path, via="module")
    script_result = run_cli("test_sample.py", cwd=tmp_path, via="script")

    assert module_result.returncode == 0
    assert script_result.returncode == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_cli_forwards_arbitrary_pytest_arguments(tmp_path):
    (tmp_path / "test_sample.py").write_text(
        "def test_a():\n    assert True\n\ndef test_b():\n    assert True\n"
    )

    result = run_cli("test_sample.py", "-k", "test_a", "-v", cwd=tmp_path)

    assert result.returncode == 0
    assert "test_a" in result.stdout
    assert "test_b" not in result.stdout


@SKIP
def test_cli_with_no_arguments_collects_from_cwd_like_bare_pytest(tmp_path):
    (tmp_path / "test_sample.py").write_text(PASSING_TEST)

    result = run_cli(cwd=tmp_path)

    assert result.returncode == 0


@SKIP
def test_cli_succeeds_in_a_minimal_headless_subprocess_environment(tmp_path):
    """A proxy for ADR-001's "laptop, headless bench, and container" claim:
    a stripped-down environment (no DISPLAY, no interactive-only vars) with
    only PATH and the Python install preserved, run in a genuinely separate
    process. Nothing about the CLI should depend on an interactive desktop.
    """
    import os

    (tmp_path / "test_sample.py").write_text(PASSING_TEST)
    minimal_env = {"PATH": os.environ["PATH"]}
    if sys.platform == "win32":
        minimal_env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    result = subprocess.run(
        [sys.executable, "-m", "tapwright", "test_sample.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        env=minimal_env,
    )

    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_cli_returns_pytest_failure_exit_code_unmasked(tmp_path):
    (tmp_path / "test_sample.py").write_text(FAILING_TEST)

    result = run_cli("test_sample.py", cwd=tmp_path)

    assert result.returncode == 1


@SKIP
def test_cli_returns_pytest_usage_error_exit_code_unmasked(tmp_path):
    result = run_cli("--not-a-real-flag", cwd=tmp_path)

    assert result.returncode == 4


@SKIP
def test_cli_returns_no_tests_collected_exit_code_unmasked(tmp_path):
    result = run_cli(cwd=tmp_path)  # empty directory, nothing to collect

    assert result.returncode == 5

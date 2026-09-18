# SPDX-License-Identifier: Apache-2.0

"""T1: loop telemetry's mechanically-derivable subset (INF-07).

Mirrors tests/unit/test_guardrails.py's own style for tools/ scripts:
importable, testable functions plus a thin main()/CLI wrapper, exercised
directly rather than by shelling out to the script.
"""

from __future__ import annotations

import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import loop_telemetry  # noqa: E402


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def commit(repo: Path, message: str) -> None:
    (repo / "file.txt").write_text(message, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)


# ---------------------------------------------------------------------------
# closed_loop_count
# ---------------------------------------------------------------------------


def test_closed_loop_count_parses_the_summary_line(tmp_path):
    loops_md = tmp_path / "LOOPS.md"
    loops_md.write_text("intro text\n\n**12 of 38 loops closed** (details...)\n", encoding="utf-8")
    assert loop_telemetry.closed_loop_count(loops_md) == 12


def test_closed_loop_count_raises_on_missing_line(tmp_path):
    loops_md = tmp_path / "LOOPS.md"
    loops_md.write_text("no summary line here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="loops closed"):
        loop_telemetry.closed_loop_count(loops_md)


# ---------------------------------------------------------------------------
# fixture_tamper_attempt_count
# ---------------------------------------------------------------------------


def test_fixture_tamper_attempt_count_counts_real_trailers(tmp_path):
    repo = make_repo(tmp_path)
    commit(repo, "chore: unrelated change")
    commit(
        repo,
        "fix(fixtures): correct a wrong golden value\n\n"
        "fixture-change: the DBC's own scale factor was mistranscribed; "
        "re-verified against the vendor spec",
    )
    assert loop_telemetry.fixture_tamper_attempt_count(repo) == 1


def test_fixture_tamper_attempt_count_ignores_prose_mentions(tmp_path):
    """A commit merely *discussing* the trailer convention, without one of
    its own lines actually being the trailer, must not be miscounted —
    found directly against this repo's own history while writing this
    loop (two commits mention "fixture-change:" in explanatory prose).
    """
    repo = make_repo(tmp_path)
    commit(
        repo,
        "docs: explain the fixture-change: trailer convention in AGENTS.md",
    )
    assert loop_telemetry.fixture_tamper_attempt_count(repo) == 0


def test_fixture_tamper_attempt_count_returns_zero_with_no_trailers(tmp_path):
    repo = make_repo(tmp_path)
    commit(repo, "feat: add a thing")
    commit(repo, "test: add a test")
    assert loop_telemetry.fixture_tamper_attempt_count(repo) == 0


# ---------------------------------------------------------------------------
# needs_rca_issue_count
# ---------------------------------------------------------------------------


def test_needs_rca_issue_count_returns_none_without_token():
    assert loop_telemetry.needs_rca_issue_count(token="") is None


def test_needs_rca_issue_count_parses_total_count(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return b'{"total_count": 5}'

    monkeypatch.setattr(loop_telemetry.urllib.request, "urlopen", lambda *a, **kw: FakeResponse())
    assert loop_telemetry.needs_rca_issue_count(token="fake-token") == 5


def test_needs_rca_issue_count_returns_none_on_network_error(monkeypatch):
    def raise_error(*args, **kwargs):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(loop_telemetry.urllib.request, "urlopen", raise_error)
    assert loop_telemetry.needs_rca_issue_count(token="fake-token") is None


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_computes_escape_rate(tmp_path, monkeypatch):
    (tmp_path / "LOOPS.md").write_text("**10 of 38 loops closed**\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    commit(tmp_path, "chore: init")

    monkeypatch.setattr(loop_telemetry, "needs_rca_issue_count", lambda token=None: 2)

    report = loop_telemetry.build_report(tmp_path)
    assert report["closed_loops"] == 10
    assert report["needs_rca_issues"] == 2
    assert report["escape_rate"] == 0.2
    assert report["not_computed"] == loop_telemetry.NOT_COMPUTED


def test_build_report_escape_rate_is_none_when_rca_count_unavailable(tmp_path, monkeypatch):
    (tmp_path / "LOOPS.md").write_text("**10 of 38 loops closed**\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    commit(tmp_path, "chore: init")

    monkeypatch.setattr(loop_telemetry, "needs_rca_issue_count", lambda token=None: None)

    report = loop_telemetry.build_report(tmp_path)
    assert report["needs_rca_issues"] is None
    assert report["escape_rate"] is None

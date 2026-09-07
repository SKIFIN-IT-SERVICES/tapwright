# SPDX-License-Identifier: Apache-2.0

"""T1 tests for INF-08 — docs site + executable examples, doctest in CI
(`FW-REQ-066`).

Implements #59. Oracle per the plan's own row: "Every code sample in docs
runs in CI." `docs/quickstart.md`'s Python example is verified via
`doctest` (the plan's own literal wording — no custom fenced-code-block
extractor needed).

`mkdocs build --strict` (the actual "site builds live" proof) runs as its
own CI job step, not wrapped in pytest — it's an external build tool
invocation, not a Python-level testable unit. This file instead checks
`mkdocs.yml`'s own config sanity fast and without a dependency on `mkdocs`
being importable: valid YAML, referencing only files that actually exist.
"""

from __future__ import annotations

import doctest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
QUICKSTART = REPO_ROOT / "docs" / "quickstart.md"
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"


def test_quickstart_doctest_passes():
    results = doctest.testfile(str(QUICKSTART), module_relative=False, optionflags=doctest.ELLIPSIS)
    assert results.attempted > 0, "quickstart.md has no runnable doctest examples"
    assert results.failed == 0


def test_doctest_runner_catches_a_wrong_example(tmp_path):
    """A meta-test proving the check isn't vacuous: a deliberately wrong
    expected value must actually fail, the same way a real drift between
    quickstart.md and tapwright's own API would.
    """
    broken = tmp_path / "broken.md"
    broken.write_text(
        "```\n>>> 1 + 1\n3\n```\n",
        encoding="utf-8",
    )
    results = doctest.testfile(str(broken), module_relative=False)
    assert results.attempted > 0
    assert results.failed > 0


def test_mkdocs_config_is_valid_yaml():
    config = yaml.safe_load(MKDOCS_CONFIG.read_text(encoding="utf-8"))
    assert "nav" in config


def test_mkdocs_config_references_only_existing_files():
    config = yaml.safe_load(MKDOCS_CONFIG.read_text(encoding="utf-8"))
    docs_dir = REPO_ROOT / "docs"

    def _pages(nav_entries):
        for entry in nav_entries:
            if isinstance(entry, str):
                yield entry
            elif isinstance(entry, dict):
                for value in entry.values():
                    if isinstance(value, str):
                        yield value
                    else:
                        yield from _pages(value)

    for page in _pages(config["nav"]):
        assert (docs_dir / page).is_file(), f"mkdocs.yml nav references missing file: {page}"

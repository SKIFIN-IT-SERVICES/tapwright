# SPDX-License-Identifier: Apache-2.0

"""`tapwright` — the unified CLI entry point (RUN-05, `TOOL-REQ-030`,
ADR-001).

    tapwright [pytest args...]

A thin pass-through to `pytest.main()`, not a reimplementation of test
collection or execution, per `AGENTS.md`'s reuse rule: pytest already *is*
"one engine, invocation modes only" (the same command line runs unmodified
on a laptop, a headless bench, or in a CI container) — this module exists
so that property has a named, branded entry point rather than requiring
`pytest`-and-flags knowledge on day one. Every argument is forwarded to
pytest unchanged, and pytest's own exit code is returned unchanged.
"""

from __future__ import annotations

import sys

import pytest


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    return int(pytest.main(args))

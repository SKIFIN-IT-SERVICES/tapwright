# SPDX-License-Identifier: Apache-2.0

"""L3 — pytest plugin: fixtures, deterministic wait helpers, CI entrypoints.

Tests are plain pytest — this module is the fixture layer, not a custom
runner. See ARCHITECTURE.md at the repository root.

Implemented so far: `plugin.py` (RUN-01, `TOOL-REQ-028`; RUN-03/04 report
auto-enable) — the `ecu`, `bus`, `uds` fixtures, registered as a `pytest11`
entry point in `pyproject.toml` so they're auto-discovered on
`pip install tapwright`, no `pytest_plugins = [...]` needed. `cli.py`
(RUN-05, `TOOL-REQ-030`) — the unified CLI entry point. `wait.py` (RUN-10,
`TOOL-REQ-029`) — `wait_for_message()`/`wait_for_signal()`/
`wait_for_response()`. None of these are imported here: pytest discovers
`plugin.py` via the entry point directly, `cli.py`/`wait.py` are imported
directly by name (`from tapwright.runner.wait import ...`), not via
`tapwright.runner`'s own import graph.
"""

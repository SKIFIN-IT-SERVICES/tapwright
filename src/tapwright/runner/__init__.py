# SPDX-License-Identifier: Apache-2.0

"""L3 — pytest plugin: fixtures, deterministic wait helpers, CI entrypoints.

Tests are plain pytest — this module is the fixture layer, not a custom
runner. See ARCHITECTURE.md at the repository root.

Implemented so far: `plugin.py` (RUN-01, `TOOL-REQ-028`) — the `ecu`, `bus`,
`uds` fixtures, registered as a `pytest11` entry point in `pyproject.toml`
so they're auto-discovered on `pip install tapwright`, no
`pytest_plugins = [...]` needed. Not imported here: pytest discovers plugin
modules via the entry point directly, not via `tapwright.runner`'s own
import graph.

Not yet implemented: deterministic `wait_for_*` helpers (`TOOL-REQ-029`,
a separate requirement from RUN-01's three fixtures), CLI entrypoints
(RUN-05), reports (RUN-03/04).
"""

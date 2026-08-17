# SPDX-License-Identifier: Apache-2.0

"""T1: HAL config-validation errors (issue #3) — no socket touched, so no
`vcan` needed. The lifecycle/capability error cases that do need a live bus
are in `tests/integration/test_hal_lifecycle_errors.py`.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3
"""

from __future__ import annotations

import pytest


def test_open_bus_with_unknown_backend_raises_clear_error():
    """An unknown backend name fails fast with a typed, readable error — not
    a bare AttributeError/KeyError surfaced from deep inside the
    implementation.

    Adjacent to TOOL-REQ-009 (capability detection / graceful degradation),
    which is not cited on issue #3 — included here because "unknown
    backend" is a more basic instance of the same principle, directly
    implied by TOOL-REQ-001's "interface swap is a config change" framing: a
    bad config value must be caught, not silently misrouted.
    """
    from tapwright.hal import open_bus
    from tapwright.hal.errors import HalError

    with pytest.raises(HalError):
        open_bus(backend="not-a-real-backend", channel="vcan0")


def test_open_bus_with_missing_channel_raises_clear_error():
    """Missing required config (no channel) is caught at the config
    boundary, not several frames deep inside python-can."""
    from tapwright.hal import open_bus
    from tapwright.hal.errors import HalError

    with pytest.raises(HalError):
        open_bus(backend="socketcan")

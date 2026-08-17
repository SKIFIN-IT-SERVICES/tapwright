# SPDX-License-Identifier: Apache-2.0

"""T2: HAL bus-lifecycle and capability-mismatch errors (issue #3) — need a
live `vcan` bus, unlike the config-validation cases in
`tests/unit/test_hal_config_errors.py`.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_vcan


def test_send_after_shutdown_raises_clear_error(vcan_channel):
    """Using a bus handle after shutdown() must raise a clear error, not
    hang or silently no-op."""
    from tapwright.hal import Frame, open_bus
    from tapwright.hal.errors import HalError

    bus = open_bus(backend="socketcan", channel=vcan_channel)
    bus.shutdown()
    with pytest.raises(HalError):
        bus.send(Frame(arbitration_id=0x1, data=b"\x00"))


def test_can_fd_send_on_non_fd_bus_raises_clear_error(vcan_channel):
    """TOOL-REQ-009: attempting a CAN-FD operation on a classic-CAN-only-
    opened bus produces a clear error, not a silent failure or crash.

    Folded into issue #3's scope during test-plan review (originally not
    cited on the issue) since the send path already distinguishes fd vs.
    non-fd for the CAN-FD round-trip cases in test_hal_abstraction.py and
    test_hal_boundaries.py.
    """
    from tapwright.hal import Frame, open_bus
    from tapwright.hal.errors import HalError

    bus = open_bus(backend="socketcan", channel=vcan_channel, fd=False)
    try:
        with pytest.raises(HalError):
            bus.send(Frame(arbitration_id=0x1, data=b"\x00" * 32, is_fd=True))
    finally:
        bus.shutdown()

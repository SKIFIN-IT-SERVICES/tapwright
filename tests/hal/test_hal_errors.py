"""Test plan (error cases) for issue #3 — invalid config and bus-lifecycle
misuse.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3
"""

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

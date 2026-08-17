# SPDX-License-Identifier: Apache-2.0

"""T2: happy-path test plan for issue #3 — L0 HAL abstraction skeleton +
SocketCAN backend + vcan + basic CAN/CAN-FD frame send/receive.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3
Implements: TOOL-REQ-001 (partial), TOOL-REQ-002, TOOL-REQ-008, TOOL-REQ-009,
TOOL-REQ-010.
See docs/tooling-requirements.md for each ID's full acceptance criteria.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_vcan


def test_open_bus_returns_hal_bus_for_socketcan_backend(vcan_channel):
    """TOOL-REQ-002/008: opening a SocketCAN-backed bus (incl. vcan) returns
    a bus handle exposing the abstraction's send/recv/shutdown surface."""
    from tapwright.hal import open_bus

    bus = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        assert hasattr(bus, "send")
        assert hasattr(bus, "recv")
        assert hasattr(bus, "shutdown")
    finally:
        bus.shutdown()


def test_classic_can_frame_roundtrips_over_vcan(vcan_channel):
    """TOOL-REQ-010/008: a frame round-trips across two vcan-connected bus
    handles — the literal M1 acceptance criterion."""
    from tapwright.hal import Frame, open_bus

    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sent = Frame(arbitration_id=0x123, data=b"\x01\x02\x03\x04")
        sender.send(sent)
        received = receiver.recv(timeout=1.0)
        assert received is not None
        assert received.arbitration_id == sent.arbitration_id
        assert received.data == sent.data
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_can_fd_frame_roundtrips_over_vcan(vcan_channel):
    """TOOL-REQ-010: a CAN-FD frame (>8-byte payload) round-trips, proving
    CAN-FD is actually exercised and not just classic CAN."""
    from tapwright.hal import Frame, open_bus

    sender = open_bus(backend="socketcan", channel=vcan_channel, fd=True)
    receiver = open_bus(backend="socketcan", channel=vcan_channel, fd=True)
    try:
        payload = bytes(range(32))  # exceeds classic CAN's 8-byte max
        sent = Frame(arbitration_id=0x456, data=payload, is_fd=True)
        sender.send(sent)
        received = receiver.recv(timeout=1.0)
        assert received is not None
        assert received.is_fd is True
        assert received.data == payload
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_backend_swap_is_config_only(vcan_channel):
    """TOOL-REQ-001 (partial): swapping backend is a config change, not an
    app-code branch.

    This proves the abstraction *shape* using socketcan/vcan as the only
    real backend this issue implements. TOOL-REQ-001's full "works
    unmodified across >=3 distinct backends" acceptance criterion is
    explicitly deferred to a follow-up issue (gs_usb + Kvaser backends), per
    issue #3's body — not claimed satisfied by this test alone.

    Uses two bus handles, like every other round-trip case in this file —
    a single handle sending and receiving on itself will never observe its
    own frame on SocketCAN unless the bus was opened with
    receive_own_messages=True, which open_bus() deliberately doesn't default
    to (that's a loopback-testing convenience, not part of the abstraction's
    contract). This is a real fix, caught by this branch's own CI: the
    original single-handle version failed with `assert None is not None`.
    """
    from tapwright.hal import Frame, open_bus

    def roundtrip(config):
        sender = open_bus(**config)
        receiver = open_bus(**config)
        try:
            sent = Frame(arbitration_id=0x1, data=b"\xaa")
            sender.send(sent)
            return receiver.recv(timeout=1.0)
        finally:
            sender.shutdown()
            receiver.shutdown()

    result = roundtrip({"backend": "socketcan", "channel": vcan_channel})
    assert result is not None

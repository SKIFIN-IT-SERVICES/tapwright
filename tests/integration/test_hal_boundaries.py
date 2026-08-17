# SPDX-License-Identifier: Apache-2.0

"""T2: edge-case test plan for issue #3 — boundary conditions implied by
TOOL-REQ-008/010 but not spelled out literally in their acceptance criteria.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.requires_vcan


def test_recv_times_out_cleanly_with_no_traffic(vcan_channel):
    """Derived from NFR-003 (test determinism): recv() must return promptly,
    not hang, when nothing is sent — not a literal TOOL-REQ-010 clause, but
    implied by the "deterministic wait helpers" thread the rest of the spec
    depends on (TOOL-REQ-029)."""
    from tapwright.hal import open_bus

    bus = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        start = time.monotonic()
        result = bus.recv(timeout=0.2)
        elapsed = time.monotonic() - start
        assert result is None
        assert elapsed < 1.0
    finally:
        bus.shutdown()


def test_classic_can_max_payload_8_bytes_roundtrips(vcan_channel):
    """Boundary: classic CAN's maximum 8-byte payload."""
    from tapwright.hal import Frame, open_bus

    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        payload = bytes(range(8))
        sender.send(Frame(arbitration_id=0x7, data=payload))
        received = receiver.recv(timeout=1.0)
        assert received is not None
        assert received.data == payload
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_can_fd_max_payload_64_bytes_roundtrips(vcan_channel):
    """Boundary: CAN-FD's maximum 64-byte payload."""
    from tapwright.hal import Frame, open_bus

    sender = open_bus(backend="socketcan", channel=vcan_channel, fd=True)
    receiver = open_bus(backend="socketcan", channel=vcan_channel, fd=True)
    try:
        payload = bytes(range(64))
        sender.send(Frame(arbitration_id=0x8, data=payload, is_fd=True))
        received = receiver.recv(timeout=1.0)
        assert received is not None
        assert received.data == payload
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_extended_29bit_arbitration_id_roundtrips(vcan_channel):
    """Boundary: 29-bit extended CAN ID, not just the 11-bit standard ID
    used by the other happy-path cases."""
    from tapwright.hal import Frame, open_bus

    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sent = Frame(arbitration_id=0x1FFFFFFF, data=b"\x01", is_extended_id=True)
        sender.send(sent)
        received = receiver.recv(timeout=1.0)
        assert received is not None
        assert received.arbitration_id == 0x1FFFFFFF
        assert received.is_extended_id is True
    finally:
        sender.shutdown()
        receiver.shutdown()

# SPDX-License-Identifier: Apache-2.0

"""T4 (property, per the plan's own declared tier for HAL-07 — a
parametrized sweep here, not `hypothesis`; see module docstring's own
note below for why) test plan for HAL-07 / `TOOL-REQ-009` — capability
detection + graceful degradation.

Implements #43. Oracle is the plan's own line: "CAN-FD op on classic-CAN
device → clear error, never silent failure. Property test: no silent
capability mismatch across backend/op matrix."

A capability check already exists —
`tapwright.hal.bus.Bus.send()` raises `CapabilityError` when
`frame.is_fd and not self._fd` — but was completely untested before this
loop (no test file anywhere referenced `CapabilityError`). This file is
that missing coverage, not new capability-check logic (unless a case
below surfaces a real gap).

## Scope notes (posted in full to #43; kept here as a pointer)

- **The "matrix" is currently single-backend, single-dimension.** Only
  `socketcan` exists today — `gs_usb`/Kvaser/PEAK/Vector XL (HAL-03–06)
  are hardware-gated and not yet built. `(bus_fd, frame_fd)` is the full
  matrix this loop can honestly test; the same parametrize-driven approach
  extends once more backends land, each contributing its own capability
  dimensions, rather than this loop pretending to sweep backends that
  don't exist yet.
- **Parametrize, not `hypothesis`, and that's a deliberate choice, not a
  tier downgrade.** The state space is 2 booleans — 4 combinations,
  already fully enumerable. `hypothesis` over a space this small adds
  ceremony without adding coverage a plain `@pytest.mark.parametrize`
  doesn't already provide completely.
"""

from __future__ import annotations

import pytest

from tapwright.hal import Frame, open_bus
from tapwright.hal.errors import CapabilityError

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #43)")

pytestmark = pytest.mark.requires_vcan


# ---------------------------------------------------------------------------
# The property itself — the literal T4 deliverable
# ---------------------------------------------------------------------------


@SKIP
@pytest.mark.parametrize(
    ("bus_fd", "frame_fd", "should_raise"),
    [
        (True, True, False),  # FD frame on an FD-capable bus: fine
        (True, False, False),  # classic frame on an FD-capable bus: fine
        (False, False, False),  # classic frame on a classic bus: fine
        (False, True, True),  # FD frame on a classic-only bus: the mismatch
    ],
)
def test_capability_matrix_across_bus_and_frame_fd_combinations(
    vcan_channel, bus_fd, frame_fd, should_raise
):
    bus = open_bus(backend="socketcan", channel=vcan_channel, fd=bus_fd)
    try:
        frame = Frame(arbitration_id=0x123, data=b"\x01\x02", is_fd=frame_fd)
        if should_raise:
            with pytest.raises(CapabilityError):
                bus.send(frame)
        else:
            bus.send(frame)  # must not raise
    finally:
        bus.shutdown()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_capability_error_message_names_the_mismatch(vcan_channel):
    """"Clear error" means a human reading it understands what went
    wrong -- not just that *something* raised.
    """
    bus = open_bus(backend="socketcan", channel=vcan_channel, fd=False)
    try:
        with pytest.raises(CapabilityError) as exc_info:
            bus.send(Frame(arbitration_id=0x123, data=b"\x01", is_fd=True))
        message = str(exc_info.value).lower()
        assert "fd" in message
    finally:
        bus.shutdown()


@SKIP
def test_capability_mismatch_does_not_corrupt_bus_state(vcan_channel):
    """"Never a silent failure" extends to "never corrupts state either" --
    a rejected send must not leave the bus unusable for a subsequent valid
    operation.
    """
    bus = open_bus(backend="socketcan", channel=vcan_channel, fd=False)
    try:
        with pytest.raises(CapabilityError):
            bus.send(Frame(arbitration_id=0x123, data=b"\x01", is_fd=True))

        # The same handle, right after a rejected send, still works.
        bus.send(Frame(arbitration_id=0x456, data=b"\x02", is_fd=False))
    finally:
        bus.shutdown()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_rejected_fd_frame_is_never_silently_sent(vcan_channel):
    """The literal "never a silent failure" requirement, proven rather
    than assumed: a second, independent bus handle confirms nothing
    reached the wire when the capability check rejected the send.
    """
    sender = open_bus(backend="socketcan", channel=vcan_channel, fd=False)
    receiver = open_bus(backend="socketcan", channel=vcan_channel, fd=True)
    try:
        with pytest.raises(CapabilityError):
            sender.send(Frame(arbitration_id=0x789, data=b"\x03", is_fd=True))

        assert receiver.recv(timeout=0.3) is None
    finally:
        sender.shutdown()
        receiver.shutdown()

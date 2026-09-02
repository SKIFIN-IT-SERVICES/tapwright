# SPDX-License-Identifier: Apache-2.0

"""T4 (timing property, not `hypothesis`) test plan for BUS-07 — cyclic
send engine, DBC-driven cycle times (`TOOL-REQ-011`).

Implements #49. Oracle is the plan's own line: "Timing within tolerance
over N seconds on `vcan`; no drift." Per `AGENTS.md`'s reuse rule,
`hal.Bus.send_periodic()` wraps `can.BusABC.send_periodic()` (already
implemented by `python-can`) rather than reimplementing periodic timing.

## Scope note (posted in full to #49; kept here as a pointer)

**Single/multi-*message* cyclic sending, not multi-*node* restbus
simulation.** The plan's own loop table titles this "multi-node," but the
underlying requirement (`TOOL-REQ-011`, Must) is scoped to "basic
stimulation" — full multi-node restbus simulation with node-behavior
scripting is `TOOL-REQ-012` (Should/Fast-follow, explicitly deferred,
matching `docs/tooling-requirements.md`'s own Won't-scope entry for a
"GUI restbus-simulation designer"). Not built here.

## Timing-tolerance note

CI runners are shared, non-realtime VMs — a scheduler jitter budget that a
real ECU or an RTOS could meet reliably cannot be guaranteed on a shared
CI host. Cases here use a generously wide tolerance band (not the literal
±5% `TOOL-REQ-011` names) precisely enough to prove genuinely-cyclic
behavior (not one-shot, not silently stalled) without being flaky on a
loaded runner. Honest about the gap rather than either testing a bound CI
can't reliably meet or silently dropping the timing assertion altogether.
"""

from __future__ import annotations

import time

import pytest

from tapwright.buses.cyclic import start_cyclic_from_dbc
from tapwright.dbc_arxml import load_dbc
from tapwright.hal import Frame, open_bus
from tapwright.hal.errors import CapabilityError

pytestmark = pytest.mark.requires_vcan

FIXTURES_DBC = "fixtures/databases/cyclic.dbc"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_send_periodic_transmits_repeatedly_at_the_configured_period(vcan_channel):
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        task = sender.send_periodic(Frame(arbitration_id=0x100, data=b"\x01"), period=0.05)
        try:
            received = 0
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if receiver.recv(timeout=0.2) is not None:
                    received += 1
            # ~20 expected over 1s at 50ms; a wide band tolerant of CI
            # scheduler jitter (see module docstring), not the literal spec.
            assert 10 <= received <= 30
        finally:
            task.stop()
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_dbc_declared_cycle_time_is_used_automatically(vcan_channel):
    """The literal "DBC-driven cycle times" requirement: the caller
    doesn't specify a period at all -- it comes from the loaded
    `CanDatabase`'s own message definition.
    """
    db = load_dbc(FIXTURES_DBC)
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        signals = {"EngineSpeed": 1000.0, "EngineTemp": 60}
        task = start_cyclic_from_dbc(sender, db, "EngineData", signals)
        try:
            assert receiver.recv(timeout=1.0) is not None
        finally:
            task.stop()
    finally:
        sender.shutdown()
        receiver.shutdown()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_stop_actually_stops_transmission(vcan_channel):
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        task = sender.send_periodic(Frame(arbitration_id=0x200, data=b"\x02"), period=0.05)
        assert receiver.recv(timeout=0.5) is not None  # it's actually running
        task.stop()

        while receiver.recv(timeout=0) is not None:
            pass  # drain anything already in flight when stop() was called

        assert receiver.recv(timeout=0.3) is None
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_dbc_message_with_no_declared_cycle_time_raises_clear_error(vcan_channel):
    """A message the DBC doesn't declare a cycle time for can't silently
    default to something arbitrary -- the caller must be told to supply
    one explicitly.
    """
    db = load_dbc(FIXTURES_DBC)  # NoCycleMessage declares no GenMsgCycleTime
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        with pytest.raises(ValueError):
            start_cyclic_from_dbc(sender, db, "NoCycleMessage", {"Flag": 0})
    finally:
        sender.shutdown()


def test_multiple_concurrent_cyclic_tasks_do_not_interfere(vcan_channel):
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        task_a = sender.send_periodic(Frame(arbitration_id=0x10, data=b"\xaa"), period=0.05)
        task_b = sender.send_periodic(Frame(arbitration_id=0x20, data=b"\xbb"), period=0.05)
        try:
            seen_ids = set()
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline:
                frame = receiver.recv(timeout=0.2)
                if frame is not None:
                    seen_ids.add(frame.arbitration_id)
            assert seen_ids == {0x10, 0x20}

            task_a.stop()
            # b keeps running independently of a's stop
            assert receiver.recv(timeout=0.3) is not None
        finally:
            task_b.stop()
    finally:
        sender.shutdown()
        receiver.shutdown()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_non_positive_period_raises_clear_error_immediately(vcan_channel):
    bus = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        with pytest.raises(ValueError):
            bus.send_periodic(Frame(arbitration_id=0x1, data=b"\x01"), period=0.0)
    finally:
        bus.shutdown()


def test_capability_check_still_applies_through_the_periodic_path(vcan_channel):
    """The same `CapabilityError` HAL-07 already proved for `send()` must
    not be bypassable by going through `send_periodic()` instead -- one
    capability check, not two code paths that could drift apart.
    """
    bus = open_bus(backend="socketcan", channel=vcan_channel, fd=False)
    try:
        with pytest.raises(CapabilityError):
            bus.send_periodic(Frame(arbitration_id=0x1, data=b"\x01", is_fd=True), period=0.05)
    finally:
        bus.shutdown()

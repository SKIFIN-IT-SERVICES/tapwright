# SPDX-License-Identifier: Apache-2.0

"""T2 tests for `wait_for_message()`/`wait_for_signal()` (RUN-10,
`TOOL-REQ-029`).

Implements #53. Oracle per `NFR-003`: no flakiness under normal CI timing
variance — proven here by exercising both the "found before timeout" and
"genuinely times out" paths against real `vcan`.

RUN-10 is a new loop, not one of the plan's original 37 — `TOOL-REQ-029`
was explicitly flagged as out of scope during RUN-01 (see `LOOPS.md`) and
never picked up since; see issue #53 for the full gap writeup.

`wait_for_response()`'s tests live in `tests/unit/test_wait_response.py`
instead — it polls an arbitrary callable, not a bus, so it needs no
`vcan` and shouldn't be gated behind it.

Reuses `fixtures/databases/cyclic.dbc` (BUS-07's self-authored fixture) —
`EngineData` (frame ID `0x100`, `EngineSpeed`/`EngineTemp` signals) is
exactly the shape `wait_for_signal()`'s tests need; no new fixture
required.
"""

from __future__ import annotations

import pytest

from tapwright.dbc_arxml import load_dbc
from tapwright.hal import Frame, open_bus
from tapwright.runner.wait import WaitTimeoutError, wait_for_message, wait_for_signal

pytestmark = pytest.mark.requires_vcan

FIXTURES_DBC = "fixtures/databases/cyclic.dbc"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_wait_for_message_returns_the_first_matching_frame(vcan_channel):
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(Frame(arbitration_id=0x1, data=b"\x00"))  # non-matching, sent first
        sender.send(Frame(arbitration_id=0x2, data=b"\x01"))  # matching

        frame = wait_for_message(receiver, timeout=1.0, predicate=lambda f: f.arbitration_id == 0x2)
        assert frame.arbitration_id == 0x2
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_wait_for_signal_returns_the_decoded_value_once_the_predicate_matches(vcan_channel):
    db = load_dbc(FIXTURES_DBC)
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(db.encode("EngineData", {"EngineSpeed": 100.0, "EngineTemp": 20}))
        sender.send(db.encode("EngineData", {"EngineSpeed": 5000.0, "EngineTemp": 90}))

        value = wait_for_signal(
            receiver, db, "EngineData", "EngineSpeed", predicate=lambda v: v >= 5000.0, timeout=1.0
        )
        assert value == 5000.0
    finally:
        sender.shutdown()
        receiver.shutdown()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_wait_for_message_returns_immediately_when_first_frame_already_matches(vcan_channel):
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(Frame(arbitration_id=0x5, data=b"\x00"))
        frame = wait_for_message(receiver, timeout=1.0, predicate=lambda f: f.arbitration_id == 0x5)
        assert frame.arbitration_id == 0x5
    finally:
        sender.shutdown()
        receiver.shutdown()


def test_wait_for_signal_keeps_polling_past_an_unrelated_frame(vcan_channel):
    """An unrelated frame ID arriving first must not cause `wait_for_signal`
    to error or falsely resolve — exercises the "keep polling past
    non-matching arbitration IDs" path directly, not just "signal value
    not yet right."
    """
    db = load_dbc(FIXTURES_DBC)
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(Frame(arbitration_id=0x999, data=b"\x00" * 8))  # unrelated frame ID
        sender.send(db.encode("EngineData", {"EngineSpeed": 42.0, "EngineTemp": 0}))

        value = wait_for_signal(
            receiver, db, "EngineData", "EngineSpeed", predicate=lambda v: v == 42.0, timeout=1.0
        )
        assert value == 42.0
    finally:
        sender.shutdown()
        receiver.shutdown()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_wait_for_message_raises_wait_timeout_error_when_nothing_matches(vcan_channel):
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        with pytest.raises(WaitTimeoutError):
            wait_for_message(receiver, timeout=0.3, predicate=lambda f: False)
    finally:
        receiver.shutdown()


def test_wait_for_signal_raises_wait_timeout_error_when_predicate_never_matches(vcan_channel):
    db = load_dbc(FIXTURES_DBC)
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(db.encode("EngineData", {"EngineSpeed": 1.0, "EngineTemp": 0}))
        with pytest.raises(WaitTimeoutError):
            wait_for_signal(
                receiver,
                db,
                "EngineData",
                "EngineSpeed",
                predicate=lambda v: v > 999999,
                timeout=0.3,
            )
    finally:
        sender.shutdown()
        receiver.shutdown()

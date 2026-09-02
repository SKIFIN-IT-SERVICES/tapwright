# SPDX-License-Identifier: Apache-2.0

"""T2 test plan for RUN-10 — deterministic wait helpers (`TOOL-REQ-029`).

Implements #53. Oracle per `NFR-003`: no flakiness under normal CI timing
variance — proven here by exercising both the "found before timeout" and
"genuinely times out" paths for all three helpers against real `vcan`.

RUN-10 is a new loop, not one of the plan's original 37 — `TOOL-REQ-029`
was explicitly flagged as out of scope during RUN-01 (see `LOOPS.md`) and
never picked up since; see issue #53 for the full gap writeup.

`wait_for_message()`/`wait_for_signal()`/`wait_for_response()` all raise
one new `WaitTimeoutError` on timeout, matching this project's established
"no silent failure" convention (`hal.errors.CapabilityError`'s own
precedent; the BUS-05 `ASCReader` hardening fix).

Reuses `fixtures/databases/cyclic.dbc` (BUS-07's self-authored fixture) —
`EngineData` (frame ID `0x100`, `EngineSpeed`/`EngineTemp` signals) is
exactly the shape `wait_for_signal()`'s tests need; no new fixture
required.
"""

from __future__ import annotations

import pytest

from tapwright.dbc_arxml import load_dbc
from tapwright.hal import Frame, open_bus

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #53)")

pytestmark = pytest.mark.requires_vcan

FIXTURES_DBC = "fixtures/databases/cyclic.dbc"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_wait_for_message_returns_the_first_matching_frame(vcan_channel):
    from tapwright.runner.wait import wait_for_message

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


@SKIP
def test_wait_for_signal_returns_the_decoded_value_once_the_predicate_matches(vcan_channel):
    from tapwright.runner.wait import wait_for_signal

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


@SKIP
def test_wait_for_response_retries_the_callable_until_the_predicate_matches():
    from tapwright.runner.wait import wait_for_response

    calls = iter([1, 2, 3])
    result = wait_for_response(lambda: next(calls), predicate=lambda v: v == 3, timeout=1.0, poll_interval=0.01)
    assert result == 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_wait_for_message_returns_immediately_when_first_frame_already_matches(vcan_channel):
    from tapwright.runner.wait import wait_for_message

    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(Frame(arbitration_id=0x5, data=b"\x00"))
        frame = wait_for_message(receiver, timeout=1.0, predicate=lambda f: f.arbitration_id == 0x5)
        assert frame.arbitration_id == 0x5
    finally:
        sender.shutdown()
        receiver.shutdown()


@SKIP
def test_wait_for_signal_keeps_polling_past_an_unrelated_frame(vcan_channel):
    """An unrelated frame ID arriving first must not cause `wait_for_signal`
    to error or falsely resolve — exercises the "keep polling past
    non-matching arbitration IDs" path directly, not just "signal value
    not yet right."
    """
    from tapwright.runner.wait import wait_for_signal

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


@SKIP
def test_wait_for_response_honors_poll_interval_bounding_call_count():
    from tapwright.runner.wait import WaitTimeoutError, wait_for_response

    calls = []

    def call():
        calls.append(1)
        return False

    with pytest.raises(WaitTimeoutError):
        wait_for_response(call, predicate=lambda v: v is True, timeout=0.2, poll_interval=0.05)

    # ~4 polls expected at 0.2s/0.05s; a wide band tolerant of CI scheduler
    # jitter, proving it isn't busy-looping (which would be hundreds of calls).
    assert 1 <= len(calls) <= 10


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_wait_for_message_raises_wait_timeout_error_when_nothing_matches(vcan_channel):
    from tapwright.runner.wait import WaitTimeoutError, wait_for_message

    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        with pytest.raises(WaitTimeoutError):
            wait_for_message(receiver, timeout=0.3, predicate=lambda f: False)
    finally:
        receiver.shutdown()


@SKIP
def test_wait_for_signal_raises_wait_timeout_error_when_predicate_never_matches(vcan_channel):
    from tapwright.runner.wait import WaitTimeoutError, wait_for_signal

    db = load_dbc(FIXTURES_DBC)
    sender = open_bus(backend="socketcan", channel=vcan_channel)
    receiver = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        sender.send(db.encode("EngineData", {"EngineSpeed": 1.0, "EngineTemp": 0}))
        with pytest.raises(WaitTimeoutError):
            wait_for_signal(
                receiver, db, "EngineData", "EngineSpeed", predicate=lambda v: v > 999999, timeout=0.3
            )
    finally:
        sender.shutdown()
        receiver.shutdown()


@SKIP
def test_wait_for_response_raises_wait_timeout_error_when_predicate_never_matches():
    from tapwright.runner.wait import WaitTimeoutError, wait_for_response

    with pytest.raises(WaitTimeoutError):
        wait_for_response(lambda: False, predicate=lambda v: v is True, timeout=0.2, poll_interval=0.05)

# SPDX-License-Identifier: Apache-2.0

"""Deterministic wait helpers (RUN-10, `TOOL-REQ-029`).

`wait_for_message()`/`wait_for_signal()`/`wait_for_response()` replace
hand-rolled sleep/retry loops around a bus event or a diagnostic response
with a single call that raises `WaitTimeoutError` on timeout instead of
looping forever or silently giving up — the "no silent failure" convention
`hal.errors.CapabilityError` already established.

No library to wrap here per `AGENTS.md`'s reuse-first rule: this is
project-specific glue over `tapwright`'s own `hal.Frame`/
`dbc_arxml.CanDatabase` types, not a reimplementation of anything
`python-can`/`cantools`/`udsoncan` already provide.

`wait_for_message()` needs no artificial polling interval: `hal.Bus.recv()`
already blocks up to its own `timeout` argument, so each call either
returns a candidate frame or the deadline has passed — no `time.sleep()`
anywhere in that path. `wait_for_response()` polls an arbitrary callable
instead of a bus, which has no equivalent blocking primitive, so it uses
`poll_interval` between calls.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from tapwright.hal import Frame

if TYPE_CHECKING:
    from tapwright.dbc_arxml import CanDatabase
    from tapwright.hal import Bus

T = TypeVar("T")


class WaitTimeoutError(Exception):
    """Raised by `wait_for_message()`/`wait_for_signal()`/
    `wait_for_response()` when their condition never became true within
    the given timeout."""


def wait_for_message(
    bus: Bus,
    timeout: float,
    predicate: Callable[[Frame], bool] | None = None,
) -> Frame:
    """Block until a `Frame` satisfying `predicate` is received on `bus`,
    or raise `WaitTimeoutError` after `timeout` seconds.
    """
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WaitTimeoutError(f"no matching frame received within {timeout}s")
        frame = bus.recv(timeout=remaining)
        if frame is not None and (predicate is None or predicate(frame)):
            return frame


def wait_for_signal(
    bus: Bus,
    db: CanDatabase,
    message_name: str,
    signal_name: str,
    predicate: Callable[[Any], bool],
    timeout: float,
) -> Any:
    """Block until `message_name`'s `signal_name`, decoded via `db`,
    satisfies `predicate`, or raise `WaitTimeoutError` after `timeout`
    seconds.

    Filters incoming frames by `message_name`'s own arbitration ID (via
    `db.frame_id()`) before decoding, so a frame from an unrelated message
    can never be misattributed even if it happens to decode a same-named
    signal.
    """
    frame_id, is_extended_id = db.frame_id(message_name)

    def matches(frame: Frame) -> bool:
        if frame.arbitration_id != frame_id or frame.is_extended_id != is_extended_id:
            return False
        decoded = db.decode(frame)
        return signal_name in decoded and predicate(decoded[signal_name])

    frame = wait_for_message(bus, timeout=timeout, predicate=matches)
    return db.decode(frame)[signal_name]


def wait_for_response(
    call: Callable[[], T],
    predicate: Callable[[T], bool],
    timeout: float,
    poll_interval: float = 0.05,
) -> T:
    """Call `call()` repeatedly until its result satisfies `predicate`, or
    raise `WaitTimeoutError` after `timeout` seconds.
    """
    deadline = time.monotonic() + timeout
    while True:
        result = call()
        if predicate(result):
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WaitTimeoutError(f"predicate never matched within {timeout}s")
        time.sleep(min(poll_interval, remaining))

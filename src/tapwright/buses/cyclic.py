# SPDX-License-Identifier: Apache-2.0

"""Cyclic-send engine, DBC-driven cycle times (BUS-07, `TOOL-REQ-011`).

Single/multi-*message* cyclic stimulation — a configured signal transmits
at a fixed period on vcan. Not multi-node restbus simulation with
node-behavior scripting (`TOOL-REQ-012`, Should/Fast-follow, out of scope
here); see issue #49 for the scope correction against the plan's own loop
table title.

`hal.Bus.send_periodic()` already wraps `can.BusABC.send_periodic()` — the
only thing this module adds is deriving the period from an already-loaded
`CanDatabase`'s own declared cycle time, so a caller doesn't have to know
or restate it.
"""

from __future__ import annotations

from typing import Any

import can

from tapwright.dbc_arxml import CanDatabase
from tapwright.hal import Bus


def start_cyclic_from_dbc(
    bus: Bus,
    db: CanDatabase,
    message_name: str,
    signals: dict[str, Any],
    *,
    period: float | None = None,
) -> can.broadcastmanager.CyclicSendTaskABC:
    """Start cyclically sending `message_name`, encoded from `signals` via
    `db`, at `period` seconds — or, if `period` is omitted, at the
    database's own declared cycle time for that message.

    Raises `ValueError` if `period` is omitted and the database declares no
    cycle time for `message_name`, rather than silently defaulting to an
    arbitrary period.
    """
    if period is None:
        period = db.cycle_time(message_name)
        if period is None:
            raise ValueError(
                f"message {message_name!r} declares no cycle time in the database — "
                f"pass period= explicitly"
            )

    frame = db.encode(message_name, signals)
    return bus.send_periodic(frame, period)

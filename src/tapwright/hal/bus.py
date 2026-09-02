# SPDX-License-Identifier: Apache-2.0

"""The SocketCAN backend (TOOL-REQ-002), including Linux's vcan virtual
interface (TOOL-REQ-008), behind the L0 abstraction (TOOL-REQ-001).

Nothing above this module should ever branch on backend — swapping backend
is a config change to open_bus(), not an app-code change.
"""

from __future__ import annotations

import can

from .errors import BusClosedError, BusConfigError, CapabilityError
from .frame import Frame

_BACKENDS = {"socketcan"}


class Bus:
    """A backend-agnostic CAN/CAN-FD bus handle.

    Always constructed via open_bus() — never directly — so config
    validation runs before any OS-level resource is touched.
    """

    def __init__(self, raw_bus: can.BusABC, *, fd: bool) -> None:
        self._raw_bus = raw_bus
        self._fd = fd
        self._closed = False

    def send(self, frame: Frame) -> None:
        if self._closed:
            raise BusClosedError("cannot send on a bus after shutdown()")
        if frame.is_fd and not self._fd:
            raise CapabilityError("cannot send a CAN-FD frame on a bus opened without fd=True")
        message = can.Message(
            arbitration_id=frame.arbitration_id,
            data=frame.data,
            is_extended_id=frame.is_extended_id,
            is_fd=frame.is_fd,
        )
        self._raw_bus.send(message)

    def send_periodic(self, frame: Frame, period: float) -> can.broadcastmanager.CyclicSendTaskABC:
        """Transmit `frame` repeatedly every `period` seconds until stopped.

        TOOL-REQ-011 (basic single/multi-message cyclic stimulation), not
        multi-node restbus simulation (TOOL-REQ-012, out of scope). Wraps
        can.BusABC.send_periodic() rather than reimplementing periodic
        timing — see AGENTS.md §3. The returned task's only public method is
        stop(); no tapwright-specific wrapper is added around it since there
        is nothing left to bridge.
        """
        if self._closed:
            raise BusClosedError("cannot send on a bus after shutdown()")
        if period <= 0:
            raise ValueError(f"period must be positive, got {period!r}")
        if frame.is_fd and not self._fd:
            raise CapabilityError("cannot send a CAN-FD frame on a bus opened without fd=True")
        message = can.Message(
            arbitration_id=frame.arbitration_id,
            data=frame.data,
            is_extended_id=frame.is_extended_id,
            is_fd=frame.is_fd,
        )
        return self._raw_bus.send_periodic(message, period)

    def recv(self, timeout: float | None = None) -> Frame | None:
        if self._closed:
            raise BusClosedError("cannot recv on a bus after shutdown()")
        message = self._raw_bus.recv(timeout=timeout)
        if message is None:
            return None
        return Frame(
            arbitration_id=message.arbitration_id,
            data=bytes(message.data),
            is_extended_id=message.is_extended_id,
            is_fd=message.is_fd,
        )

    def shutdown(self) -> None:
        if self._closed:
            return
        self._raw_bus.shutdown()
        self._closed = True


def open_bus(*, backend: str, channel: str | None = None, fd: bool = False, **kwargs) -> Bus:
    """Open a CAN/CAN-FD bus through the tapwright HAL.

    Config is validated before any OS-level resource is touched: an unknown
    backend or a missing required field raises BusConfigError here, not an
    AttributeError/OSError surfaced from deep inside python-can.
    """
    if backend not in _BACKENDS:
        raise BusConfigError(
            f"unknown hal backend {backend!r} — supported backends: {sorted(_BACKENDS)}"
        )
    if not channel:
        raise BusConfigError("channel is required to open a socketcan bus")

    raw_bus = can.Bus(interface="socketcan", channel=channel, fd=fd, **kwargs)
    return Bus(raw_bus, fd=fd)

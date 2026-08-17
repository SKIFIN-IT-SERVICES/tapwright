# SPDX-License-Identifier: Apache-2.0

"""`udsoncan.connections.BaseConnection` adapter over DIAG-01's
`IsoTpTransport` (DIAG-02, `TOOL-REQ-022`'s client half).

This is the only code this loop writes. Once `udsoncan.Client` is handed a
`TapwrightIsoTpConnection`, every service method it already implements
(RDBI, WDBI, DTC read/clear, RoutineControl, SecurityAccess, session
control, ...) works through our transport automatically — none of that
service-level encode/decode logic is reimplemented here, per `AGENTS.md`'s
reuse rule ("`udsoncan`: MIT — reuse; wrap, don't rewrite").
"""

from __future__ import annotations

from udsoncan.connections import BaseConnection

from .isotp_transport import IsoTpTransport


class TapwrightIsoTpConnection(BaseConnection):
    """Bridges an `IsoTpTransport` to `udsoncan`'s connection interface.

    The transport is already running by the time this wraps it —
    `IsoTpTransport` starts serving in its own constructor, unlike
    `BaseConnection`'s expected "construct, then open()" lifecycle. `open()`
    here only flips this adapter's own `is_open()` flag; `close()` closes
    the underlying transport too, matching `IsoTpTransport`'s own
    never-restarts-after-close contract, so a closed connection stays
    closed rather than silently reusable.
    """

    def __init__(self, transport: IsoTpTransport, name: str | None = None) -> None:
        super().__init__(name)
        self._transport = transport
        self._is_open = True  # the transport is already running (see above)

    def open(self) -> TapwrightIsoTpConnection:
        self._is_open = True
        return self

    def close(self) -> None:
        if not self._is_open:
            return
        self._is_open = False
        self._transport.close()

    def is_open(self) -> bool:
        return self._is_open

    def specific_send(self, payload: bytes, timeout: float | None = None) -> None:
        self._transport.send(payload)

    def specific_wait_frame(self, timeout: float | None = None) -> bytes | None:
        return self._transport.recv(timeout=timeout)

    def empty_rxqueue(self) -> None:
        while self._transport.recv(timeout=0) is not None:
            pass

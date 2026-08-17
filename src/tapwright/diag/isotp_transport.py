# SPDX-License-Identifier: Apache-2.0

"""ISO-TP (ISO 15765-2) transport for L2, built on `tapwright.hal.Bus`
(DIAG-01, `TOOL-REQ-022`'s transport half).

Wraps `can-isotp`'s `isotp.TransportLayer` — the segmentation, reassembly,
and flow-control state machine is entirely the library's; this module's only
job is bridging it to `hal.Bus` via `_rxfn`/`_txfn` adapters that convert
between `hal.Frame` and `isotp.CanMessage`. That is a deliberate layering
choice: L2 sits on L0 (`docs/architecture.md`), so this does *not* open its
own `python-can` bus the way `tools/virtual_ecu` does (a shortcut taken
before HAL existed — see the scope note on issue #11).

`can-isotp` is MIT (verified, `licences.toml`) — no isolation question, only
`python-can` (LGPL-3.0, dependency-only per C-9) carries that.
"""

from __future__ import annotations

import isotp

from tapwright.hal import Bus, Frame

from .errors import TransportClosedError, TransportProtocolError


class IsoTpTransport:
    """A byte-stream ISO-TP transport over a `tapwright.hal.Bus`.

    `send`/`recv` deal in whole ISO-TP payloads (bytes) — the multi-frame
    handshake, if any, is invisible to the caller. Kept deliberately simple:
    per `docs/architecture.md` §4, this is not itself the request/response
    interception point a future fuzzer would hook into (that's DIAG-02's
    UDS client, one layer up), but its shape must not preclude one being
    added later without a breaking change.
    """

    def __init__(
        self,
        bus: Bus,
        *,
        rxid: int,
        txid: int,
        addressing_mode: isotp.AddressingMode = isotp.AddressingMode.Normal_11bits,
        params: dict[str, object] | None = None,
    ) -> None:
        self._bus = bus
        self._closed = False
        self._protocol_error: BaseException | None = None

        address = isotp.Address(addressing_mode, rxid=rxid, txid=txid)
        self._stack = isotp.TransportLayer(
            rxfn=self._rxfn,
            txfn=self._txfn,
            address=address,
            error_handler=self._on_protocol_error,
            params=params,
        )
        self._stack.start()

    def send(self, data: bytes) -> None:
        if self._closed:
            raise TransportClosedError("cannot send on a transport after close()")
        self._stack.send(bytes(data))

    def recv(self, timeout: float | None = None) -> bytes | None:
        """Block for up to `timeout` seconds for one fully reassembled ISO-TP
        payload. Returns None on timeout with no traffic — matches
        `hal.Bus.recv`'s own contract (NFR-003: a prompt, non-hanging
        timeout, not an exception).
        """
        if self._closed:
            raise TransportClosedError("cannot recv on a transport after close()")

        result = self._stack.recv(block=True, timeout=timeout)

        if self._protocol_error is not None:
            error, self._protocol_error = self._protocol_error, None
            raise TransportProtocolError(str(error)) from error

        return bytes(result) if result is not None else None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stack.stop()

    def __enter__(self) -> IsoTpTransport:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- hal.Bus <-> isotp.CanMessage bridge --------------------------------

    def _rxfn(self, timeout: float) -> isotp.CanMessage | None:
        try:
            frame = self._bus.recv(timeout=timeout)
        except Exception:
            # The bus was closed out from under this transport (e.g. by
            # another thread) while a receive was in flight. Reported to the
            # isotp background thread as "nothing arrived" rather than
            # letting an exception escape into its internals — the caller
            # already gets a clear TransportClosedError the next time it
            # calls send()/recv() itself, per test_underlying_hal_bus_closed_
            # does_not_hang_recv.
            return None
        if frame is None:
            return None
        return isotp.CanMessage(
            arbitration_id=frame.arbitration_id,
            data=frame.data,
            extended_id=frame.is_extended_id,
            is_fd=frame.is_fd,
        )

    def _txfn(self, message: isotp.CanMessage) -> None:
        self._bus.send(
            Frame(
                arbitration_id=message.arbitration_id,
                data=bytes(message.data),
                is_extended_id=message.extended_id,
                is_fd=message.is_fd,
            )
        )

    def _on_protocol_error(self, error: Exception) -> None:
        # Called from can-isotp's own background thread. Stashed rather than
        # raised here — there is no caller frame to raise into — and
        # re-raised from the next recv() call, per
        # test_out_of_sequence_consecutive_frame_is_reported_not_silently_
        # misassembled.
        self._protocol_error = error

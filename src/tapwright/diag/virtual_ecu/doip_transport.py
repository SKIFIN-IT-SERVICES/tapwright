# SPDX-License-Identifier: Apache-2.0

"""DoIP (ISO 13400) responder for the virtual ECU (DIAG-03, `TOOL-REQ-023`).

Dispatches to the *same* `ProtocolState` the CAN-side responder
(`transport.py`) uses — the UDS service logic is shared across both
transports, only the framing differs. Reuses `doipclient`'s own message
pack/unpack (`doipclient.messages`) and its TCP-framing state machine
(`doipclient.client.Parser`); the code here is the accept loop, the
routing-activation gate, and dispatch, not DoIP wire-format encode/decode.

Scope, per the reuse evaluation on issue #15: routing activation (any
`source_address` accepted — this is a test double, not a real gateway's
security boundary) and diagnostic message request/response. No TLS, no UDP
vehicle-discovery broadcast, no alive-check timer.
"""

from __future__ import annotations

import logging
import socket
import struct
import threading

from doipclient.client import Parser
from doipclient.messages import (
    DiagnosticMessage,
    DiagnosticMessageNegativeAcknowledgement,
    DiagnosticMessagePositiveAcknowledgement,
    RoutingActivationRequest,
    RoutingActivationResponse,
)

from .protocol import ProtocolState
from .scenario import Scenario

_logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 0x02
RECV_BUFFER_SIZE = 4096
SOCKET_POLL_TIMEOUT = 0.2

# The DoIPMessage base class declares neither .pack() nor .payload_type
# (each subclass adds them individually, without an abstract base
# requiring it) — this is the actual set of messages this responder ever
# packs, typed explicitly rather than against the looser base class.
_OutgoingMessage = (
    RoutingActivationResponse
    | DiagnosticMessagePositiveAcknowledgement
    | DiagnosticMessageNegativeAcknowledgement
    | DiagnosticMessage
)


def _pack_doip(message: _OutgoingMessage) -> bytes:
    """The generic 8-byte DoIP header (ISO 13400-2 Table 16) plus payload —
    matches `doipclient.client.DoIPClient._pack_doip` exactly, reimplemented
    rather than imported since that method is a leading-underscore internal
    of another package, not a stable public API to depend on.
    """
    payload = message.pack()
    header = struct.pack(
        "!BBHL", PROTOCOL_VERSION, 0xFF ^ PROTOCOL_VERSION, message.payload_type, len(payload)
    )
    return header + payload


class DoIPTransport:
    """Runs a `ProtocolState` behind a minimal DoIP-over-TCP responder."""

    def __init__(
        self,
        scenario: Scenario,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        ecu_logical_address: int = 0x0001,
    ) -> None:
        self._scenario = scenario
        self._host = host
        self._requested_port = port
        self._ecu_logical_address = ecu_logical_address
        self.protocol = ProtocolState(scenario)

        self._server_socket: socket.socket | None = None
        self._serve_thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._started = threading.Event()
        self._start_error: BaseException | None = None
        self.bound_port: int | None = None

    def start(self) -> None:
        if self._serve_thread is not None:
            raise RuntimeError("DoIPTransport is already started")

        self._stop_requested.clear()
        self._started.clear()
        self._start_error = None
        self.bound_port = None
        self._serve_thread = threading.Thread(target=self._run, daemon=True)
        self._serve_thread.start()

        if not self._started.wait(timeout=5.0):
            self._stop_requested.set()
            raise RuntimeError(
                f"virtual ECU DoIP responder failed to start on {self._host}:"
                f"{self._requested_port} within 5s"
            )
        if self._start_error is not None:
            self._serve_thread.join(timeout=2.0)
            self._serve_thread = None
            raise RuntimeError(
                f"virtual ECU DoIP responder failed to start: {self._start_error}"
            ) from self._start_error

    def stop(self) -> None:
        self._stop_requested.set()
        if self._serve_thread is not None:
            self._serve_thread.join(timeout=5.0)
            self._serve_thread = None

    def _run(self) -> None:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self._host, self._requested_port))
            server.listen(1)
            server.settimeout(SOCKET_POLL_TIMEOUT)
            self.bound_port = server.getsockname()[1]
            self._server_socket = server
        except Exception as exc:  # noqa: BLE001 - reported to start(), not swallowed
            self._start_error = exc
            self._started.set()
            return

        self._started.set()
        try:
            while not self._stop_requested.is_set():
                try:
                    conn, _addr = server.accept()
                except TimeoutError:
                    continue
                except OSError:
                    break  # socket closed out from under accept() during stop()
                try:
                    self._handle_connection(conn)
                except Exception:
                    # One misbehaving connection must not kill the whole
                    # responder — same defensive principle as
                    # ECUTransport._run (see transport.py).
                    _logger.exception("virtual ECU DoIP responder: unhandled error; continuing")
                finally:
                    conn.close()
        finally:
            server.close()
            self._server_socket = None

    def _handle_connection(self, conn: socket.socket) -> None:
        conn.settimeout(SOCKET_POLL_TIMEOUT)
        parser = Parser()
        activated = False

        while not self._stop_requested.is_set():
            try:
                data = conn.recv(RECV_BUFFER_SIZE)
            except TimeoutError:
                continue
            if not data:
                return  # client closed the connection

            message = parser.read_message(data)
            if message is None:
                continue

            if isinstance(message, RoutingActivationRequest):
                activated = True
                conn.sendall(
                    _pack_doip(
                        RoutingActivationResponse(
                            client_logical_address=message.source_address,
                            logical_address=self._ecu_logical_address,
                            response_code=RoutingActivationResponse.ResponseCode.Success,
                        )
                    )
                )
            elif isinstance(message, DiagnosticMessage):
                self._handle_diagnostic_message(conn, message, activated)
            # AliveCheckRequest and anything else: not handled (out of scope).

    def _handle_diagnostic_message(
        self, conn: socket.socket, message: DiagnosticMessage, activated: bool
    ) -> None:
        if not activated:
            conn.sendall(
                _pack_doip(
                    DiagnosticMessageNegativeAcknowledgement(
                        source_address=self._ecu_logical_address,
                        target_address=message.source_address,
                        nack_code=DiagnosticMessageNegativeAcknowledgement.NackCodes.InvalidSourceAddress,
                    )
                )
            )
            return

        conn.sendall(
            _pack_doip(
                DiagnosticMessagePositiveAcknowledgement(
                    source_address=self._ecu_logical_address,
                    target_address=message.source_address,
                    ack_code=0x00,
                )
            )
        )

        result = self.protocol.handle_request(bytes(message.user_data))
        if result.kind == "silence":
            return  # injected timeout: send nothing further
        if result.kind == "response":
            conn.sendall(
                _pack_doip(
                    DiagnosticMessage(
                        source_address=self._ecu_logical_address,
                        target_address=message.source_address,
                        user_data=result.data,
                    )
                )
            )
        elif result.kind == "malformed":
            # DoIP has no ISO-TP-style "truncated frame" concept — the
            # closest native analogue is a diagnostic message whose declared
            # length doesn't match its actual payload. Sending fewer bytes
            # than the message claims is left to a future hardening loop if
            # one needs it; this loop's failure-injection coverage is the
            # timeout/NRC kinds already exercised by the shared ProtocolState.
            _logger.debug("malformed injection requested over DoIP; no native analogue, skipping")

# SPDX-License-Identifier: Apache-2.0

"""Request/response interception, working across a process boundary
(DIAG-05, `TOOL-REQ-027`, ADR-004).

Per `docs/architecture.md` §4's second bullet — the one every prior DIAG
loop noted as "not built yet, but the API must not preclude it": `boofuzz`
(GPL-2.0) and CaringCaribou (GPL-3.0) can't be linked into a proprietary L4
in-process (C-9's reasoning extends to GPL), so a future Gallia-based
fuzzer, in a separate repository, has to talk to this connection across a
real process boundary — not a Python callback, not a thread.

`InterceptingConnection` wraps *any* existing
`udsoncan.connections.BaseConnection` (transport-agnostic by construction —
it doesn't know or care whether the wrapped connection is CAN or DoIP,
reusing DIAG-04's `open_connection()`'s "one client type either way"
property) and publishes every outbound request / inbound response to at
most one connected observer, over a plain TCP socket speaking
newline-delimited JSON:

    {"type": "request"|"response", "data": "<hex>"}

An observer replies with one line, either:

    {"action": "replace", "data": "<hex>"}   # substitute the payload
    {"action": "observe"}                     # (or anything else) pass through

With no observer connected — the default, overwhelmingly common case —
publishing costs one non-blocking `accept()` call that returns immediately:
no thread, no polling loop, no added latency on the hot path.
"""

from __future__ import annotations

import json
import logging
import socket
from typing import Any

from udsoncan.connections import BaseConnection

_logger = logging.getLogger(__name__)

# How long to wait for a connected observer's reply before assuming it's
# unresponsive and falling back to passthrough. A misbehaving external
# process must not become a denial-of-service on the diagnostic session.
REPLY_TIMEOUT = 2.0


class InterceptingConnection(BaseConnection):
    """Wraps `inner` (any `BaseConnection`), publishing every request and
    response to at most one connected observer.
    """

    def __init__(
        self,
        inner: BaseConnection,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        name: str | None = None,
    ) -> None:
        super().__init__(name)
        self._inner = inner
        self._host = host
        self._requested_port = port
        self._server: socket.socket | None = None
        self._client: socket.socket | None = None
        self._client_buffer = b""
        self.bound_port: int | None = None

    def open(self) -> InterceptingConnection:
        self._inner.open()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self._host, self._requested_port))
        server.listen(1)
        server.setblocking(False)  # accept() must never block the hot path

        self.bound_port = server.getsockname()[1]
        self._server = server
        return self

    def close(self) -> None:
        self._drop_client()
        if self._server is not None:
            self._server.close()
            self._server = None
        self._inner.close()

    def is_open(self) -> bool:
        # Deliberately not just `self._inner.is_open()`: some inner
        # connections (e.g. TapwrightIsoTpConnection) report themselves open
        # immediately at construction, since their underlying transport is
        # already running. If is_open() delegated to the inner connection
        # alone, udsoncan.Client.open()'s `if not self.conn.is_open():
        # self.conn.open()` guard would see True before this wrapper's own
        # open() -- which binds the listening socket -- ever ran, and the
        # observer socket would never come up. `self._server is not None`
        # is this wrapper's own state, set only inside open().
        return self._server is not None and self._inner.is_open()

    def empty_rxqueue(self) -> None:
        self._inner.empty_rxqueue()

    def specific_send(self, payload: bytes, timeout: float | None = None) -> None:
        published = self._publish("request", payload)
        self._inner.send(published, timeout=timeout)

    def specific_wait_frame(self, timeout: float | None = None) -> bytes | None:
        payload = self._inner.wait_frame(timeout=timeout)
        if payload is None:
            return None
        return self._publish("response", payload)

    # -- interception protocol -----------------------------------------

    def _ensure_client(self) -> socket.socket | None:
        """Return the connected observer, accepting a newly-pending one if
        there's no client yet. Never blocks: a non-blocking accept() either
        finds a connection immediately or doesn't, per `open()`'s own
        non-blocking listening socket.
        """
        if self._client is not None:
            return self._client
        assert self._server is not None, "InterceptingConnection.open() was not called"
        try:
            client, _addr = self._server.accept()
        except BlockingIOError:
            return None
        client.settimeout(REPLY_TIMEOUT)
        self._client = client
        self._client_buffer = b""
        return client

    def _drop_client(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except OSError:
                pass
        self._client = None
        self._client_buffer = b""

    def _read_line(self, client: socket.socket) -> str | None:
        while b"\n" not in self._client_buffer:
            chunk = client.recv(4096)
            if not chunk:
                return None  # observer closed the connection
            self._client_buffer += chunk
        line, _, self._client_buffer = self._client_buffer.partition(b"\n")
        return line.decode()

    def _publish(self, kind: str, payload: bytes) -> bytes:
        client = self._ensure_client()
        if client is None:
            return payload  # no observer attached: pure passthrough

        message = json.dumps({"type": kind, "data": payload.hex()}) + "\n"
        try:
            client.sendall(message.encode())
            line = self._read_line(client)
        except OSError:
            _logger.debug("interception observer connection error; dropping and passing through")
            self._drop_client()
            return payload

        if line is None:
            _logger.debug("interception observer disconnected; dropping and passing through")
            self._drop_client()
            return payload

        try:
            reply: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            _logger.debug(
                "interception observer sent malformed reply; dropping and passing through"
            )
            self._drop_client()
            return payload

        if reply.get("action") == "replace":
            try:
                return bytes.fromhex(reply["data"])
            except (KeyError, ValueError):
                _logger.debug(
                    "interception observer sent an invalid replace payload; passing through"
                )
                return payload

        return payload

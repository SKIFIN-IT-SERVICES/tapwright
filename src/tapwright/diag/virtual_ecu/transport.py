# SPDX-License-Identifier: Apache-2.0

"""Binds `protocol.py`'s pure UDS state machine to a real `vcan` interface.

Two send paths, deliberately kept separate:

- **Normal responses** go through `isotp.CanStack` — correct ISO-TP
  segmentation/reassembly, exactly what a real UDS client expects.
- **The "truncated" failure-injection kind** bypasses the ISO-TP stack
  entirely and writes one raw CAN frame directly via the underlying
  `python-can` bus: a First Frame that declares a length no Consecutive
  Frame ever completes. That is the deliberate malformation
  `test_injected_truncated_frame_is_actually_sent_on_the_bus` in the test
  plan checks for — `isotp.CanStack.send()` cannot produce it, because
  producing correct framing is the one thing that class exists to guarantee.

`python-can` is LGPL-3.0 and used here strictly as an installed dependency,
never vendored (C-9, FW-REQ-019) — see `licences.toml`. `can-isotp` is MIT.
"""

from __future__ import annotations

import logging
import threading

import can
import isotp

from .protocol import ProtocolResult, ProtocolState
from .scenario import Scenario

_logger = logging.getLogger(__name__)


class ECUTransport:
    """Runs `ProtocolState` against a live `vcan` interface until stopped."""

    def __init__(self, scenario: Scenario, channel: str) -> None:
        self._scenario = scenario
        self._channel = channel
        self.protocol = ProtocolState(scenario)
        self._bus: can.BusABC | None = None
        self._stack: isotp.CanStack | None = None
        self._serve_thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._started = threading.Event()
        self._start_error: BaseException | None = None

    def start(self) -> None:
        if self._serve_thread is not None:
            raise RuntimeError("ECUTransport is already started")

        self._stop_requested.clear()
        self._started.clear()
        self._start_error = None
        self._serve_thread = threading.Thread(target=self._run, daemon=True)
        self._serve_thread.start()

        # Bus/stack construction happens on the serve thread (python-can's
        # socketcan backend is not guaranteed thread-transferable once bound),
        # so start() blocks here until that thread confirms success or failure
        # — a caller must never observe "started" before the socket actually
        # exists, per test_unstartable_configuration_fails_fast_with_a_clear_error.
        if not self._started.wait(timeout=5.0):
            self._stop_requested.set()
            raise RuntimeError(
                f"virtual ECU failed to start on {self._channel!r} within 5s "
                f"(interface missing or already in use?)"
            )
        if self._start_error is not None:
            self._serve_thread.join(timeout=2.0)
            self._serve_thread = None
            raise RuntimeError(
                f"virtual ECU failed to start on {self._channel!r}: {self._start_error}"
            ) from self._start_error

    def stop(self) -> None:
        self._stop_requested.set()
        if self._serve_thread is not None:
            self._serve_thread.join(timeout=5.0)
            self._serve_thread = None

    def _run(self) -> None:
        try:
            self._bus = can.Bus(
                interface="socketcan", channel=self._channel, receive_own_messages=False
            )
            self._stack = isotp.CanStack(
                bus=self._bus,
                address=isotp.Address(
                    isotp.AddressingMode.Normal_11bits,
                    rxid=self._scenario.request_id,
                    txid=self._scenario.response_id,
                ),
                error_handler=lambda _error: None,
            )
            self._stack.start()
        except Exception as exc:  # noqa: BLE001 - reported to start(), not swallowed
            self._start_error = exc
            self._started.set()
            return

        self._started.set()
        try:
            while not self._stop_requested.is_set():
                try:
                    request = self._stack.recv(block=True, timeout=0.2)
                    if request is None:
                        continue
                    result = self.protocol.handle_request(bytes(request))
                    self._respond(result)
                except Exception:
                    # One malformed exchange must not silently kill the
                    # whole responder — a fixture that dies partway through
                    # a suite is worse than one that logs an anomaly and
                    # keeps serving the next request. Genuine ISO-TP protocol
                    # errors (bad frames, sequence errors) already go through
                    # `error_handler` above and never reach here; anything
                    # that does reach here is unexpected, hence logged loudly
                    # rather than swallowed like the expected-error path is.
                    _logger.exception(
                        "virtual ECU on %r: unhandled error serving one request; continuing",
                        self._channel,
                    )
        finally:
            self._stack.stop()
            self._bus.shutdown()
            self._stack = None
            self._bus = None

    def _respond(self, result: ProtocolResult) -> None:
        if result.kind == "silence":
            return
        if result.kind == "response":
            assert self._stack is not None
            self._stack.send(result.data)
            return
        if result.kind == "malformed":
            self._send_malformed_first_frame(result.declared_length)

    def _send_malformed_first_frame(self, declared_length: int) -> None:
        """Send one raw First Frame declaring `declared_length` bytes, with
        no Consecutive Frames to follow — deliberately incomplete, bypassing
        `isotp.CanStack` entirely (see module docstring).
        """
        assert self._bus is not None
        pci_high = 0x10 | ((declared_length >> 8) & 0x0F)
        pci_low = declared_length & 0xFF
        payload = bytes([pci_high, pci_low]) + bytes(6)
        message = can.Message(
            arbitration_id=self._scenario.response_id,
            data=payload,
            is_extended_id=False,
        )
        self._bus.send(message)

# SPDX-License-Identifier: Apache-2.0

"""T3 differential tests for DIAG-01 / TOOL-REQ-022's transport half — the
ISO-TP transport wrapping `can-isotp` over `tapwright.hal.Bus`.

Implements #11. Every case drives `IsoTpTransport` against a stock
`isotp.CanStack` used directly on a raw `python-can` bus on the same `vcan`
interface — that pairing is this loop's oracle, per the same
independently-authored-reference discipline used for INF-05 (see
`docs/inf-05-simulator-reuse-evaluation.md`).

## Scope notes (posted in full to #11; kept here as a pointer)

- Layering: built on `tapwright.hal.Bus` via `rxfn`/`txfn` adapters, not a
  raw `python-can` bus — unlike `tools/virtual_ecu` (INF-05), which took
  that shortcut before HAL existed. Flagged as a known inconsistency to
  revisit separately, not fixed here.
- Normal_11bits addressing only; extended/mixed addressing deferred.
- **L2 API-cleanliness note**: this transport is not `docs/architecture.md`
  §4's interception point (that's DIAG-02, one layer up) — noted so the
  constraint isn't rediscovered later. Kept simple enough for a future hook
  to sit between the UDS client and this transport without this class
  needing to change.
"""

from __future__ import annotations

import contextlib
import time

import can
import isotp
import pytest

from tapwright.diag.errors import TransportClosedError, TransportProtocolError
from tapwright.diag.isotp_transport import IsoTpTransport
from tapwright.hal import open_bus

pytestmark = pytest.mark.requires_vcan

# Arbitration IDs from *our transport's* perspective: it listens on
# DEFAULT_RXID, transmits on DEFAULT_TXID. A peer therefore listens on
# DEFAULT_TXID and transmits on DEFAULT_RXID.
DEFAULT_RXID = 0x7E0
DEFAULT_TXID = 0x7E8


@contextlib.contextmanager
def stock_isotp_peer(channel: str, *, rxid: int, txid: int):
    """A stock `isotp.CanStack` peer on a raw `python-can` bus — this file's
    oracle. `rxid`/`txid` are from the peer's own perspective.
    """
    bus = can.Bus(interface="socketcan", channel=channel, receive_own_messages=False)
    stack = isotp.CanStack(
        bus=bus,
        address=isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=rxid, txid=txid),
        error_handler=lambda _error: None,
    )
    stack.start()
    try:
        yield stack
    finally:
        stack.stop()
        bus.shutdown()


@contextlib.contextmanager
def our_transport(channel: str, *, rxid: int = DEFAULT_RXID, txid: int = DEFAULT_TXID):
    bus = open_bus(backend="socketcan", channel=channel)
    transport = IsoTpTransport(bus, rxid=rxid, txid=txid)
    try:
        yield transport
    finally:
        transport.close()
        bus.shutdown()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_single_frame_send_reaches_a_stock_isotp_peer(vcan_channel):
    """A payload small enough for one ISO-TP frame, sent through our
    transport, arrives byte-identical at a peer using isotp.CanStack
    directly — the oracle for the send direction.
    """
    payload = b"\x01\x02\x03"
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        transport.send(payload)
        received = peer.recv(block=True, timeout=2.0)
    assert received is not None
    assert bytes(received) == payload


def test_multi_frame_send_reaches_a_stock_isotp_peer(vcan_channel):
    """A payload beyond one frame, sent through our transport, triggers the
    First-Frame/Flow-Control/Consecutive-Frame handshake and arrives
    byte-identical at a stock isotp.CanStack peer.
    """
    payload = bytes(range(30))
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        transport.send(payload)
        received = peer.recv(block=True, timeout=2.0)
    assert received is not None
    assert bytes(received) == payload


def test_single_frame_received_from_a_stock_isotp_peer(vcan_channel):
    """Reverse direction: a stock isotp.CanStack peer sends a single-frame
    payload; our transport reassembles (trivially, for one frame) and
    returns it byte-identical.
    """
    payload = b"\xaa\xbb"
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        peer.send(payload)
        received = transport.recv(timeout=2.0)
    assert received == payload


def test_multi_frame_received_from_a_stock_isotp_peer(vcan_channel):
    """Reverse direction, multi-frame: a stock isotp.CanStack peer sends a
    payload requiring segmentation; our transport correctly handles flow
    control and reassembles it byte-identical.
    """
    payload = bytes(range(40))
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        peer.send(payload)
        received = transport.recv(timeout=2.0)
    assert received == payload


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_payload_exactly_at_single_frame_boundary(vcan_channel):
    """Exactly 7 bytes (classic CAN's single-frame max with a 1-byte PCI)
    round-trips as a single frame."""
    payload = bytes(range(7))
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        transport.send(payload)
        received = peer.recv(block=True, timeout=2.0)
    assert received is not None
    assert bytes(received) == payload


def test_payload_one_byte_over_single_frame_boundary_triggers_segmentation(vcan_channel):
    """8 bytes — one past the single-frame boundary — round-trips correctly,
    proving segmentation kicks in rather than truncating or erroring."""
    payload = bytes(range(8))
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        transport.send(payload)
        received = peer.recv(block=True, timeout=2.0)
    assert received is not None
    assert bytes(received) == payload


def test_large_payload_near_classic_isotp_maximum_round_trips(vcan_channel):
    """A payload approaching classic ISO-TP's 4095-byte maximum round-trips
    correctly — proves flow-control block-size/separation-time handling
    works across many consecutive frames, not just two or three."""
    payload = bytes(i % 256 for i in range(4000))
    with (
        stock_isotp_peer(vcan_channel, rxid=DEFAULT_TXID, txid=DEFAULT_RXID) as peer,
        our_transport(vcan_channel) as transport,
    ):
        transport.send(payload)
        received = peer.recv(block=True, timeout=10.0)
    assert received is not None
    assert bytes(received) == payload


def test_configurable_arbitration_ids_are_not_hardcoded(vcan_channel):
    """A transport opened with a non-default rx/tx ID pair works correctly
    — arbitration IDs are a construction-time config, matching HAL's own
    "swap is a config change" property carried up to L2."""
    rxid, txid = 0x123, 0x456
    payload = b"\x99"
    with (
        stock_isotp_peer(vcan_channel, rxid=txid, txid=rxid) as peer,
        our_transport(vcan_channel, rxid=rxid, txid=txid) as transport,
    ):
        transport.send(payload)
        received = peer.recv(block=True, timeout=2.0)
    assert received is not None
    assert bytes(received) == payload


def test_recv_times_out_cleanly_with_no_traffic(vcan_channel):
    """No traffic means a prompt timeout, not a hang — same boundary
    HAL-01/02 already established for hal.Bus.recv()."""
    with our_transport(vcan_channel) as transport:
        start = time.monotonic()
        result = transport.recv(timeout=0.2)
        elapsed = time.monotonic() - start
    assert result is None
    assert elapsed < 1.0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_out_of_sequence_consecutive_frame_is_reported_not_silently_misassembled(vcan_channel):
    """A peer sending Consecutive Frames with a wrong sequence number is a
    malformed transfer. Our transport must surface this as an error rather
    than silently assembling a wrong payload — the "silently wrong decode"
    failure mode the verification ladder exists to catch (plan §3).
    """
    with our_transport(vcan_channel) as transport:
        raw = can.Bus(interface="socketcan", channel=vcan_channel, receive_own_messages=False)
        try:
            # First Frame declaring a 12-byte payload (forces multi-frame).
            raw.send(
                can.Message(
                    arbitration_id=DEFAULT_RXID,
                    data=bytes([0x10, 0x0C]) + bytes(6),
                    is_extended_id=False,
                )
            )

            # Our transport, as receiver, must answer with Flow Control
            # before any Consecutive Frame is valid.
            flow_control = raw.recv(timeout=2.0)
            assert flow_control is not None
            assert flow_control.data[0] >> 4 == 0x3, "expected a Flow Control response"

            # Consecutive Frame with the wrong sequence number: the first CF
            # must be sequence 1; send 3 instead.
            raw.send(
                can.Message(
                    arbitration_id=DEFAULT_RXID,
                    data=bytes([0x23]) + bytes(range(6)),
                    is_extended_id=False,
                )
            )

            with pytest.raises(TransportProtocolError):
                transport.recv(timeout=2.0)
        finally:
            raw.shutdown()


def test_send_after_close_raises_clear_error(vcan_channel):
    """Using a transport handle after close() raises a clear, typed error —
    matching the HalError convention HAL-01 already established."""
    bus = open_bus(backend="socketcan", channel=vcan_channel)
    transport = IsoTpTransport(bus, rxid=DEFAULT_RXID, txid=DEFAULT_TXID)
    transport.close()
    try:
        with pytest.raises(TransportClosedError):
            transport.send(b"\x01")
    finally:
        bus.shutdown()


def test_underlying_hal_bus_closed_does_not_hang_recv(vcan_channel):
    """If the tapwright.hal.Bus underneath is closed while a recv() is
    in-flight, recv() returns or raises promptly rather than blocking
    forever — a hang here is a much worse failure mode than a clean error,
    since it doesn't even produce a readable pytest failure, just a stuck
    CI job."""
    bus = open_bus(backend="socketcan", channel=vcan_channel)
    transport = IsoTpTransport(bus, rxid=DEFAULT_RXID, txid=DEFAULT_TXID)
    bus.shutdown()

    start = time.monotonic()
    try:
        result = transport.recv(timeout=1.0)
        assert result is None
    except Exception:
        pass  # raising is also an acceptable outcome; hanging is not
    elapsed = time.monotonic() - start

    transport.close()
    assert elapsed < 3.0

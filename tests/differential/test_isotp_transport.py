# SPDX-License-Identifier: Apache-2.0

"""Test plan for DIAG-01 / TOOL-REQ-022's transport half — the ISO-TP
transport wrapping `can-isotp` over `tapwright.hal.Bus`.

Implements #11. T3 differential tier: every case drives our transport against
a stock `isotp.CanStack` used directly on a raw `python-can` bus on the same
`vcan` interface — that pairing is this loop's oracle, per the same
independently-authored-reference discipline used for INF-05 (see
`docs/inf-05-simulator-reuse-evaluation.md`). Our wrapper's segmented and
reassembled payloads must be byte-identical to what the library produces
when driven directly, in both directions.

TOOL-REQ-022's acceptance criterion (the half this loop owns): a UDS client
needs a working ISO-TP transport before DIAG-02 can read a DID at all.

## Scope notes (posted in full to #11; kept here as a pointer)

- Layering: this transport is built on `tapwright.hal.Bus` via small
  `rxfn`/`txfn` adapters bridging `hal.Frame` <-> `isotp.CanMessage`, *not*
  by opening its own `python-can` bus directly — unlike `tools/virtual_ecu`
  (INF-05), which took that shortcut before HAL existed. Flagged as a known
  inconsistency to revisit separately; out of this issue's blast radius.
- Addressing: Normal_11bits only, matching the virtual ECU's own addressing.
  Extended/mixed addressing is a follow-up, not required for DIAG-02.
- Flow-control state machine itself is `can-isotp`'s job, not reimplemented
  here — this loop tests that our HAL bridge doesn't corrupt or drop what
  the library already does correctly.
- **L2 API-cleanliness note** (test-plan skill step 5): this transport is
  not itself the request/response interception point `docs/architecture.md`
  §4 requires — that's DIAG-02's UDS client, sitting one layer up. Nothing
  here tests that interception point (it doesn't exist yet), but this
  transport's `send`/`recv` shape is kept simple and inspectable enough that
  a future interception hook can sit between the UDS client and this
  transport without this class needing to change — noted so it isn't
  rediscovered as a rewrite requirement later, per §4's own instruction.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #11)")

# ---------------------------------------------------------------------------
# Happy path — TOOL-REQ-022's transport half
# ---------------------------------------------------------------------------


@SKIP
def test_single_frame_send_reaches_a_stock_isotp_peer(vcan_channel):
    """A payload small enough for one ISO-TP frame (<=7 bytes on classic
    CAN), sent through our transport, arrives byte-identical at a peer using
    isotp.CanStack directly — the oracle for the send direction.
    """


@SKIP
def test_multi_frame_send_reaches_a_stock_isotp_peer(vcan_channel):
    """A payload beyond one frame, sent through our transport, triggers the
    First-Frame/Flow-Control/Consecutive-Frame handshake and arrives
    byte-identical at a stock isotp.CanStack peer — proves our HAL bridge
    doesn't break segmentation.
    """


@SKIP
def test_single_frame_received_from_a_stock_isotp_peer(vcan_channel):
    """Reverse direction: a stock isotp.CanStack peer sends a single-frame
    payload; our transport reassembles (trivially, for one frame) and
    returns it byte-identical.
    """


@SKIP
def test_multi_frame_received_from_a_stock_isotp_peer(vcan_channel):
    """Reverse direction, multi-frame: a stock isotp.CanStack peer sends a
    payload requiring segmentation; our transport correctly handles flow
    control and reassembles it byte-identical to what was sent.
    """


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_payload_exactly_at_single_frame_boundary(vcan_channel):
    """Exactly 7 bytes (classic CAN's single-frame max with a 1-byte PCI)
    round-trips as a single frame, not an unnecessary multi-frame sequence.
    """


@SKIP
def test_payload_one_byte_over_single_frame_boundary_triggers_segmentation(vcan_channel):
    """8 bytes — one byte past the single-frame boundary — correctly
    triggers multi-frame segmentation rather than truncating or erroring.
    """


@SKIP
def test_large_payload_near_classic_isotp_maximum_round_trips(vcan_channel):
    """A payload approaching classic ISO-TP's 4095-byte maximum round-trips
    correctly — proves flow-control block-size/separation-time handling
    works across many consecutive frames, not just two or three.
    """


@SKIP
def test_configurable_arbitration_ids_are_not_hardcoded(vcan_channel):
    """A transport opened with a non-default rx/tx ID pair works correctly
    — arbitration IDs are a construction-time config, matching HAL's own
    "swap is a config change" property (TOOL-REQ-001) carried up to L2.
    """


@SKIP
def test_recv_times_out_cleanly_with_no_traffic(vcan_channel):
    """Derived from NFR-003 (test determinism), same boundary HAL-01/02
    already established for its own recv(): no traffic means a prompt
    timeout, not a hang.
    """


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_out_of_sequence_consecutive_frame_is_reported_not_silently_misassembled(vcan_channel):
    """A peer sending Consecutive Frames with a wrong sequence number is a
    malformed transfer. Our transport must surface this as an error (or a
    dropped/None result with the error visible via a callback/log) rather
    than silently assembling a wrong payload — the "silently wrong decode"
    failure mode the whole verification ladder exists to catch (plan §3).
    """


@SKIP
def test_send_after_close_raises_clear_error(vcan_channel):
    """Using a transport handle after close() raises a clear, typed error —
    matching the HalError convention HAL-01 already established, not a bare
    exception surfaced from deep inside can-isotp.
    """


@SKIP
def test_underlying_hal_bus_closed_does_not_hang_recv(vcan_channel):
    """If the tapwright.hal.Bus underneath is closed while a recv() is
    in-flight (e.g. another thread calls bus.shutdown()), recv() returns or
    raises promptly rather than blocking forever — a hang here would be a
    much worse test-suite failure mode than a clean error, since it doesn't
    even produce a readable pytest failure, just a stuck CI job.
    """

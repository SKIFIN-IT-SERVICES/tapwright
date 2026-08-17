# SPDX-License-Identifier: Apache-2.0

"""Test plan for DIAG-03 / TOOL-REQ-023 — the DoIP transport: client via
`doipclient`, virtual ECU DoIP responder.

Implements #15. Unlike every `vcan`-gated loop since INF-05, DoIP runs over
plain TCP — these tests need no Linux kernel feature and are **not** marked
`requires_vcan`. They run, and can be genuinely red/green locally, on any
platform including this project's own Windows dev environment.

## Reuse findings (posted in full to #15; kept here as a pointer)

- `doipclient` ships its own official `udsoncan.connections.BaseConnection`
  adapter (`doipclient.connectors.DoIPClientUDSConnector`) — unlike
  DIAG-01/DIAG-02, this loop writes **no connection adapter**, only a thin
  factory (`open_doip_uds_client()`) wiring `doipclient.DoIPClient` + that
  connector + `udsoncan.Client`.
- No reusable DoIP *server* exists (the one candidate found, a 2020
  single-commit reference project, was rejected — same reasoning as
  INF-05's rejection of `lbenthins/ecu-simulator`). The virtual ECU's DoIP
  responder is new code, but it reuses `doipclient.messages`' pack/unpack
  for every DoIP message type and `doipclient.client.Parser` for TCP
  framing — and, critically, dispatches to the *same* `ProtocolState` the
  CAN-side virtual ECU already uses, so no UDS service logic is duplicated.

## Oracle

`doipclient.DoIPClient` + `doipclient.connectors.DoIPClientUDSConnector` +
`udsoncan.Client`, used directly — the reference stack, exactly mirroring
`uds_client_factory`'s role for the CAN-side loops. Since that connector is
entirely reused rather than written by us, the real risk in this loop is in
the *responder* (does our DoIP server speak the protocol correctly to a
real client implementation) — analogous to INF-05, where the oracle caught
ECU bugs, not client bugs.

## Scope notes

- **L2 API-cleanliness note**: `open_doip_uds_client()` returns a plain
  `udsoncan.Client`, the same type `open_uds_client()` (DIAG-02) returns —
  this *is* `docs/architecture.md` §4's "one client object, transport is a
  construction-time choice" property, now proven across two transports.
- No TLS, no UDP vehicle-discovery broadcast, no alive-check timer — none
  are needed to prove a DID read round-trips over DoIP; out of scope for
  this loop, addable later if a loop actually needs them (posted to #15).
"""

from __future__ import annotations

import pytest

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #15)")

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_read_did_via_our_doip_client_matches_oracle():
    """A DID read through open_doip_uds_client() returns the same value as
    the same read through doipclient's own reference stack — this loop's
    central proof.
    """


@SKIP
def test_write_then_read_did_round_trips_via_our_doip_client():
    """WDBI then RDBI through our DoIP client reflects the written value."""


@SKIP
def test_change_session_via_our_doip_client():
    """DiagnosticSessionControl through our DoIP client succeeds and a
    session-gated DID becomes readable afterward."""


@SKIP
def test_large_did_value_round_trips_via_our_doip_client():
    """DoIP diagnostic messages aren't ISO-TP-segmented — a payload well
    beyond ISO-TP's classic single-frame size still round-trips correctly
    as a single TCP-framed message, confirming no accidental truncation.
    """


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_routing_activation_is_required_before_diagnostic_message():
    """A client that skips routing activation and sends a diagnostic
    message directly is rejected (or ignored) by the responder, not
    silently dispatched to the UDS core — matches ISO 13400's activation
    gate, which real DoIP gateways enforce.
    """


@SKIP
def test_two_independent_doip_clients_do_not_interfere():
    """docs/architecture.md §4: "no hidden state that a second, concurrent
    test can't observe" — mirrors DIAG-02's analogous case for the CAN
    transport. Two separate open_doip_uds_client() connections against the
    same ECU don't share state.
    """


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_read_unconfigured_did_raises_negative_response_exception():
    """A DID the scenario never configured raises udsoncan's
    NegativeResponseException with the same NRC through both stacks."""


@SKIP
def test_connection_closed_raises_clear_error_on_further_use():
    """Using a client after its DoIP connection has been closed raises a
    clear error rather than hanging or silently no-op-ing."""


@SKIP
def test_request_timeout_raises_timeout_exception_via_our_doip_client():
    """A scenario-injected timeout (the virtual ECU's existing
    failure-injection mechanism, INF-05, shared across transports since
    both drive the same ProtocolState) produces udsoncan's TimeoutException
    through our DoIP client too.
    """

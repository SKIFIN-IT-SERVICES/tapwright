# SPDX-License-Identifier: Apache-2.0

"""Test plan for DIAG-02 / TOOL-REQ-022 (client half) — the UDS client over
the DIAG-01 ISO-TP transport.

Implements #13. T3 differential tier: `tapwright.diag.uds_client.open_uds_client()`
*is* `udsoncan.Client` (per `AGENTS.md`'s reuse rule) — the only code this
loop actually writes is `tapwright.diag.connection.TapwrightIsoTpConnection`,
the `BaseConnection` adapter bridging DIAG-01's `IsoTpTransport` to
`udsoncan`. The oracle is therefore a `udsoncan.Client` built with
`udsoncan`'s *own* `PythonIsoTpConnection` + `isotp.CanStack` directly on a
raw `python-can` bus — exactly the `uds_client_factory` fixture already
built for INF-05's differential tests (`tests/conftest.py`). Every case here
runs the same request through both stacks against the virtual ECU (#9) and
asserts identical results — proving our connection adapter is behaviourally
equivalent to udsoncan's own reference connection, not just "our client
agrees with itself."

## Scope notes (posted in full to #13; kept here as a pointer)

- **Narrower than full `TOOL-REQ-024`**: the virtual ECU doesn't implement
  RoutineControl (`0x31`) or ClearDiagnosticInformation (`0x14`) yet (#9's
  own scope note). Since the connection adapter makes every `udsoncan.Client`
  method work generically — no service-specific code lives in this loop —
  this loop proves that *plumbing* correctness even for unimplemented
  services: a request for one should cleanly yield a `serviceNotSupported`
  negative response through our stack, not a crash or hang. Full ECU-side
  RoutineControl/ClearDTC support is separate future work on #9.
- **L2 API-cleanliness note** (test-plan skill step 5): this is the first
  loop to touch `diag/`'s constrained public surface (`docs/architecture.md`
  §4, TOOL-REQ-027, ADR-004). `open_uds_client()` returns a plain
  `udsoncan.Client` — already a widely-wrappable, well-known object external
  tools already know how to subclass or intercept via its `.conn` attribute
  — so nothing here precludes adding a formal interception hook later. No
  interception-hook test exists today (none is required in v0.1 per §4's own
  text), but the constraint wasn't forgotten.
- T4 (property) coverage is a separate file:
  `tests/property/test_uds_client_properties.py` — DIAG-02's tier is T4 per
  `LOOPS.md`, which subsumes this T3 file, not replaces it.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #13)")

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_read_did_via_our_client_matches_oracle(vcan_channel, uds_client_factory):
    """A DID read through open_uds_client() (our connection adapter) returns
    the same value as the same read through udsoncan's own reference
    connection stack — this loop's central proof.
    """


@SKIP
def test_write_then_read_did_round_trips_via_our_client(vcan_channel, uds_client_factory):
    """WDBI then RDBI through our client reflects the written value —
    proves the write direction through our adapter, not just read.
    """


@SKIP
def test_change_session_via_our_client(vcan_channel, uds_client_factory):
    """DiagnosticSessionControl through our client succeeds and a
    session-gated DID becomes readable afterward."""


@SKIP
def test_read_dtc_information_via_our_client_matches_oracle(vcan_channel, uds_client_factory):
    """ReadDTCInformation through our client returns the same DTC list as
    the oracle stack."""


@SKIP
def test_security_access_unlock_via_our_client(vcan_channel, uds_client_factory):
    """request_seed/send_key through our client succeeds against the
    virtual ECU's configured security level."""


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_multi_frame_did_value_round_trips_via_our_client(vcan_channel, uds_client_factory):
    """A DID value beyond one ISO-TP frame reads correctly end-to-end
    through udsoncan.Client -> our connection adapter -> IsoTpTransport —
    proves segmentation survives the full stack, not just DIAG-01's own
    transport-level test.
    """


@SKIP
def test_two_independent_clients_do_not_interfere(vcan_channel):
    """docs/architecture.md §4: "no hidden state that a second, concurrent
    test can't observe." Two separate open_uds_client() instances against
    the same ECU don't share session/security state through some
    module-level global in our adapter.
    """


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_read_unconfigured_did_raises_negative_response_exception(vcan_channel, uds_client_factory):
    """A DID the scenario never configured raises udsoncan's
    NegativeResponseException with the same NRC through both stacks."""


@SKIP
def test_unsupported_service_yields_clean_negative_response_not_a_hang(vcan_channel):
    """RoutineControl (0x31) — a service the virtual ECU does not implement
    — still round-trips a clean serviceNotSupported negative response
    through our client, proving the adapter carries an arbitrary UDS
    exchange correctly rather than only the services the ECU happens to
    answer (see the scope note above).
    """


@SKIP
def test_connection_closed_raises_clear_error_on_further_use(vcan_channel):
    """Using a client after its connection has been closed raises a clear
    error rather than hanging or silently no-op-ing — matching
    IsoTpTransport's own TransportClosedError contract (DIAG-01), surfaced
    sensibly through the udsoncan connection layer.
    """


@SKIP
def test_request_timeout_raises_timeout_exception_via_our_client(vcan_channel, uds_client_factory):
    """A scenario-injected timeout (the virtual ECU's own failure-injection
    mechanism, INF-05) produces udsoncan's TimeoutException through our
    client, matching the oracle's behaviour for the same injected failure.
    """

# SPDX-License-Identifier: Apache-2.0

"""Test plan for INF-05 / TOOL-REQ-026 — the virtual UDS ECU responder.

Implements #9. T3 differential tier: every case in this file drives the
virtual ECU with a stock `udsoncan` client used directly, with no Tapwright
code in the request/response path. That is this loop's own oracle — per
`docs/inf-05-simulator-reuse-evaluation.md`, a `udsoncan` client completing a
session-control + RDBI exchange against our simulated ECU is what proves the
responder is honest about the ISO 14229 spec rather than merely consistent
with our own client (which would prove nothing: our client and our ECU could
agree with each other while both being wrong).

TOOL-REQ-026's acceptance criterion: *"A `pip install`-only user can run a
full read-DID round trip against a simulated ECU with zero hardware; this
target doubles as the CI test fixture and the GitHub Actions demo."*

Cases are stubbed with `@pytest.mark.skip` per PROCESS.md step 2 — this file
*is* the test plan; `tdd-develop` un-skips one case at a time. Imports of the
not-yet-existing implementation are kept inside each test body (not at module
level) so the file collects cleanly while everything is skipped.

## Scope notes flagged during planning (not silently dropped, not silently
## added — see test-plan skill step 3)

- **Service set is narrower than full TOOL-REQ-024.** This loop covers
  DiagnosticSessionControl (0x10), RDBI/WDBI (0x22/0x2E), ReadDTCInformation
  (0x19), and SecurityAccess *mechanics only* (0x27 request-seed/send-key,
  never derivation — C-10). RoutineControl (0x31) and the transfer/flash
  sequence (0x34-0x37) are deferred to a follow-up loop once DIAG-02 needs
  them — TOOL-REQ-026's acceptance criterion is a *read-DID round trip*,
  which this set satisfies; the fuller set is TOOL-REQ-024's job, not this
  loop's.
- **Failure injection is in scope for *this* loop**, not deferred to DIAG-09.
  DIAG-09 is the exhaustive hardening battery against the client; this loop
  only has to prove the ECU's injection knobs work at all (a configured NRC
  is actually returned, a configured timeout actually produces silence).
  That is TOOL-REQ-026's "doubles as ... CI test fixture" clause in practice:
  a fixture that can't misbehave on command can't be used to test how our own
  client handles misbehaviour.
- **Location:** `DEVELOPMENT-PLAN-L0-L3-AGENTIC.md` §4.1 places this at
  `tools/virtual_ecu/`; `docs/architecture.md`'s module table lists the
  "virtual-ECU responder" under `diag/` (L2). Resolved as `tools/virtual_ecu/`
  for the responder process itself — it is test/CI infrastructure, not part
  of the shipped client API surface `diag/` exposes — with a thin
  `virtual_ecu` pytest fixture (RUN-01) as the intended future bridge. Tests
  below import `tools.virtual_ecu`; revisit if `tdd-develop` finds a reason
  the split doesn't hold.
- **L2 API-cleanliness note (test-plan skill step 5):** these tests drive the
  virtual ECU with `udsoncan` used directly, over the wire, from outside
  Tapwright's own code — structurally the same shape DIAG-05's
  process-boundary interception requirement will need. Nothing here tests
  DIAG-05 itself, but the wire protocol this loop produces must stay plain
  UDS/ISO-TP with no Tapwright-specific coupling, so that a future external
  wrapper (Gallia-style) can talk to it too.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #9)")

# ---------------------------------------------------------------------------
# Happy path — TOOL-REQ-026's literal acceptance criterion
# ---------------------------------------------------------------------------


@SKIP
def test_read_did_round_trip_via_udsoncan(vcan_channel):
    """The acceptance criterion itself: a stock udsoncan client reads a
    configured DID from the virtual ECU with zero Tapwright code involved.
    """


@SKIP
def test_session_control_moves_to_extended_session(vcan_channel):
    """0x10 with subfunction 0x03 (extendedDiagnosticSession) succeeds and a
    subsequent session-gated request is then permitted.
    """


@SKIP
def test_write_did_round_trip_via_udsoncan(vcan_channel):
    """0x2E write, then 0x22 read of the same DID reflects the written value."""


@SKIP
def test_read_dtc_information_returns_configured_dtcs(vcan_channel):
    """0x19 (reportDTCByStatusMask) returns the DTC list the scenario configured."""


@SKIP
def test_security_access_request_seed_returns_configured_seed(vcan_channel):
    """0x27 subfunction 0x01 returns a seed. Mechanics only — the seed is a
    fixed scenario-configured value, never derived (C-10, DIAG-08's forbidden
    scan must stay clean of this file).
    """


@SKIP
def test_security_access_send_key_with_correct_key_unlocks(vcan_channel):
    """0x27 subfunction 0x02 with the scenario-configured "correct" key
    (an arbitrary test constant, not a derivation) succeeds.
    """


@SKIP
def test_scenario_config_selects_initial_session_and_did_values(vcan_channel):
    """The ECU's starting session and DID table are set by the scenario
    passed to it, not hardcoded — this is the "scenario-configurable" half
    of INF-05's goal.
    """


# ---------------------------------------------------------------------------
# Edge cases — boundary conditions TOOL-REQ-026 implies but doesn't spell out
# ---------------------------------------------------------------------------


@SKIP
def test_read_did_in_wrong_session_returns_correct_nrc(vcan_channel):
    """A DID gated to extended session, requested while still in the default
    session, returns the ISO 14229-correct NRC (conditionsNotCorrect, 0x22) —
    tdd-develop pins the exact code against the spec, not against convenience.
    """


@SKIP
def test_security_access_send_key_with_wrong_key_returns_invalid_key_nrc(vcan_channel):
    """0x27 subfunction 0x02 with an incorrect key returns NRC 0x35
    (invalidKey), and the session remains locked.
    """


@SKIP
def test_read_unconfigured_did_returns_request_out_of_range(vcan_channel):
    """0x22 against a DID the scenario never configured returns NRC 0x31
    (requestOutOfRange), not a crash and not a silently-wrong value.
    """


@SKIP
def test_write_read_only_did_is_rejected(vcan_channel):
    """0x2E against a DID marked read-only in the scenario is rejected with
    the correct NRC rather than silently accepted.
    """


@SKIP
def test_multi_frame_response_segments_correctly_over_isotp(vcan_channel):
    """A DID value larger than one ISO-TP single frame round-trips correctly
    — validates our can-isotp wiring, not can-isotp itself (that's DIAG-01's
    job; this test only proves the responder is plumbed through it correctly).
    """


@SKIP
def test_ecu_responds_on_scenario_configured_arbitration_ids(vcan_channel):
    """Request/response CAN IDs are a scenario setting, not a hardcoded pair
    — a scenario for a second simulated ECU on the same bus must be able to
    use different IDs without code changes.
    """


@SKIP
def test_repeated_round_trips_are_deterministic(vcan_channel):
    """NFR-003 (test determinism): the same request run 50 times in a row
    produces the same response every time, with no flakiness under normal CI
    timing variance. A flaky fixture is worse than no fixture, because it
    poisons every test that depends on it.
    """


# ---------------------------------------------------------------------------
# Error / failure-injection cases — the reason this loop exists rather than
# wrapping a happy-path-only simulator (see docs/inf-05-simulator-reuse-
# evaluation.md)
# ---------------------------------------------------------------------------


@SKIP
def test_injected_negative_response_code_overrides_otherwise_valid_request(vcan_channel):
    """Scenario configures a specific NRC (e.g. 0x7F <SID> 0x10,
    generalReject) to be returned for a given service regardless of an
    otherwise well-formed request. Proves the injection knob works, not that
    a client survives it (DIAG-09's job).
    """


@SKIP
def test_injected_timeout_produces_silence_within_client_timeout_window(vcan_channel):
    """Scenario configures a DID/service to go silent. udsoncan's own P2
    timeout fires — no response is sent within the configured window."""


@SKIP
def test_injected_truncated_frame_is_actually_sent_on_the_bus(vcan_channel):
    """Scenario forces a truncated/malformed ISO-TP frame onto vcan,
    deliberately bypassing correct segmentation. Confirms the injection
    mechanism can actually produce a malformed frame — DIAG-09 is responsible
    for testing that a *client* handles it gracefully; this test only proves
    the fixture can misbehave on command.
    """


@SKIP
def test_injected_oversized_response_exceeds_expected_length(vcan_channel):
    """Scenario forces a response payload longer than the DID's configured
    length. Validates the injection knob, per the note above."""


@SKIP
def test_failure_injection_is_scoped_to_its_configured_trigger_only(vcan_channel):
    """Injecting a failure for one DID/service does not leak into unrelated
    happy-path requests in the same session — injection state is scoped, not
    global, so a hardening test suite can compose multiple scenarios in one
    session without cross-contamination.
    """

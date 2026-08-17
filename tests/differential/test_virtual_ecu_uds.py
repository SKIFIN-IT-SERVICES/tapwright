# SPDX-License-Identifier: Apache-2.0

"""T3 differential tests for INF-05 / TOOL-REQ-026 — the virtual UDS ECU.

Implements #9. Every case here drives the virtual ECU with a stock
`udsoncan` client used directly (via the `uds_client_factory` fixture in
`tests/conftest.py`), with no Tapwright code in the request/response path.
That is this loop's own oracle — per
`docs/inf-05-simulator-reuse-evaluation.md`, a `udsoncan` client completing a
session-control + RDBI exchange against our simulated ECU is what proves the
responder is honest about the ISO 14229 spec rather than merely consistent
with our own client (which would prove nothing: our client and our ECU could
agree with each other while both being wrong).

TOOL-REQ-026's acceptance criterion: *"A `pip install`-only user can run a
full read-DID round trip against a simulated ECU with zero hardware; this
target doubles as the CI test fixture and the GitHub Actions demo."*

## Scope notes (posted in full to #9; kept here as a pointer, not repeated)

- Service set is narrower than full `TOOL-REQ-024`: `0x10`, `0x22`/`0x2E`,
  `0x19`, `0x27` mechanics-only. `0x31`/`0x34-0x37` deferred.
- Failure injection is in scope for *this* loop; DIAG-09 is the exhaustive
  client-hardening battery, this loop only proves the injection knobs work.
- **Location corrected during `tdd-develop`**: lives at
  `src/tapwright/diag/virtual_ecu/`, shipped with the package, not
  `tools/virtual_ecu/` — `TOOL-REQ-026` requires a `pip install`-only user to
  reach it. See the `inf-05-simulator-reuse-evaluation.md` companion note.
"""

from __future__ import annotations

import can
import pytest
from udsoncan.exceptions import NegativeResponseException, TimeoutException

from tapwright.diag.virtual_ecu import (
    DTC,
    DIDConfig,
    FailureInjection,
    Scenario,
    SecurityLevelConfig,
    VirtualECU,
)
from tapwright.diag.virtual_ecu.protocol import (
    NRC_CONDITIONS_NOT_CORRECT,
    NRC_INVALID_KEY,
    NRC_REQUEST_OUT_OF_RANGE,
    SESSION_EXTENDED,
)

pytestmark = pytest.mark.requires_vcan


# ---------------------------------------------------------------------------
# Happy path — TOOL-REQ-026's literal acceptance criterion
# ---------------------------------------------------------------------------


def test_read_did_round_trip_via_udsoncan(vcan_channel, uds_client_factory):
    """The acceptance criterion itself: a stock udsoncan client reads a
    configured DID from the virtual ECU with zero Tapwright code involved.
    """
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        response = client.read_data_by_identifier(0xF190)
    assert response.service_data.values[0xF190] == b"VIN1234567890123"


def test_session_control_moves_to_extended_session(vcan_channel, uds_client_factory):
    """0x10 with subfunction 0x03 (extendedDiagnosticSession) succeeds and a
    subsequent session-gated request is then permitted.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        client.change_session(SESSION_EXTENDED)
        response = client.read_data_by_identifier(0x1234)
    assert response.service_data.values[0x1234] == b"\x01"


def test_write_did_round_trip_via_udsoncan(vcan_channel, uds_client_factory):
    """0x2E write, then 0x22 read of the same DID reflects the written value."""
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        client.write_data_by_identifier(0x1234, b"\xff\xee")
        response = client.read_data_by_identifier(0x1234)
    assert response.service_data.values[0x1234] == b"\xff\xee"


def test_read_dtc_information_returns_configured_dtcs(vcan_channel, uds_client_factory):
    """0x19 (reportDTCByStatusMask) returns the DTC list the scenario configured."""
    scenario = Scenario(dtcs=[DTC(code=b"\x01\x23\x45", status=0x08)])
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        response = client.read_dtc_information(0x02, status_mask=0xFF)
    codes = {dtc.id for dtc in response.service_data.dtcs}
    assert 0x012345 in codes


def test_security_access_request_seed_returns_configured_seed(vcan_channel, uds_client_factory):
    """0x27 subfunction 0x01 returns a seed. Mechanics only — the seed is a
    fixed scenario-configured value, never derived (C-10, DIAG-08's forbidden
    scan must stay clean of this file).
    """
    scenario = Scenario(
        security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb\xcc\xdd", key=b"\x11\x22\x33\x44")}
    )
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        response = client.request_seed(1)
    assert response.service_data.seed == b"\xaa\xbb\xcc\xdd"


def test_security_access_send_key_with_correct_key_unlocks(vcan_channel, uds_client_factory):
    """0x27 subfunction 0x02 with the scenario-configured "correct" key
    (an arbitrary test constant, not a derivation) succeeds.
    """
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\x11\x22")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        client.request_seed(1)
        response = client.send_key(1, b"\x11\x22")
    assert response.positive


def test_scenario_config_selects_initial_session_and_did_values(vcan_channel, uds_client_factory):
    """The ECU's starting session and DID table are set by the scenario
    passed to it, not hardcoded — this is the "scenario-configurable" half
    of INF-05's goal.
    """
    scenario = Scenario(
        initial_session=SESSION_EXTENDED,
        dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)},
    )
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        # No change_session call — the ECU must already be in extended
        # session because the scenario said so.
        response = client.read_data_by_identifier(0x1234)
    assert response.service_data.values[0x1234] == b"\x01"


# ---------------------------------------------------------------------------
# Edge cases — boundary conditions TOOL-REQ-026 implies but doesn't spell out
# ---------------------------------------------------------------------------


def test_read_did_in_wrong_session_returns_correct_nrc(vcan_channel, uds_client_factory):
    """A DID gated to extended session, requested while still in the default
    session, returns the ISO 14229-correct NRC (conditionsNotCorrect, 0x22).
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        with pytest.raises(NegativeResponseException) as excinfo:
            client.read_data_by_identifier(0x1234)
    assert excinfo.value.response.code == NRC_CONDITIONS_NOT_CORRECT


def test_security_access_send_key_with_wrong_key_returns_invalid_key_nrc(
    vcan_channel, uds_client_factory
):
    """0x27 subfunction 0x02 with an incorrect key returns NRC 0x35
    (invalidKey), and the session remains locked.
    """
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\x11\x22")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        client.request_seed(1)
        with pytest.raises(NegativeResponseException) as excinfo:
            client.send_key(1, b"\x00\x00")
    assert excinfo.value.response.code == NRC_INVALID_KEY


def test_read_unconfigured_did_returns_request_out_of_range(vcan_channel, uds_client_factory):
    """0x22 against a DID the scenario never configured returns NRC 0x31
    (requestOutOfRange), not a crash and not a silently-wrong value.
    """
    scenario = Scenario()
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        with pytest.raises(NegativeResponseException) as excinfo:
            client.read_data_by_identifier(0x9999)
    assert excinfo.value.response.code == NRC_REQUEST_OUT_OF_RANGE


def test_write_read_only_did_is_rejected(vcan_channel, uds_client_factory):
    """0x2E against a DID marked read-only in the scenario is rejected with
    the correct NRC rather than silently accepted.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00", read_only=True)})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        with pytest.raises(NegativeResponseException) as excinfo:
            client.write_data_by_identifier(0x1234, b"\x01")
    assert excinfo.value.response.code == NRC_REQUEST_OUT_OF_RANGE


def test_multi_frame_response_segments_correctly_over_isotp(vcan_channel, uds_client_factory):
    """A DID value larger than one ISO-TP single frame round-trips correctly
    — validates our can-isotp wiring, not can-isotp itself (that's DIAG-01's
    job; this test only proves the responder is plumbed through it correctly).
    """
    long_value = bytes(range(40))  # far beyond a classic-CAN single frame's ~7 bytes
    scenario = Scenario(dids={0xABCD: DIDConfig(value=long_value)})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        response = client.read_data_by_identifier(0xABCD)
    assert response.service_data.values[0xABCD] == long_value


def test_ecu_responds_on_scenario_configured_arbitration_ids(vcan_channel, uds_client_factory):
    """Request/response CAN IDs are a scenario setting, not a hardcoded pair
    — a scenario for a second simulated ECU on the same bus must be able to
    use different IDs without code changes.
    """
    scenario = Scenario(
        request_id=0x123, response_id=0x456, dids={0x1234: DIDConfig(value=b"\x01")}
    )
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        response = client.read_data_by_identifier(0x1234)
    assert response.service_data.values[0x1234] == b"\x01"


def test_repeated_round_trips_are_deterministic(vcan_channel, uds_client_factory):
    """NFR-003 (test determinism): the same request run repeatedly produces
    the same response every time, with no flakiness under normal CI timing
    variance. A flaky fixture is worse than no fixture, because it poisons
    every test that depends on it.
    """
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        for _ in range(20):
            response = client.read_data_by_identifier(0xF190)
            assert response.service_data.values[0xF190] == b"VIN1234567890123"


# ---------------------------------------------------------------------------
# Error / failure-injection cases — the reason this loop exists rather than
# wrapping a happy-path-only simulator (see docs/inf-05-simulator-reuse-
# evaluation.md)
# ---------------------------------------------------------------------------


def test_injected_negative_response_code_overrides_otherwise_valid_request(
    vcan_channel, uds_client_factory
):
    """Scenario configures a specific NRC (e.g. 0x10, generalReject) to be
    returned for a given DID regardless of an otherwise well-formed request.
    Proves the injection knob works, not that a client survives it
    (DIAG-09's job).
    """
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(service_id=0x22, selector=0x1234, kind="nrc", nrc=0x10)
        ],
    )
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        with pytest.raises(NegativeResponseException) as excinfo:
            client.read_data_by_identifier(0x1234)
    assert excinfo.value.response.code == 0x10


def test_injected_timeout_produces_silence_within_client_timeout_window(
    vcan_channel, uds_client_factory
):
    """Scenario configures a DID/service to go silent. udsoncan's own P2
    timeout fires — no response is sent within the configured window."""
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[FailureInjection(service_id=0x22, selector=0x1234, kind="timeout")],
    )
    with VirtualECU(scenario, channel=vcan_channel):
        with uds_client_factory(scenario, vcan_channel, request_timeout=1.5) as client:
            with pytest.raises(TimeoutException):
                client.read_data_by_identifier(0x1234)


def test_injected_truncated_frame_is_actually_sent_on_the_bus(vcan_channel):
    """Scenario forces a truncated/malformed ISO-TP frame onto vcan,
    deliberately bypassing correct segmentation. Confirms the injection
    mechanism can actually produce a malformed frame — DIAG-09 is responsible
    for testing that a *client* handles it gracefully; this test only proves
    the fixture can misbehave on command. Listens at the raw CAN level rather
    than through udsoncan, since that is what "malformed" means here.
    """
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(service_id=0x22, selector=0x1234, kind="truncated", declared_length=42)
        ],
    )
    with VirtualECU(scenario, channel=vcan_channel):
        bus = can.Bus(interface="socketcan", channel=vcan_channel, receive_own_messages=False)
        try:
            # Trigger it: a raw single-frame RDBI request on the ECU's rxid.
            bus.send(
                can.Message(
                    arbitration_id=scenario.request_id,
                    data=bytes([0x03, 0x22, 0x12, 0x34]),
                    is_extended_id=False,
                )
            )
            frame = bus.recv(timeout=2.0)
            assert frame is not None, "no traffic observed — injection did not fire"
            assert frame.arbitration_id == scenario.response_id
            # First Frame PCI nibble is 0x1; declared length's high nibble in
            # byte 0's low bits, low byte in byte 1.
            assert frame.data[0] >> 4 == 0x1
            declared = ((frame.data[0] & 0x0F) << 8) | frame.data[1]
            assert declared == 42

            # And no Consecutive Frame follows within a reasonable window —
            # that omission is the whole point of "truncated".
            follow_up = bus.recv(timeout=0.5)
            assert follow_up is None or follow_up.data[0] >> 4 != 0x2
        finally:
            bus.shutdown()


def test_injected_oversized_response_exceeds_expected_length(vcan_channel, uds_client_factory):
    """Scenario forces a response payload longer than the DID's configured
    length. Validates the injection knob, per the note above.
    """
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(service_id=0x22, selector=0x1234, kind="oversized", extra_bytes=20)
        ],
    )
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        response = client.read_data_by_identifier(0x1234)
    assert response.service_data.values[0x1234] == b"\x01" + bytes(20)


def test_failure_injection_is_scoped_to_its_configured_trigger_only(
    vcan_channel, uds_client_factory
):
    """Injecting a failure for one DID/service does not leak into unrelated
    happy-path requests in the same session — injection state is scoped, not
    global, so a hardening test suite can compose multiple scenarios in one
    session without cross-contamination.
    """
    scenario = Scenario(
        dids={0x1111: DIDConfig(value=b"\x01"), 0x2222: DIDConfig(value=b"\x02")},
        failure_injections=[
            FailureInjection(service_id=0x22, selector=0x1111, kind="nrc", nrc=0x10)
        ],
    )
    with (
        VirtualECU(scenario, channel=vcan_channel),
        uds_client_factory(scenario, vcan_channel) as client,
    ):
        with pytest.raises(NegativeResponseException):
            client.read_data_by_identifier(0x1111)
        unaffected = client.read_data_by_identifier(0x2222)
    assert unaffected.service_data.values[0x2222] == b"\x02"

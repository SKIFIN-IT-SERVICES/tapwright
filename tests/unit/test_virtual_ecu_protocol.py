# SPDX-License-Identifier: Apache-2.0

"""T1 unit tests for the virtual ECU's protocol state machine (INF-05, #9).

The original test plan on #9 covered T2 (lifecycle) and T3 (differential,
against `udsoncan`) — both `vcan`-gated by design, since they test the whole
responder including its socket path. This file is an addition made during
`tdd-develop`, not a scope change: `protocol.py` was deliberately factored out
with no socket/thread/bus code in it specifically so its request/response
logic could be tested at T1, on every platform, including this project's own
non-Linux CI matrix legs and a contributor's Windows laptop — cheaper and
faster than the T3 suite, and it exercises the exact same code path (`tools/
virtual_ecu/transport.py` calls `ProtocolState.handle_request` directly).

These are genuine unit tests, not a substitute for the differential oracle on
#9: they check that our own logic does what we intended, not that it agrees
with the ISO 14229 spec the way a stock `udsoncan` client checks it. Both
tiers matter; this one just runs everywhere and runs fast.
"""

from __future__ import annotations

import pytest

from tapwright.diag.virtual_ecu.protocol import (
    NRC_CONDITIONS_NOT_CORRECT,
    NRC_INVALID_KEY,
    NRC_REQUEST_OUT_OF_RANGE,
    NRC_REQUEST_SEQUENCE_ERROR,
    NRC_SERVICE_NOT_SUPPORTED,
    NRC_SUB_FUNCTION_NOT_SUPPORTED,
    SESSION_DEFAULT,
    SESSION_EXTENDED,
    SID_DIAGNOSTIC_SESSION_CONTROL,
    SID_READ_DATA_BY_IDENTIFIER,
    SID_READ_DTC_INFORMATION,
    SID_SECURITY_ACCESS,
    SID_WRITE_DATA_BY_IDENTIFIER,
    ProtocolState,
)
from tapwright.diag.virtual_ecu.scenario import (
    DTC,
    DIDConfig,
    FailureInjection,
    Scenario,
    SecurityLevelConfig,
)


def negative(sid: int, nrc: int) -> bytes:
    return bytes([0x7F, sid, nrc])


def positive(sid: int, payload: bytes = b"") -> bytes:
    return bytes([sid + 0x40]) + payload


# ---------------------------------------------------------------------------
# DiagnosticSessionControl (0x10)
# ---------------------------------------------------------------------------


def test_session_control_moves_to_extended_session():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_DIAGNOSTIC_SESSION_CONTROL, SESSION_EXTENDED]))
    assert result.kind == "response"
    assert result.data[:2] == positive(SID_DIAGNOSTIC_SESSION_CONTROL, bytes([SESSION_EXTENDED]))
    assert state.session == SESSION_EXTENDED


def test_session_control_rejects_unknown_subfunction():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_DIAGNOSTIC_SESSION_CONTROL, 0x7E]))
    assert result.data == negative(SID_DIAGNOSTIC_SESSION_CONTROL, NRC_SUB_FUNCTION_NOT_SUPPORTED)
    assert state.session == SESSION_DEFAULT  # unchanged on rejection


def test_initial_session_comes_from_scenario():
    state = ProtocolState(Scenario(initial_session=SESSION_EXTENDED))
    assert state.session == SESSION_EXTENDED


# ---------------------------------------------------------------------------
# ReadDataByIdentifier (0x22)
# ---------------------------------------------------------------------------


def test_read_configured_did_returns_its_value():
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0xF1, 0x90]))
    assert result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\xf1\x90" + b"VIN1234567890123")


def test_read_unconfigured_did_returns_request_out_of_range():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.data == negative(SID_READ_DATA_BY_IDENTIFIER, NRC_REQUEST_OUT_OF_RANGE)


def test_read_did_gated_to_extended_session_rejected_in_default_session():
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.data == negative(SID_READ_DATA_BY_IDENTIFIER, NRC_CONDITIONS_NOT_CORRECT)


def test_read_did_gated_to_extended_session_succeeds_after_session_change():
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    state = ProtocolState(scenario)
    state.handle_request(bytes([SID_DIAGNOSTIC_SESSION_CONTROL, SESSION_EXTENDED]))
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\x12\x34\x01")


def test_read_did_ungated_available_in_any_session():
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.kind == "response"
    assert result.data[0] == SID_READ_DATA_BY_IDENTIFIER + 0x40


def test_read_did_multi_byte_value_round_trips_whole():
    """Values longer than one ISO-TP single frame are just bytes to the
    protocol layer — segmentation is transport.py's job. Confirms this layer
    doesn't truncate or otherwise mangle a long value.
    """
    long_value = bytes(range(20))
    scenario = Scenario(dids={0xABCD: DIDConfig(value=long_value)})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0xAB, 0xCD]))
    assert result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\xab\xcd" + long_value)


# ---------------------------------------------------------------------------
# WriteDataByIdentifier (0x2E)
# ---------------------------------------------------------------------------


def test_write_did_then_read_reflects_new_value():
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00")})
    state = ProtocolState(scenario)
    write_result = state.handle_request(
        bytes([SID_WRITE_DATA_BY_IDENTIFIER, 0x12, 0x34, 0xFF, 0xEE])
    )
    assert write_result.data == positive(SID_WRITE_DATA_BY_IDENTIFIER, b"\x12\x34")

    read_result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert read_result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\x12\x34\xff\xee")


def test_write_read_only_did_is_rejected():
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00", read_only=True)})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_WRITE_DATA_BY_IDENTIFIER, 0x12, 0x34, 0x01]))
    assert result.data == negative(SID_WRITE_DATA_BY_IDENTIFIER, NRC_REQUEST_OUT_OF_RANGE)
    # and the value must not have changed
    read_result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert read_result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\x12\x34\x00")


def test_write_unconfigured_did_is_rejected():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_WRITE_DATA_BY_IDENTIFIER, 0x99, 0x99, 0x01]))
    assert result.data == negative(SID_WRITE_DATA_BY_IDENTIFIER, NRC_REQUEST_OUT_OF_RANGE)


# ---------------------------------------------------------------------------
# ReadDTCInformation (0x19)
# ---------------------------------------------------------------------------


def test_read_dtc_information_returns_configured_dtcs():
    scenario = Scenario(
        dtcs=[DTC(code=b"\x01\x23\x45", status=0x08), DTC(code=b"\xab\xcd\xef", status=0x01)]
    )
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DTC_INFORMATION, 0x02, 0xFF]))
    assert result.data == positive(
        SID_READ_DTC_INFORMATION,
        b"\x02\xff" + b"\x01\x23\x45\x08" + b"\xab\xcd\xef\x01",
    )


def test_read_dtc_information_with_no_dtcs_returns_empty_list():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_READ_DTC_INFORMATION, 0x02, 0xFF]))
    assert result.data == positive(SID_READ_DTC_INFORMATION, b"\x02\xff")


def test_read_dtc_information_unsupported_subfunction_rejected():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_READ_DTC_INFORMATION, 0x99]))
    assert result.data == negative(SID_READ_DTC_INFORMATION, NRC_SUB_FUNCTION_NOT_SUPPORTED)


# ---------------------------------------------------------------------------
# SecurityAccess (0x27) — mechanics only; see protocol.py's module docstring
# ---------------------------------------------------------------------------


def test_request_seed_returns_configured_seed():
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\xcc\xdd")})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_SECURITY_ACCESS, 0x01]))
    assert result.data == positive(SID_SECURITY_ACCESS, b"\x01\xaa\xbb")


def test_send_key_with_correct_key_unlocks():
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\xcc\xdd")})
    state = ProtocolState(scenario)
    state.handle_request(bytes([SID_SECURITY_ACCESS, 0x01]))  # request seed first
    result = state.handle_request(bytes([SID_SECURITY_ACCESS, 0x02, 0xCC, 0xDD]))
    assert result.data == positive(SID_SECURITY_ACCESS, b"\x02")
    assert 1 in state.unlocked_levels


def test_send_key_with_wrong_key_returns_invalid_key():
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\xcc\xdd")})
    state = ProtocolState(scenario)
    state.handle_request(bytes([SID_SECURITY_ACCESS, 0x01]))
    result = state.handle_request(bytes([SID_SECURITY_ACCESS, 0x02, 0x00, 0x00]))
    assert result.data == negative(SID_SECURITY_ACCESS, NRC_INVALID_KEY)
    assert 1 not in state.unlocked_levels


def test_send_key_without_prior_request_seed_is_sequence_error():
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\xcc\xdd")})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_SECURITY_ACCESS, 0x02, 0xCC, 0xDD]))
    assert result.data == negative(SID_SECURITY_ACCESS, NRC_REQUEST_SEQUENCE_ERROR)


def test_security_access_unconfigured_level_not_supported():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([SID_SECURITY_ACCESS, 0x01]))
    assert result.data == negative(SID_SECURITY_ACCESS, NRC_SUB_FUNCTION_NOT_SUPPORTED)


def test_security_access_reserved_subfunctions_rejected():
    state = ProtocolState(Scenario())
    for subfunction in (0x00, 0x7F):
        result = state.handle_request(bytes([SID_SECURITY_ACCESS, subfunction]))
        assert result.data == negative(SID_SECURITY_ACCESS, NRC_SUB_FUNCTION_NOT_SUPPORTED)


# ---------------------------------------------------------------------------
# Unsupported service
# ---------------------------------------------------------------------------


def test_unsupported_service_returns_service_not_supported():
    state = ProtocolState(Scenario())
    result = state.handle_request(bytes([0x99, 0x01]))
    assert result.data == negative(0x99, NRC_SERVICE_NOT_SUPPORTED)


def test_empty_request_produces_silence_not_a_crash():
    state = ProtocolState(Scenario())
    result = state.handle_request(b"")
    assert result.kind == "silence"


# ---------------------------------------------------------------------------
# Failure injection — the reason this loop exists rather than wrapping a
# happy-path-only simulator (docs/inf-05-simulator-reuse-evaluation.md)
# ---------------------------------------------------------------------------


def test_injected_nrc_overrides_an_otherwise_valid_request():
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER, selector=0x1234, kind="nrc", nrc=0x10
            )
        ],
    )
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.data == negative(SID_READ_DATA_BY_IDENTIFIER, 0x10)


def test_injected_timeout_produces_silence():
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER, selector=0x1234, kind="timeout"
            )
        ],
    )
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.kind == "silence"


def test_injected_truncated_reports_malformed_with_declared_length():
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER,
                selector=0x1234,
                kind="truncated",
                declared_length=42,
            )
        ],
    )
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.kind == "malformed"
    assert result.declared_length == 42


def test_injected_oversized_pads_the_response():
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER,
                selector=0x1234,
                kind="oversized",
                extra_bytes=10,
            )
        ],
    )
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x12, 0x34]))
    assert result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\x12\x34\x01" + bytes(10))


def test_failure_injection_is_scoped_to_its_configured_trigger_only():
    """An injection for one DID must not fire for a different, unrelated one
    — the exact scenario this test plan flagged as the key isolation property.
    """
    scenario = Scenario(
        dids={
            0x1111: DIDConfig(value=b"\x01"),
            0x2222: DIDConfig(value=b"\x02"),
        },
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER, selector=0x1111, kind="nrc", nrc=0x10
            )
        ],
    )
    state = ProtocolState(scenario)

    injected = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x11, 0x11]))
    assert injected.data == negative(SID_READ_DATA_BY_IDENTIFIER, 0x10)

    unaffected = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x22, 0x22]))
    assert unaffected.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\x22\x22\x02")


def test_wildcard_injection_matches_any_selector_for_its_service():
    scenario = Scenario(
        dids={0x1111: DIDConfig(value=b"\x01"), 0x2222: DIDConfig(value=b"\x02")},
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER, selector=None, kind="nrc", nrc=0x10
            )
        ],
    )
    state = ProtocolState(scenario)
    for did_bytes in (b"\x11\x11", b"\x22\x22"):
        result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER]) + did_bytes)
        assert result.data == negative(SID_READ_DATA_BY_IDENTIFIER, 0x10)


def test_exact_injection_takes_priority_over_wildcard():
    scenario = Scenario(
        dids={0x1111: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER, selector=None, kind="nrc", nrc=0x10
            ),
            FailureInjection(
                service_id=SID_READ_DATA_BY_IDENTIFIER, selector=0x1111, kind="nrc", nrc=0x22
            ),
        ],
    )
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0x11, 0x11]))
    assert result.data == negative(SID_READ_DATA_BY_IDENTIFIER, 0x22)


@pytest.mark.parametrize("_i", range(20))
def test_repeated_round_trips_are_deterministic(_i):
    """NFR-003 (test determinism), at the layer where nondeterminism would
    actually originate if it existed — parametrized rather than a manual loop
    so a failure at one iteration reports which one, not just "it flaked".
    """
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    state = ProtocolState(scenario)
    result = state.handle_request(bytes([SID_READ_DATA_BY_IDENTIFIER, 0xF1, 0x90]))
    assert result.data == positive(SID_READ_DATA_BY_IDENTIFIER, b"\xf1\x90VIN1234567890123")

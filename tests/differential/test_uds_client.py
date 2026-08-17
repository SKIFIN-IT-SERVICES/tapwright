# SPDX-License-Identifier: Apache-2.0

"""T3 differential tests for DIAG-02 / TOOL-REQ-022 (client half) — the UDS
client over the DIAG-01 ISO-TP transport.

Implements #13. `open_uds_client()` *is* `udsoncan.Client` (per `AGENTS.md`'s
reuse rule) — the only code this loop writes is
`tapwright.diag.connection.TapwrightIsoTpConnection`, the `BaseConnection`
adapter bridging DIAG-01's `IsoTpTransport` to `udsoncan`. The oracle is
therefore a `udsoncan.Client` built with `udsoncan`'s *own*
`PythonIsoTpConnection` + `isotp.CanStack` directly on a raw `python-can`
bus — exactly the `uds_client_factory` fixture already built for INF-05
(`tests/conftest.py`). Every applicable case runs the same request through
both stacks against the virtual ECU (#9) and asserts identical results.

## Scope notes (posted in full to #13; kept here as a pointer)

- Narrower than full `TOOL-REQ-024`: the virtual ECU doesn't implement
  RoutineControl (`0x31`) or ClearDiagnosticInformation (`0x14`) yet (#9's
  own deferral). Since the connection adapter makes every `udsoncan.Client`
  method work generically, this loop proves *plumbing* correctness for an
  unimplemented service too (a clean negative response, not a hang).
- **L2 API-cleanliness note**: first loop touching `diag/`'s constrained
  public surface (`docs/architecture.md` §4). `open_uds_client()` returns a
  plain `udsoncan.Client` — already externally wrappable — so the
  interception-hook constraint isn't precluded, just not built (not
  required in v0.1 per §4's own text).
- T4 (property) coverage is `tests/property/test_uds_client_properties.py`
  — DIAG-02's declared tier is T4, which subsumes this T3 file.
"""

from __future__ import annotations

import contextlib

import pytest
from udsoncan.exceptions import NegativeResponseException, TimeoutException

from tapwright.diag.uds_client import open_uds_client
from tapwright.diag.virtual_ecu import (
    DTC,
    DIDConfig,
    FailureInjection,
    Scenario,
    SecurityLevelConfig,
    VirtualECU,
)
from tapwright.diag.virtual_ecu.protocol import (
    NRC_REQUEST_OUT_OF_RANGE,
    NRC_SERVICE_NOT_SUPPORTED,
    SESSION_EXTENDED,
)
from tapwright.hal import open_bus

pytestmark = pytest.mark.requires_vcan

START_ROUTINE = 0x01


@contextlib.contextmanager
def our_client(scenario: Scenario, channel: str, raw_did_codec, **client_kwargs):
    """`open_uds_client()`'s client, wired against `scenario`'s virtual ECU
    — this file's "our stack", paired against `uds_client_factory`'s
    oracle stack in every applicable case.
    """
    bus = open_bus(backend="socketcan", channel=channel)
    data_identifiers = {**dict.fromkeys(scenario.dids, raw_did_codec), "default": raw_did_codec}
    config = {"data_identifiers": data_identifiers, **client_kwargs.pop("config_overrides", {})}
    client = open_uds_client(
        bus,
        rxid=scenario.response_id,
        txid=scenario.request_id,
        config=config,
        **client_kwargs,
    )
    try:
        with client:
            yield client
    finally:
        bus.shutdown()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_read_did_via_our_client_matches_oracle(vcan_channel, uds_client_factory, raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with VirtualECU(scenario, channel=vcan_channel):
        with uds_client_factory(scenario, vcan_channel) as oracle_client:
            oracle_value = oracle_client.read_data_by_identifier(0xF190).service_data.values[0xF190]
        with our_client(scenario, vcan_channel, raw_did_codec) as client:
            our_value = client.read_data_by_identifier(0xF190).service_data.values[0xF190]
    assert our_value == oracle_value == b"VIN1234567890123"


def test_write_then_read_did_round_trips_via_our_client(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        our_client(scenario, vcan_channel, raw_did_codec) as client,
    ):
        client.write_data_by_identifier(0x1234, b"\xff\xee")
        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result == b"\xff\xee"


def test_change_session_via_our_client(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        our_client(scenario, vcan_channel, raw_did_codec) as client,
    ):
        client.change_session(SESSION_EXTENDED)
        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result == b"\x01"


def test_read_dtc_information_via_our_client_matches_oracle(
    vcan_channel, uds_client_factory, raw_did_codec
):
    scenario = Scenario(dtcs=[DTC(code=b"\x01\x23\x45", status=0x08)])
    with VirtualECU(scenario, channel=vcan_channel):
        with uds_client_factory(scenario, vcan_channel) as oracle_client:
            oracle_dtcs = {
                dtc.id
                for dtc in oracle_client.read_dtc_information(
                    0x02, status_mask=0xFF
                ).service_data.dtcs
            }
        with our_client(scenario, vcan_channel, raw_did_codec) as client:
            our_dtcs = {
                dtc.id
                for dtc in client.read_dtc_information(0x02, status_mask=0xFF).service_data.dtcs
            }
    assert our_dtcs == oracle_dtcs == {0x012345}


def test_security_access_unlock_via_our_client(vcan_channel, raw_did_codec):
    scenario = Scenario(security_levels={1: SecurityLevelConfig(seed=b"\xaa\xbb", key=b"\x11\x22")})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        our_client(scenario, vcan_channel, raw_did_codec) as client,
    ):
        client.request_seed(1)
        response = client.send_key(1, b"\x11\x22")
    assert response.positive


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_multi_frame_did_value_round_trips_via_our_client(vcan_channel, raw_did_codec):
    long_value = bytes(range(40))
    scenario = Scenario(dids={0xABCD: DIDConfig(value=long_value)})
    with (
        VirtualECU(scenario, channel=vcan_channel),
        our_client(scenario, vcan_channel, raw_did_codec) as client,
    ):
        result = client.read_data_by_identifier(0xABCD).service_data.values[0xABCD]
    assert result == long_value


def test_two_independent_clients_do_not_interfere(vcan_channel, raw_did_codec):
    """docs/architecture.md §4: "no hidden state that a second, concurrent
    test can't observe." Sequential rather than truly concurrent (avoids
    threading complexity in the test itself), but still proves no
    module-level/class-level state leaks between independently constructed
    client stacks.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    with VirtualECU(scenario, channel=vcan_channel):
        with our_client(scenario, vcan_channel, raw_did_codec) as client_a:
            result_a = client_a.read_data_by_identifier(0x1234).service_data.values[0x1234]
        with our_client(scenario, vcan_channel, raw_did_codec) as client_b:
            result_b = client_b.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result_a == result_b == b"\x01"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_read_unconfigured_did_raises_negative_response_exception(
    vcan_channel, uds_client_factory, raw_did_codec
):
    scenario = Scenario()
    with VirtualECU(scenario, channel=vcan_channel):
        with uds_client_factory(scenario, vcan_channel) as oracle_client:
            with pytest.raises(NegativeResponseException) as oracle_exc:
                oracle_client.read_data_by_identifier(0x9999)
        with our_client(scenario, vcan_channel, raw_did_codec) as client:
            with pytest.raises(NegativeResponseException) as our_exc:
                client.read_data_by_identifier(0x9999)
    assert our_exc.value.response.code == oracle_exc.value.response.code == NRC_REQUEST_OUT_OF_RANGE


def test_unsupported_service_yields_clean_negative_response_not_a_hang(vcan_channel, raw_did_codec):
    """RoutineControl — a service the virtual ECU does not implement — still
    round-trips a clean serviceNotSupported negative response through our
    client, proving the adapter carries an arbitrary UDS exchange correctly
    rather than only the services the ECU happens to answer.
    """
    scenario = Scenario()
    with (
        VirtualECU(scenario, channel=vcan_channel),
        our_client(scenario, vcan_channel, raw_did_codec) as client,
    ):
        with pytest.raises(NegativeResponseException) as excinfo:
            client.routine_control(0x0203, START_ROUTINE)
    assert excinfo.value.response.code == NRC_SERVICE_NOT_SUPPORTED


def test_connection_closed_raises_clear_error_on_further_use(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    bus = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        with VirtualECU(scenario, channel=vcan_channel):
            client = open_uds_client(
                bus,
                rxid=scenario.response_id,
                txid=scenario.request_id,
                config={"data_identifiers": dict.fromkeys(scenario.dids, raw_did_codec)},
            )
            client.open()
            client.close()
            with pytest.raises(RuntimeError):
                client.read_data_by_identifier(0x1234)
    finally:
        bus.shutdown()


def test_request_timeout_raises_timeout_exception_via_our_client(vcan_channel, raw_did_codec):
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[FailureInjection(service_id=0x22, selector=0x1234, kind="timeout")],
    )
    with VirtualECU(scenario, channel=vcan_channel):
        with our_client(scenario, vcan_channel, raw_did_codec, request_timeout=1.5) as client:
            with pytest.raises(TimeoutException):
                client.read_data_by_identifier(0x1234)

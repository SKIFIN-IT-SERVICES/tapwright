# SPDX-License-Identifier: Apache-2.0

"""T3 differential tests for DIAG-03 / TOOL-REQ-023 — the DoIP transport:
client via `doipclient`, virtual ECU DoIP responder.

Implements #15. Unlike every `vcan`-gated loop since INF-05, DoIP runs over
plain TCP — these tests need no Linux kernel feature and are **not** marked
`requires_vcan`. They run, and can be genuinely red/green locally, on any
platform including this project's own Windows dev environment.

## Reuse findings (posted in full to #15; kept here as a pointer)

- `doipclient` ships its own official `udsoncan.connections.BaseConnection`
  adapter (`doipclient.connectors.DoIPClientUDSConnector`) — this loop
  writes **no connection adapter**, only a thin factory
  (`open_doip_uds_client()`) wiring `doipclient.DoIPClient` + that
  connector + `udsoncan.Client`.
- No reusable DoIP server exists (evaluated and rejected, same reasoning as
  INF-05's ECU-simulator rejection). The virtual ECU's DoIP responder is new
  code but reuses `doipclient.messages`' pack/unpack and
  `doipclient.client.Parser`'s TCP framing, and dispatches to the *same*
  `ProtocolState` the CAN-side virtual ECU already uses.

## Oracle

`doipclient.DoIPClient` + `doipclient.connectors.DoIPClientUDSConnector` +
`udsoncan.Client`, used directly — mirroring `uds_client_factory`'s role
for the CAN-side loops. Built locally as `oracle_client()` below (a
`uds_client_factory`-shaped helper doesn't already exist for DoIP, so this
file defines its own, the DoIP-transport twin).
"""

from __future__ import annotations

import contextlib

import pytest
from doipclient import DoIPClient
from doipclient.connectors import DoIPClientUDSConnector
from udsoncan.client import Client
from udsoncan.configs import default_client_config
from udsoncan.exceptions import NegativeResponseException, TimeoutException

from tapwright.diag.doip_client import open_doip_uds_client
from tapwright.diag.virtual_ecu import DIDConfig, DoIPVirtualECU, FailureInjection, Scenario
from tapwright.diag.virtual_ecu.protocol import NRC_REQUEST_OUT_OF_RANGE, SESSION_EXTENDED

ECU_HOST = "127.0.0.1"
ECU_LOGICAL_ADDRESS = 0x0001
CLIENT_LOGICAL_ADDRESS = 0xE00


@contextlib.contextmanager
def running_ecu(scenario: Scenario):
    with DoIPVirtualECU(scenario, host=ECU_HOST, ecu_logical_address=ECU_LOGICAL_ADDRESS) as ecu:
        yield ecu.port


def _config(scenario: Scenario, raw_did_codec) -> dict:
    return {
        "data_identifiers": {
            **dict.fromkeys(scenario.dids, raw_did_codec),
            "default": raw_did_codec,
        },
    }


@contextlib.contextmanager
def our_client(port: int, scenario: Scenario, raw_did_codec, **client_kwargs):
    with open_doip_uds_client(
        ECU_HOST,
        ECU_LOGICAL_ADDRESS,
        tcp_port=port,
        client_logical_address=CLIENT_LOGICAL_ADDRESS,
        config=_config(scenario, raw_did_codec),
        **client_kwargs,
    ) as client:
        yield client


@contextlib.contextmanager
def oracle_client(port: int, scenario: Scenario, raw_did_codec, **client_kwargs):
    """`doipclient` used directly, with no Tapwright code in the path —
    this file's own DoIP-transport twin of `uds_client_factory`.
    """
    doip_layer = DoIPClient(
        ECU_HOST,
        ECU_LOGICAL_ADDRESS,
        tcp_port=port,
        client_logical_address=CLIENT_LOGICAL_ADDRESS,
    )
    connection = DoIPClientUDSConnector(doip_layer, close_connection=True)
    config = dict(default_client_config)
    config.update(_config(scenario, raw_did_codec))
    with Client(connection, config=config, **client_kwargs) as client:
        yield client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_read_did_via_our_doip_client_matches_oracle(raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with running_ecu(scenario) as port:
        with oracle_client(port, scenario, raw_did_codec) as oracle:
            oracle_value = oracle.read_data_by_identifier(0xF190).service_data.values[0xF190]
        with our_client(port, scenario, raw_did_codec) as client:
            our_value = client.read_data_by_identifier(0xF190).service_data.values[0xF190]
    assert our_value == oracle_value == b"VIN1234567890123"


def test_write_then_read_did_round_trips_via_our_doip_client(raw_did_codec):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00")})
    with running_ecu(scenario) as port, our_client(port, scenario, raw_did_codec) as client:
        client.write_data_by_identifier(0x1234, b"\xff\xee")
        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result == b"\xff\xee"


def test_change_session_via_our_doip_client(raw_did_codec):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    with running_ecu(scenario) as port, our_client(port, scenario, raw_did_codec) as client:
        client.change_session(SESSION_EXTENDED)
        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result == b"\x01"


def test_large_did_value_round_trips_via_our_doip_client(raw_did_codec):
    """DoIP diagnostic messages aren't ISO-TP-segmented — a payload well
    beyond ISO-TP's classic single-frame size still round-trips correctly
    as a single TCP-framed message.
    """
    large_value = bytes(i % 256 for i in range(500))
    scenario = Scenario(dids={0xABCD: DIDConfig(value=large_value)})
    with running_ecu(scenario) as port, our_client(port, scenario, raw_did_codec) as client:
        result = client.read_data_by_identifier(0xABCD).service_data.values[0xABCD]
    assert result == large_value


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_routing_activation_is_required_before_diagnostic_message():
    """A client that skips routing activation and sends a diagnostic
    message directly is rejected (our responder answers with a Negative
    Acknowledgement), not silently dispatched to the UDS core.
    `doipclient`'s own `send_diagnostic()` blocks for the ack/nack itself
    and raises `OSError` on a negative one — caught here rather than in the
    originally-planned `receive_diagnostic()` timeout, once this branch's
    local run (real red/green, no `vcan` needed for DoIP) showed that's
    where the rejection actually surfaces.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    with running_ecu(scenario) as port:
        doip_layer = DoIPClient(
            ECU_HOST,
            ECU_LOGICAL_ADDRESS,
            tcp_port=port,
            client_logical_address=CLIENT_LOGICAL_ADDRESS,
            activation_type=None,  # skip the automatic routing activation
        )
        try:
            with pytest.raises(OSError, match="negative acknowledge"):
                doip_layer.send_diagnostic(bytearray([0x22, 0x12, 0x34]))
        finally:
            doip_layer.close()


def test_two_independent_doip_clients_do_not_interfere(raw_did_codec):
    """docs/architecture.md §4: "no hidden state that a second, concurrent
    test can't observe" — mirrors DIAG-02's analogous case.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    with running_ecu(scenario) as port:
        with our_client(port, scenario, raw_did_codec) as client_a:
            result_a = client_a.read_data_by_identifier(0x1234).service_data.values[0x1234]
        with our_client(port, scenario, raw_did_codec) as client_b:
            result_b = client_b.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result_a == result_b == b"\x01"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_read_unconfigured_did_raises_negative_response_exception(raw_did_codec):
    scenario = Scenario()
    with running_ecu(scenario) as port:
        with oracle_client(port, scenario, raw_did_codec) as oracle:
            with pytest.raises(NegativeResponseException) as oracle_exc:
                oracle.read_data_by_identifier(0x9999)
        with our_client(port, scenario, raw_did_codec) as client:
            with pytest.raises(NegativeResponseException) as our_exc:
                client.read_data_by_identifier(0x9999)
    assert our_exc.value.response.code == oracle_exc.value.response.code == NRC_REQUEST_OUT_OF_RANGE


def test_connection_closed_raises_clear_error_on_further_use(raw_did_codec):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    with running_ecu(scenario) as port:
        client = open_doip_uds_client(
            ECU_HOST,
            ECU_LOGICAL_ADDRESS,
            tcp_port=port,
            client_logical_address=CLIENT_LOGICAL_ADDRESS,
            config=_config(scenario, raw_did_codec),
        )
        client.open()
        client.close()
        with pytest.raises(RuntimeError):
            client.read_data_by_identifier(0x1234)


def test_request_timeout_raises_timeout_exception_via_our_doip_client(raw_did_codec):
    scenario = Scenario(
        dids={0x1234: DIDConfig(value=b"\x01")},
        failure_injections=[FailureInjection(service_id=0x22, selector=0x1234, kind="timeout")],
    )
    with running_ecu(scenario) as port:
        with our_client(port, scenario, raw_did_codec, request_timeout=1.5) as client:
            with pytest.raises(TimeoutException):
                client.read_data_by_identifier(0x1234)

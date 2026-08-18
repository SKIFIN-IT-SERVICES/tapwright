# SPDX-License-Identifier: Apache-2.0

"""T3 tests for DIAG-04 — the transport-agnostic connection abstraction.

Implements #17. Unlike every prior DIAG loop, this one's oracle isn't a
differential comparison against a reference library — it's the
parametrization itself succeeding: **one test body, run twice (CAN and
DoIP), with no per-transport branching in the body**. That literal
unmodified-reuse is `docs/architecture.md` §4's "construction-time choice,
invisible to the calling code" property, demonstrated rather than argued.

`connection_config` (below) does the actual work: depending on which
parametrization instance is running, it starts either a `VirtualECU` on
`vcan` or a `DoIPVirtualECU` over TCP, builds the matching
`CanConnectionConfig`/`DoipConnectionConfig`, and yields a context manager
that opens a client via `open_connection()`. Every test function below
calls it and asserts on the client — never on which transport is
underneath.

The CAN parametrization is marked `requires_vcan` (per-parameter, via
`pytest.param(..., marks=...)`) so it skips cleanly off-Linux; the DoIP
parametrization always runs, same split every DIAG-03 test already uses.

## Scope note

`open_connection()` dispatches on the config object's *type*
(`CanConnectionConfig` vs. `DoipConnectionConfig`), not a string literal —
a caller can't typo a transport name into something that silently falls
through. "SOVD-shaped": a future `SovdConnectionConfig` (DIAG-07) slots
into the same dispatch without touching `open_connection()`'s signature.

**L2 API-cleanliness note** (test-plan skill step 5): this loop is squarely
about `docs/architecture.md` §4's first bullet (transport-agnostic client
interface) — that's the whole point of the oracle here. The second bullet
(request/response interception point) still isn't built; `open_connection()`
doesn't preclude adding it later, same conclusion DIAG-01/02/03 each
reached for their own pieces.

## Correction from the test plan

The plan (posted to #17) said `open_connection()` would be re-exported at
`tapwright.diag` package level. On reflection while implementing, that
breaks the "stay cheap" convention every prior `diag/` submodule
(`uds_client`, `doip_client`, `isotp_transport`) already established —
`connection_config.py` needs both `can`/`isotp` *and* `doipclient`
regardless of which transport a caller picks, so keeping it out of
`tapwright.diag`'s own import graph matters *more* here, not less. Kept as
`tapwright.diag.connection_config.open_connection`, consistent with every
other loop's submodule-access pattern.
"""

from __future__ import annotations

import contextlib

import pytest
from udsoncan.exceptions import NegativeResponseException

from tapwright.diag.connection_config import (
    CanConnectionConfig,
    DoipConnectionConfig,
    open_connection,
)
from tapwright.diag.virtual_ecu import DIDConfig, DoIPVirtualECU, Scenario, VirtualECU
from tapwright.diag.virtual_ecu.protocol import NRC_REQUEST_OUT_OF_RANGE, SESSION_EXTENDED
from tapwright.hal import open_bus

DOIP_ECU_HOST = "127.0.0.1"
DOIP_ECU_LOGICAL_ADDRESS = 0x0001
DOIP_CLIENT_LOGICAL_ADDRESS = 0xE00


@pytest.fixture(
    params=[
        pytest.param("can", marks=pytest.mark.requires_vcan),
        pytest.param("doip"),
    ]
)
def connection_config(request, vcan_channel, raw_did_codec):
    """Yields a callable, `open_client_for(scenario)`, returning a context
    manager over an opened `udsoncan.Client` — built via whichever
    transport this parametrization instance is. Every test below is
    identical regardless of which one runs.
    """
    transport = request.param

    @contextlib.contextmanager
    def open_client_for(scenario: Scenario):
        data_identifiers = {**dict.fromkeys(scenario.dids, raw_did_codec), "default": raw_did_codec}
        client_config = {"data_identifiers": data_identifiers}

        if transport == "can":
            bus = open_bus(backend="socketcan", channel=vcan_channel)
            try:
                transport_config = CanConnectionConfig(
                    bus=bus, rxid=scenario.response_id, txid=scenario.request_id
                )
                with VirtualECU(scenario, channel=vcan_channel):
                    client = open_connection(transport_config, config=client_config)
                    with client:
                        yield client
            finally:
                bus.shutdown()
        else:
            with DoIPVirtualECU(
                scenario, host=DOIP_ECU_HOST, ecu_logical_address=DOIP_ECU_LOGICAL_ADDRESS
            ) as ecu:
                transport_config = DoipConnectionConfig(
                    ecu_ip_address=DOIP_ECU_HOST,
                    ecu_logical_address=DOIP_ECU_LOGICAL_ADDRESS,
                    tcp_port=ecu.port,
                    client_logical_address=DOIP_CLIENT_LOGICAL_ADDRESS,
                )
                client = open_connection(transport_config, config=client_config)
                with client:
                    yield client

    yield open_client_for


# ---------------------------------------------------------------------------
# Happy path — the oracle itself: one body, both transports
# ---------------------------------------------------------------------------


def test_read_did_over_either_transport(connection_config):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with connection_config(scenario) as client:
        result = client.read_data_by_identifier(0xF190).service_data.values[0xF190]
    assert result == b"VIN1234567890123"


def test_write_then_read_did_over_either_transport(connection_config):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00")})
    with connection_config(scenario) as client:
        client.write_data_by_identifier(0x1234, b"\xff\xee")
        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result == b"\xff\xee"


def test_change_session_over_either_transport(connection_config):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01", session_gate=SESSION_EXTENDED)})
    with connection_config(scenario) as client:
        client.change_session(SESSION_EXTENDED)
        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]
    assert result == b"\x01"


# ---------------------------------------------------------------------------
# Error cases — the abstraction must not leak transport-specific exceptions
# ---------------------------------------------------------------------------


def test_read_unconfigured_did_raises_over_either_transport(connection_config):
    scenario = Scenario()
    with connection_config(scenario) as client:
        with pytest.raises(NegativeResponseException) as excinfo:
            client.read_data_by_identifier(0x9999)
    assert excinfo.value.response.code == NRC_REQUEST_OUT_OF_RANGE


def test_connection_closed_raises_over_either_transport(connection_config):
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    with connection_config(scenario) as client:
        pass  # exiting the context manager closes it
    with pytest.raises(RuntimeError):
        client.read_data_by_identifier(0x1234)

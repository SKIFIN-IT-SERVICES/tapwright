# SPDX-License-Identifier: Apache-2.0

"""T3 (subsumed under DIAG-09's declared T4 — mirrors DIAG-02's own
`test_uds_client.py` + `test_uds_client_properties.py` split) test plan for
DIAG-09 — malformed-response hardening for *our own* client stack.

Implements #35. The oracle is the plan's own acceptance line: "Fuzzed
responses from INF-05; no crash, no hang, clear errors." The virtual ECU's
`FailureInjection` (4 kinds: `nrc`, `timeout`, `truncated`, `oversized`)
was built in INF-05 and is already exercised twice over — against the raw
protocol layer (`tests/unit/test_virtual_ecu_protocol.py`) and against a
*stock* `udsoncan` client (`tests/differential/test_virtual_ecu_uds.py`,
whose own `test_injected_truncated_frame_is_actually_sent_on_the_bus`
explicitly hands this exact case off: "DIAG-09 is responsible for testing
that a *client* handles it gracefully; this test only proves the fixture
can misbehave on command"). Neither exercises *our* client wrapper
(`open_uds_client`/`open_doip_uds_client`/`open_connection`) — that gap is
this loop's whole job.

Reuses DIAG-04's own `connection_config` fixture shape (one test body, run
over both CAN and DoIP via parametrization, no per-transport branching) —
the same "construction-time choice, invisible to calling code" property
`test_connection_abstraction.py` already established, applied here to
error paths instead of the happy path.

## Scope notes (posted in full to #35; kept here as a pointer)

- **`oversized` is not an error case.** Per the existing
  `test_injected_oversized_response_exceeds_expected_length` (already in
  `test_virtual_ecu_uds.py`), a flexible/raw DID codec just reads the extra
  bytes as part of the value -- no exception. Asserted here as "completes
  normally, no crash," not "raises."
- **`truncated` is the highest-risk case.** It tests whether ISO-TP's own
  consecutive-frame timeout actually fires when the ECU declares a
  multi-frame length it then never completes -- the literal "no hang"
  requirement, not just "no crash."
- **Genuinely `hypothesis`-fuzzed NRC-byte-range case lives in
  `tests/property/test_client_hardening_properties.py`** -- this file's
  own cases are a deterministic enumeration of the 4 known kinds, not
  itself hypothesis-driven.
- **L2 API-cleanliness note** (test-plan skill step 5): this loop hardens
  callers of `diag/`'s public API surface; it doesn't change that surface
  itself, so no interaction with the still-pending interception point
  beyond what DIAG-05 already established.
"""

from __future__ import annotations

import contextlib
import time

import pytest
from udsoncan.exceptions import NegativeResponseException, TimeoutException

from tapwright.diag.connection_config import (
    CanConnectionConfig,
    DoipConnectionConfig,
    open_connection,
)
from tapwright.diag.virtual_ecu import (
    DIDConfig,
    DoIPVirtualECU,
    FailureInjection,
    Scenario,
    VirtualECU,
)
from tapwright.hal import open_bus

DOIP_ECU_HOST = "127.0.0.1"
DOIP_ECU_LOGICAL_ADDRESS = 0x0001
DOIP_CLIENT_LOGICAL_ADDRESS = 0xE00

TARGET_DID = 0x1234
RDBI_SID = 0x22


@pytest.fixture(
    params=[
        pytest.param("can", marks=pytest.mark.requires_vcan),
        pytest.param("doip"),
    ]
)
def connection_config(request, vcan_channel, raw_did_codec):
    """Yields `open_client_for(scenario)`, a context manager over an opened
    `udsoncan.Client` built via whichever transport this parametrization
    instance is -- identical to `test_connection_abstraction.py`'s own
    fixture, reused rather than re-derived.
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
# Happy path -- the 4 known kinds, one body, both transports
# ---------------------------------------------------------------------------


def test_nrc_response_raises_negative_response_exception_cleanly(connection_config):
    scenario = Scenario(
        dids={TARGET_DID: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(service_id=RDBI_SID, selector=TARGET_DID, kind="nrc", nrc=0x31)
        ],
    )
    with connection_config(scenario) as client:
        with pytest.raises(NegativeResponseException):
            client.read_data_by_identifier(TARGET_DID)


def test_timeout_raises_timeout_exception_cleanly(connection_config):
    scenario = Scenario(
        dids={TARGET_DID: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(service_id=RDBI_SID, selector=TARGET_DID, kind="timeout")
        ],
    )
    with connection_config(scenario) as client:
        with pytest.raises(TimeoutException):
            client.read_data_by_identifier(TARGET_DID)


def test_oversized_response_completes_normally_no_crash(connection_config):
    scenario = Scenario(
        dids={TARGET_DID: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=RDBI_SID, selector=TARGET_DID, kind="oversized", extra_bytes=20
            )
        ],
    )
    with connection_config(scenario) as client:
        response = client.read_data_by_identifier(TARGET_DID)
    assert response.service_data.values[TARGET_DID] == b"\x01" + bytes(20)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_truncated_response_fails_cleanly_and_does_not_hang(connection_config):
    """The literal "no hang" requirement: the ECU declares a multi-frame
    length it never completes. A clean, bounded-time failure -- not an
    indefinite block -- is what this loop exists to prove.
    """
    scenario = Scenario(
        dids={TARGET_DID: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(
                service_id=RDBI_SID, selector=TARGET_DID, kind="truncated", declared_length=42
            )
        ],
    )
    with connection_config(scenario) as client:
        start = time.monotonic()
        with pytest.raises(Exception):  # noqa: B017 -- exact type TBD in tdd-develop
            client.read_data_by_identifier(TARGET_DID)
        elapsed = time.monotonic() - start

    assert elapsed < 10.0  # bounded, not indefinite


def test_boundary_nrc_value_translates_correctly(connection_config):
    """A non-obvious NRC byte (0xFF, outside the commonly-used range this
    codebase's own constants cover) still translates to a clean exception
    rather than an unhandled parse failure -- the deterministic sibling of
    the property file's full-byte-range fuzz.
    """
    scenario = Scenario(
        dids={TARGET_DID: DIDConfig(value=b"\x01")},
        failure_injections=[
            FailureInjection(service_id=RDBI_SID, selector=TARGET_DID, kind="nrc", nrc=0xFF)
        ],
    )
    with connection_config(scenario) as client:
        with pytest.raises(NegativeResponseException) as exc_info:
            client.read_data_by_identifier(TARGET_DID)
    assert exc_info.value.response.code == 0xFF


# ---------------------------------------------------------------------------
# Error case
# ---------------------------------------------------------------------------


def test_session_recovers_after_a_failure_injected_request(connection_config):
    """A malformed response to one request must not corrupt the session for
    the next one -- "no crash" means the client, not just the one call,
    survives.
    """
    other_did = 0x5678
    scenario = Scenario(
        dids={TARGET_DID: DIDConfig(value=b"\x01"), other_did: DIDConfig(value=b"\x02")},
        failure_injections=[
            FailureInjection(service_id=RDBI_SID, selector=TARGET_DID, kind="nrc", nrc=0x31)
        ],
    )
    with connection_config(scenario) as client:
        with pytest.raises(NegativeResponseException):
            client.read_data_by_identifier(TARGET_DID)

        # The same client, same session, completes a normal request next.
        response = client.read_data_by_identifier(other_did)
    assert response.service_data.values[other_did] == b"\x02"

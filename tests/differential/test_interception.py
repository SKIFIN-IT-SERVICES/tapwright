# SPDX-License-Identifier: Apache-2.0

"""T2 tests for DIAG-05 — request/response interception hooks, working
across a process boundary.

Implements #25. The oracle (plan §2.1, DIAG-05's own backlog line, verbatim):
"A third-party wrapper can observe and modify a request/response without
forking, from a separate process." Every case below spawns a genuine OS
subprocess (`_interception_observer.py`, imports nothing from `tapwright`)
as the "third party" — not an in-process mock, not a thread. That subprocess
speaks only the plain newline-delimited-JSON protocol
`InterceptingConnection` publishes over a TCP socket.

Most cases are CAN/`vcan`-based (marked individually, not at module scope,
since the DoIP case at the bottom needs no `vcan` at all — matching
DIAG-03's own no-module-mark precedent).

## Scope notes

- Single observer at a time — multi-observer fan-out is a fast-follow, not
  required by this loop's oracle.
- **L2 API-cleanliness note** (test-plan skill step 5): this loop *is*
  `docs/architecture.md` §4's second bullet, the one every prior DIAG loop
  noted as "not built yet, but not precluded." It's transport-agnostic by
  construction (wraps whatever `BaseConnection` DIAG-04's `open_connection()`
  produces), so it doesn't reopen or special-case CAN vs. DoIP.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from doipclient import DoIPClient
from doipclient.connectors import DoIPClientUDSConnector
from udsoncan.client import Client
from udsoncan.configs import default_client_config

from tapwright.diag.connection import TapwrightIsoTpConnection
from tapwright.diag.interception import InterceptingConnection
from tapwright.diag.isotp_transport import IsoTpTransport
from tapwright.diag.virtual_ecu import DIDConfig, DoIPVirtualECU, Scenario, VirtualECU
from tapwright.hal import open_bus

OBSERVER_SCRIPT = Path(__file__).resolve().parent / "_interception_observer.py"
DOIP_ECU_HOST = "127.0.0.1"
DOIP_ECU_LOGICAL_ADDRESS = 0x0001
DOIP_CLIENT_LOGICAL_ADDRESS = 0xE00

# Time to let a spawned observer's TCP connect land in the listening
# backlog before the intercepted call that should pick it up. The connect
# itself is near-instant on localhost; this covers subprocess startup.
OBSERVER_SETTLE_TIME = 0.3


def spawn_observer(port: int | None, *args: str) -> subprocess.Popen:
    """A real OS subprocess — the "separate process" the oracle requires.

    `port` is `int | None` because it mirrors `InterceptingConnection.bound_port`,
    which is only ever `None` before `open()` — by the time a test calls this,
    the connection is already open, but the assert documents that invariant
    rather than silently accepting `None`.
    """
    assert port is not None, "InterceptingConnection.open() must run before spawning an observer"
    return subprocess.Popen(
        [sys.executable, str(OBSERVER_SCRIPT), str(port), *args],
        stdout=subprocess.PIPE,
        text=True,
    )


def read_observer_messages(proc: subprocess.Popen, count: int) -> list[dict]:
    assert proc.stdout is not None
    messages = []
    for _ in range(count):
        line = proc.stdout.readline()
        if not line:
            break
        messages.append(json.loads(line))
    return messages


def client_config(scenario: Scenario, raw_did_codec) -> dict:
    data_identifiers = {**dict.fromkeys(scenario.dids, raw_did_codec), "default": raw_did_codec}
    config = dict(default_client_config)
    config["data_identifiers"] = data_identifiers
    return config


@contextlib.contextmanager
def intercepted_can_client(scenario: Scenario, vcan_channel: str, raw_did_codec):
    bus = open_bus(backend="socketcan", channel=vcan_channel)
    try:
        with VirtualECU(scenario, channel=vcan_channel):
            transport = IsoTpTransport(bus, rxid=scenario.response_id, txid=scenario.request_id)
            intercepting = InterceptingConnection(TapwrightIsoTpConnection(transport))
            with Client(intercepting, config=client_config(scenario, raw_did_codec)) as client:
                yield client, intercepting
    finally:
        bus.shutdown()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.requires_vcan
def test_observer_process_observes_request_and_response_without_modifying(
    vcan_channel, raw_did_codec
):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, intercepting):
        observer = spawn_observer(intercepting.bound_port, "--messages", "2")
        time.sleep(OBSERVER_SETTLE_TIME)
        response = client.read_data_by_identifier(0xF190)
        observer.wait(timeout=5.0)

    assert response.service_data.values[0xF190] == b"VIN1234567890123"
    messages = read_observer_messages(observer, 2)
    assert [m["type"] for m in messages] == ["request", "response"]


@pytest.mark.requires_vcan
def test_observer_process_can_replace_a_response(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    replacement = bytes([0x62, 0xF1, 0x90]) + b"REPLACEDVALUE"

    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, intercepting):
        observer = spawn_observer(
            intercepting.bound_port, "--messages", "2", "--replace", f"response:{replacement.hex()}"
        )
        time.sleep(OBSERVER_SETTLE_TIME)
        response = client.read_data_by_identifier(0xF190)
        observer.wait(timeout=5.0)

    assert response.service_data.values[0xF190] == b"REPLACEDVALUE"


@pytest.mark.requires_vcan
def test_observer_process_can_replace_a_request(vcan_channel, raw_did_codec):
    """The observer rewrites an outbound WriteDataByIdentifier request's
    *value* before it reaches the ECU. Reading the DID back afterward
    (with no observer attached — pure passthrough by then) shows the ECU
    stored what the observer substituted, not what the caller originally
    asked to write — proof the ECU actually received the mutated request.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x00\x00")})
    mutated_value = b"\xbb\xbb"
    replacement_request = bytes([0x2E, 0x12, 0x34]) + mutated_value

    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, intercepting):
        observer = spawn_observer(
            intercepting.bound_port,
            "--messages",
            "2",
            "--replace",
            f"request:{replacement_request.hex()}",
        )
        time.sleep(OBSERVER_SETTLE_TIME)
        client.write_data_by_identifier(0x1234, b"\xaa\xaa")
        observer.wait(timeout=5.0)

        result = client.read_data_by_identifier(0x1234).service_data.values[0x1234]

    assert result == mutated_value


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.requires_vcan
def test_no_observer_attached_is_pure_passthrough(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, _intercepting):
        start = time.monotonic()
        response = client.read_data_by_identifier(0xF190)
        elapsed = time.monotonic() - start

    assert response.service_data.values[0xF190] == b"VIN1234567890123"
    # No observer ever connects in this test: publishing is one non-blocking
    # accept() per message. A generous bound (normal vcan round-trips are
    # single-digit milliseconds) that would still catch an accidental
    # blocking-accept regression.
    assert elapsed < 1.0


@pytest.mark.requires_vcan
def test_observer_disconnecting_mid_session_falls_back_to_passthrough(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, intercepting):
        # Observes exactly the request, then exits -- closed before the
        # response is published.
        observer = spawn_observer(intercepting.bound_port, "--messages", "1")
        time.sleep(OBSERVER_SETTLE_TIME)
        response = client.read_data_by_identifier(0xF190)
        observer.wait(timeout=5.0)

    assert response.service_data.values[0xF190] == b"VIN1234567890123"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.requires_vcan
def test_unresponsive_observer_does_not_block_traffic_forever(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, intercepting):
        observer = spawn_observer(intercepting.bound_port, "--messages", "1", "--silent")
        time.sleep(OBSERVER_SETTLE_TIME)
        start = time.monotonic()
        response = client.read_data_by_identifier(0xF190)
        elapsed = time.monotonic() - start
        observer.terminate()
        observer.wait(timeout=5.0)

    assert response.service_data.values[0xF190] == b"VIN1234567890123"
    assert elapsed < 10.0  # bounded (REPLY_TIMEOUT-scale), not indefinite


@pytest.mark.requires_vcan
def test_malformed_observer_reply_is_ignored_not_crashing(vcan_channel, raw_did_codec):
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with intercepted_can_client(scenario, vcan_channel, raw_did_codec) as (client, intercepting):
        observer = spawn_observer(intercepting.bound_port, "--messages", "1", "--garbage")
        time.sleep(OBSERVER_SETTLE_TIME)
        response = client.read_data_by_identifier(0xF190)
        observer.wait(timeout=5.0)

    assert response.service_data.values[0xF190] == b"VIN1234567890123"


# ---------------------------------------------------------------------------
# Transport-agnosticism — no requires_vcan: DoIP is plain TCP
# ---------------------------------------------------------------------------


def test_interception_wraps_a_doip_connection_identically(raw_did_codec):
    """InterceptingConnection wraps whatever BaseConnection DIAG-04's
    open_connection() produces — confirmed once here against a DoIP-backed
    connection, not re-running the full observe/replace matrix a second
    time (DIAG-04 already established transport-agnosticism as a property
    of the underlying connection types; this only confirms interception
    doesn't special-case CAN).
    """
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})
    with DoIPVirtualECU(
        scenario, host=DOIP_ECU_HOST, ecu_logical_address=DOIP_ECU_LOGICAL_ADDRESS
    ) as ecu:
        doip_layer = DoIPClient(
            DOIP_ECU_HOST,
            DOIP_ECU_LOGICAL_ADDRESS,
            tcp_port=ecu.port,
            client_logical_address=DOIP_CLIENT_LOGICAL_ADDRESS,
        )
        intercepting = InterceptingConnection(
            DoIPClientUDSConnector(doip_layer, close_connection=True)
        )
        with Client(intercepting, config=client_config(scenario, raw_did_codec)) as client:
            observer = spawn_observer(intercepting.bound_port, "--messages", "2")
            time.sleep(OBSERVER_SETTLE_TIME)
            response = client.read_data_by_identifier(0xF190)
            observer.wait(timeout=5.0)

    assert response.service_data.values[0xF190] == b"VIN1234567890123"
    messages = read_observer_messages(observer, 2)
    assert [m["type"] for m in messages] == ["request", "response"]

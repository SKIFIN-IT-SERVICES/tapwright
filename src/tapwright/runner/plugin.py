# SPDX-License-Identifier: Apache-2.0

"""The `pytest11` plugin: `ecu`, `bus`, `uds` fixtures (RUN-01,
`TOOL-REQ-028`).

Registered via `pyproject.toml`'s `[project.entry-points.pytest11]` — pytest
auto-discovers this on `pip install tapwright`, so a user's own test file
needs no `pytest_plugins = [...]` to get these fixtures. That auto-discovery
*is* the "zero custom test-runner boilerplate" `TOOL-REQ-028` names.

    def test_read_vin(uds):
        response = uds.read_data_by_identifier(0xF190)
        assert response.service_data.values[0xF190] == b"..."

`scenario` is the one fixture a user is expected to override — standard
pytest fixture-override, not a plugin-specific mechanism — to configure
what the virtual ECU actually responds with. Left unoverridden, it's an
empty `Scenario()`, so `uds`/`ecu` still construct cleanly with zero
configuration; reads just get UDS's own "unconfigured DID" negative
response rather than a construction failure.

CAN/`vcan` only in this loop — DoIP fixtures are a fast-follow (DIAG-04
already proved the transport swap is a construction-time choice, not a
design question this plugin needs to re-answer).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
import udsoncan
from udsoncan.client import Client

from tapwright.diag.connection_config import CanConnectionConfig, open_connection
from tapwright.diag.virtual_ecu import Scenario, VirtualECU
from tapwright.hal import Bus, open_bus

DEFAULT_CHANNEL = "vcan0"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("tapwright")
    group.addoption(
        "--tapwright-channel",
        action="store",
        default=None,
        help=(
            "CAN channel the ecu/bus/uds fixtures use "
            f"(default: {DEFAULT_CHANNEL}, or the TAPWRIGHT_CHANNEL env var)"
        ),
    )


def _resolve_channel(request: pytest.FixtureRequest) -> str:
    cli_value = request.config.getoption("--tapwright-channel")
    if cli_value:
        return str(cli_value)
    return os.environ.get("TAPWRIGHT_CHANNEL", DEFAULT_CHANNEL)


class _RawCodec(udsoncan.DidCodec):
    """Default DID codec: every configured DID's payload is treated as
    opaque bytes. A first-time user hasn't written a UDS codec yet either —
    this is what lets `uds` work with zero configuration. Override with a
    typed `udsoncan.DidCodec` via `open_connection(..., config={...})`
    directly once you know a real DID's actual encoding.
    """

    def encode(self, *did_value: Any) -> bytes:
        (value,) = did_value
        return bytes(value)

    def decode(self, did_payload: bytes) -> bytes:
        return bytes(did_payload)

    def __len__(self) -> int:
        raise udsoncan.DidCodec.ReadAllRemainingData


@pytest.fixture
def scenario() -> Scenario:
    """Override this in your own test file/conftest to configure the
    virtual ECU's DIDs, DTCs, security levels, or arbitration IDs — plain
    pytest fixture-override, nothing plugin-specific. Empty by default.
    """
    return Scenario()


@pytest.fixture
def bus(request: pytest.FixtureRequest) -> Iterator[Bus]:
    channel = _resolve_channel(request)
    hal_bus = open_bus(backend="socketcan", channel=channel)
    try:
        yield hal_bus
    finally:
        hal_bus.shutdown()


@pytest.fixture
def ecu(scenario: Scenario, request: pytest.FixtureRequest) -> Iterator[VirtualECU]:
    channel = _resolve_channel(request)
    with VirtualECU(scenario, channel=channel) as running_ecu:
        yield running_ecu


@pytest.fixture
def uds(bus: Bus, ecu: VirtualECU) -> Iterator[Client]:
    transport_config = CanConnectionConfig(
        bus=bus, rxid=ecu.scenario.response_id, txid=ecu.scenario.request_id
    )
    data_identifiers: dict[int | str, type[udsoncan.DidCodec]] = {
        **dict.fromkeys(ecu.scenario.dids, _RawCodec),
        "default": _RawCodec,
    }
    client = open_connection(transport_config, config={"data_identifiers": data_identifiers})
    with client:
        yield client

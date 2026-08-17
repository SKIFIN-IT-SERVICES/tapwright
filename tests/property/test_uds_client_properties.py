# SPDX-License-Identifier: Apache-2.0

"""T4 property test for DIAG-02 — DIAG-02's declared tier (`LOOPS.md`) is T4,
which subsumes the T3 differential file
(`tests/differential/test_uds_client.py`), not replaces it.

One property, chosen to stress exactly the plumbing DIAG-02 adds: a DID
value written through `open_uds_client()`'s client, of varying length
(crossing the ISO-TP single/multi-frame boundary many times over a run),
reads back byte-identical. `hypothesis` generates the lengths and content;
a fixed seed corpus isn't enough to have caught the `is_extended_id` bug
DIAG-01 (#11) shipped with, and this tier exists precisely to widen the net
beyond what a human enumerates by hand.

The ECU/client pair is set up once via a fixture, not per hypothesis
example — constructing a fresh vcan-bound client per example (dozens to
hundreds of times) would make this tier prohibitively slow for no
additional coverage, since round-trip correctness doesn't depend on setup
order.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from udsoncan.client import Client

from tapwright.diag.uds_client import open_uds_client
from tapwright.diag.virtual_ecu import DIDConfig, Scenario, VirtualECU
from tapwright.hal import open_bus

pytestmark = pytest.mark.requires_vcan

TEST_DID = 0x1234


@pytest.fixture(scope="module")
def client(vcan_channel, raw_did_codec) -> Iterator[Client]:
    scenario = Scenario(dids={TEST_DID: DIDConfig(value=b"\x00")})
    bus = open_bus(backend="socketcan", channel=vcan_channel)
    with VirtualECU(scenario, channel=vcan_channel):
        uds_client = open_uds_client(
            bus,
            rxid=scenario.response_id,
            txid=scenario.request_id,
            config={"data_identifiers": {TEST_DID: raw_did_codec}},
        )
        try:
            with uds_client:
                yield uds_client
        finally:
            bus.shutdown()


@settings(deadline=None)
@given(value=st.binary(min_size=1, max_size=60))
def test_write_then_read_did_round_trips_for_arbitrary_values(client: Client, value: bytes) -> None:
    """Any byte value, of any length within a generous bound, written then
    read back through our client, round-trips exactly — across the
    single-frame/multi-frame boundary many times over a hypothesis run.
    """
    client.write_data_by_identifier(TEST_DID, value)
    result = client.read_data_by_identifier(TEST_DID).service_data.values[TEST_DID]
    assert result == value

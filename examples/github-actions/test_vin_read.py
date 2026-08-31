# SPDX-License-Identifier: Apache-2.0

"""RUN-06 example (`TOOL-REQ-033`): the entire test a consumer writes.

No `hal.Bus`, no `VirtualECU`, no connection wiring anywhere in this
file — `ecu`/`uds` come from `tapwright`'s own pytest plugin
(`tapwright.runner.plugin`, RUN-01), auto-discovered the moment
`tapwright` is installed. `scenario` overrides the plugin's own empty
default via a plain pytest fixture override, not a plugin-specific
mechanism.

Run it yourself:

    python -m venv .venv && . .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
    pip install -r requirements.txt
    sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0
    pytest

Or in CI: see `.github/workflows/test.yml` (in this same example
directory) — no local vcan setup needed there, the workflow does it via
`tapwright`'s own reusable `bring-up-vcan` composite action.
"""

from __future__ import annotations

import pytest

from tapwright.diag.virtual_ecu import DIDConfig, Scenario


@pytest.fixture
def scenario() -> Scenario:
    return Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})


def test_read_vin_from_the_virtual_ecu(uds):
    response = uds.read_data_by_identifier(0xF190)
    assert response.service_data.values[0xF190] == b"VIN1234567890123"

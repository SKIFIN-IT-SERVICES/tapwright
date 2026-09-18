# SPDX-License-Identifier: Apache-2.0

"""RUN-07 example (`TOOL-REQ-034`): the entire test a consumer writes.

Identical content to `examples/github-actions/test_vin_read.py` (RUN-06) —
the point of this example is the CI orchestration YAML, not a second test
to maintain. No `hal.Bus`, no `VirtualECU`, no connection wiring anywhere
in this file — `ecu`/`uds` come from `tapwright`'s own pytest plugin
(`tapwright.runner.plugin`, RUN-01), auto-discovered the moment
`tapwright` is installed. `scenario` overrides the plugin's own empty
default via a plain pytest fixture override, not a plugin-specific
mechanism.

Run it yourself:

    python -m venv .venv && . .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
    pip install -r requirements.txt
    sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0
    pytest

Or in CI: see `.gitlab-ci.yml` (in this same example directory) — **not
run-and-observed-green on real GitLab CI**; see this directory's own
README for why.
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

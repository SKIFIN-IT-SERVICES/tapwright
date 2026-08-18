# SPDX-License-Identifier: Apache-2.0

"""Test plan for RUN-01 / TOOL-REQ-028 — the pytest-native plugin's `ecu`,
`bus`, `uds` fixtures.

Implements #20. The oracle (plan §2.1) is literal: "a user test using only
fixtures passes with no boilerplate." This file *is* that user — it imports
nothing from `tapwright.hal` or `tapwright.diag.uds_client`/`connection_config`
in any test body, only `Scenario`/`DIDConfig` to describe the ECU's data
(configuration, not test-runner setup).

The auto-discovery half of the oracle is proven implicitly: these fixtures
are used below with no `pytest_plugins = [...]` anywhere in this repo's
`tests/` tree. If the `pytest11` entry point in `pyproject.toml` isn't wired
correctly, every test in this file fails to collect at all (unknown fixture
`uds`/`bus`/`ecu`) rather than failing an assertion — collection succeeding
*is* part of what each case proves.

## Scope notes (posted in full to #20; kept here as a pointer)

- CAN/`vcan` only (`ecu` = `VirtualECU`) — a DoIP fixture set is a
  fast-follow, not required to meet this loop's own oracle (DIAG-04 already
  proved the transport swap is a construction-time choice).
- `TOOL-REQ-029` (deterministic `wait_for_*` helpers) is a separate
  requirement, not part of `TOOL-REQ-028`'s three named fixtures — flagged
  as a fast-follow, not silently folded in.
- **L2 API-cleanliness note** (test-plan skill step 5): `uds` is built via
  DIAG-04's `open_connection()`, so it inherits that loop's transport-
  agnostic and (future) interception-point properties automatically —
  nothing about wrapping it in a fixture changes `diag/`'s public contract.
"""

from __future__ import annotations

import pytest

from tapwright.diag.virtual_ecu import DIDConfig, Scenario

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #20)")


@pytest.fixture
def scenario() -> Scenario:
    """Overrides the plugin's own default (empty) `scenario` fixture —
    standard pytest fixture-override, no plugin-specific mechanism needed.
    This is the *only* tapwright-aware code most of this file's tests
    contain; everything else is plain pytest + plain UDS calls.
    """
    return Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})


# ---------------------------------------------------------------------------
# Happy path — the oracle itself
# ---------------------------------------------------------------------------


@SKIP
def test_uds_fixture_reads_configured_did(uds):
    """def test_x(uds): ... — TOOL-REQ-028's acceptance criterion, verbatim.
    No Bus, no VirtualECU, no connection wiring anywhere in this function.
    """


@SKIP
def test_ecu_fixture_is_usable_directly(ecu):
    """A user who wants lower-level access than `uds` gives (e.g. to expect
    a specific failure injection) can still reach the running ECU object
    directly."""


@SKIP
def test_bus_fixture_is_usable_directly(bus):
    """A user who wants raw frame access below UDS can still reach a
    working, already-open Bus directly."""


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_uds_fixture_constructs_with_default_scenario(vcan_channel):
    """A test file that does *not* override `scenario` still gets a working
    `uds` fixture (against the plugin's own empty-Scenario default) rather
    than a construction failure — "zero boilerplate" includes "zero
    configuration" as a valid starting point, not just a supported one.

    Deliberately does not depend on the `uds` fixture directly as a
    parameter, since this file's own `scenario` override (above) would
    shadow the plugin's default and defeat the point — exercised via a
    dedicated non-overriding scenario in the real test body instead.
    """


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_uds_read_unconfigured_did_raises_clear_error(uds):
    """Reading a DID the scenario never configured raises udsoncan's
    NegativeResponseException — a clear, typed error, not a hang or a bare
    exception from deep inside the stack. Matches every DIAG loop's own
    established contract for this case.
    """


@SKIP
def test_bus_channel_is_configurable_not_hardcoded():
    """The channel `bus`/`ecu` use is a config option (CLI/ini), not a
    hardcoded "vcan0" literal — matching HAL-01's own "swap is a config
    change" property, carried up to the fixture layer.
    """

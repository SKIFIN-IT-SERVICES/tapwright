# SPDX-License-Identifier: Apache-2.0

"""T2: the virtual ECU's own process/fixture lifecycle (INF-05, #9).

These cases are about the responder as a piece of test infrastructure — does
it start, bind to the interface it's told to, and stop cleanly — rather than
about UDS correctness (that's `tests/differential/test_virtual_ecu_uds.py`,
this loop's T3 tier and primary oracle).

This matters on its own: the plan calls the virtual ECU "load-bearing three
times over" (onboarding demo, CI fixture, every downstream loop's oracle). A
responder that leaks a background thread, leaves a bound socket behind, or
hangs on shutdown will produce mysterious failures in every test file after
it, not just its own — so its lifecycle gets the same test-first treatment as
its protocol behaviour.
"""

from __future__ import annotations

import can
import pytest

from tapwright.diag.virtual_ecu import DIDConfig, Scenario, VirtualECU

pytestmark = pytest.mark.requires_vcan


def test_starts_and_binds_to_configured_vcan_interface(vcan_channel, uds_client_factory):
    """Constructing and starting the responder against `vcan_channel` binds
    a socket on that interface and answers a request sent on it — the
    simplest observable proof the bind actually happened, rather than
    reaching into the responder's private socket state. Uses the same
    `udsoncan`-based helper the differential oracle uses, so the request is
    correctly ISO-TP-framed rather than hand-rolled raw bytes.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})
    with VirtualECU(scenario, channel=vcan_channel):
        with uds_client_factory(scenario, vcan_channel) as client:
            response = client.read_data_by_identifier(0x1234)
    assert response.service_data.values[0x1234] == b"\x01"


def test_stops_cleanly_and_releases_the_socket(vcan_channel):
    """Stopping the responder closes its socket and joins its background
    thread within a bounded time — no orphaned resources between tests,
    which is what NFR-003 (test determinism) depends on across an entire
    suite, not just within one test.
    """
    ecu = VirtualECU(Scenario(), channel=vcan_channel)
    ecu.start()
    ecu.stop()

    assert ecu._transport._serve_thread is None
    assert ecu._transport._bus is None

    # And starting again on the same channel must not fail because a
    # previous run left the interface busy.
    ecu.start()
    ecu.stop()


def test_usable_as_a_context_manager(vcan_channel):
    """`with VirtualECU(...) as ecu:` starts on enter and stops on exit,
    including when the body raises — a fixture that leaks state on a failing
    test is worse than one that leaks state on a passing one, because it's
    the failure case tests exist to catch.
    """
    scenario = Scenario(dids={0x1234: DIDConfig(value=b"\x01")})

    with VirtualECU(scenario, channel=vcan_channel) as ecu:
        assert ecu._transport._serve_thread is not None

    assert ecu._transport._serve_thread is None

    with pytest.raises(RuntimeError):
        with VirtualECU(scenario, channel=vcan_channel) as ecu:
            raise RuntimeError("boom")

    assert ecu._transport._serve_thread is None


def test_two_independent_scenarios_do_not_interfere_on_different_channels(
    vcan_channel, uds_client_factory
):
    """Two responder instances, configured with different scenarios on two
    different vcan interfaces, do not cross-talk — needed so a future
    multi-ECU integration test (DIAG-04-adjacent) isn't blocked by a
    single-instance assumption baked in here.

    CI only guarantees `vcan0`; a second interface is opt-in locally.
    """
    second_channel = "vcan1"
    try:
        probe = can.Bus(interface="socketcan", channel=second_channel)
        probe.shutdown()
    except Exception:
        pytest.skip(f"{second_channel} not available — bring it up to run this case locally")

    scenario_a = Scenario(dids={0x1111: DIDConfig(value=b"\xaa")})
    scenario_b = Scenario(dids={0x1111: DIDConfig(value=b"\xbb")})

    with (
        VirtualECU(scenario_a, channel=vcan_channel),
        VirtualECU(scenario_b, channel=second_channel),
    ):
        with uds_client_factory(scenario_a, vcan_channel) as client_a:
            response_a = client_a.read_data_by_identifier(0x1111)
        with uds_client_factory(scenario_b, second_channel) as client_b:
            response_b = client_b.read_data_by_identifier(0x1111)

    assert response_a.service_data.values[0x1111] == b"\xaa"
    assert response_b.service_data.values[0x1111] == b"\xbb"


def test_unstartable_configuration_fails_fast_with_a_clear_error():
    """An invalid configuration (here: a nonexistent interface) raises
    immediately with an actionable message, rather than hanging or failing
    silently — this is the fixture a new contributor's first `pip install`
    and first test run depends on (TOOL-REQ-026's "zero hardware" onboarding
    claim), so its failure mode matters as much as its success path.
    """
    ecu = VirtualECU(Scenario(), channel="vcan_does_not_exist")
    with pytest.raises(RuntimeError, match="vcan_does_not_exist"):
        ecu.start()

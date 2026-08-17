# SPDX-License-Identifier: Apache-2.0

"""Test plan for INF-05 — the virtual ECU's own process/fixture lifecycle.

Implements #9. T2 tier: these cases are about the responder as a piece of test
infrastructure — does it start, bind to the interface it's told to, and stop
cleanly — rather than about UDS correctness (that's
`tests/differential/test_virtual_ecu_uds.py`, this loop's T3 tier and primary
oracle).

This matters on its own: the plan calls the virtual ECU "load-bearing three
times over" (onboarding demo, CI fixture, every downstream loop's oracle). A
responder that leaks a background thread, leaves a bound socket behind, or
hangs on shutdown will produce mysterious failures in every test file after
it, not just its own — so its lifecycle gets the same test-first treatment as
its protocol behaviour.

Stubbed per PROCESS.md step 2; see test_virtual_ecu_uds.py's module docstring
for the scope notes (service set, failure-injection-in-scope, file location)
that apply to INF-05 as a whole.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #9)")


@SKIP
def test_starts_and_binds_to_configured_vcan_interface(vcan_channel):
    """Constructing and starting the responder against `vcan_channel` binds
    a socket on that interface and no other.
    """


@SKIP
def test_stops_cleanly_and_releases_the_socket(vcan_channel):
    """Stopping the responder closes its socket and joins any background
    thread/process within a bounded time — no orphaned resources between
    tests, which is what NFR-003 (test determinism) depends on across an
    entire suite, not just within one test.
    """


@SKIP
def test_usable_as_a_context_manager(vcan_channel):
    """`with VirtualECU(...) as ecu:` starts on enter and stops on exit,
    including when the body raises — a fixture that leaks state on a failing
    test is worse than one that leaks state on a passing one, because it's
    the failure case tests exist to catch.
    """


@SKIP
def test_two_independent_scenarios_do_not_interfere_on_different_channels(vcan_channel):
    """Two responder instances, configured with different scenarios on two
    different vcan interfaces, do not cross-talk — needed so a future
    multi-ECU integration test (DIAG-04-adjacent) isn't blocked by a
    single-instance assumption baked in here.
    """


@SKIP
def test_unstartable_configuration_fails_fast_with_a_clear_error(vcan_channel):
    """An invalid scenario (e.g. a nonexistent interface, or a malformed
    scenario file) raises immediately with an actionable message, rather than
    hanging or failing silently — this is the fixture a new contributor's
    first `pip install` and first test run depends on (TOOL-REQ-026's
    "zero hardware" onboarding claim), so its failure mode matters as much as
    its success path.
    """

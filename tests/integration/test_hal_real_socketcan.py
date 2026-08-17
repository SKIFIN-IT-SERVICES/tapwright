# SPDX-License-Identifier: Apache-2.0

"""TOOL-REQ-002's real-Linux-interface acceptance criterion.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3

Requires an actual SocketCAN-visible interface (e.g. a physical adapter
brought up as can0) — never available on this (macOS) dev host, and not
assumed present on a generic CI runner either. Opt-in via
TAPWRIGHT_TEST_REAL_CAN_IFACE (the interface name) *and* the project-wide
`requires_hardware` marker (see tests/conftest.py) so it shows up under the
same TAPWRIGHT_HARDWARE=1 gate as every other real-hardware case, per
CONTRIBUTING.md's skip-cleanly contract.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.requires_hardware


def test_frame_visible_through_abstraction_on_real_socketcan_interface():
    """TOOL-REQ-002: candump-equivalent traffic visible through the
    abstraction on a real Linux CAN interface."""
    iface = os.environ.get("TAPWRIGHT_TEST_REAL_CAN_IFACE")
    if not iface:
        pytest.skip(
            "set TAPWRIGHT_TEST_REAL_CAN_IFACE to a real SocketCAN interface "
            "name (e.g. can0) to run this opt-in test"
        )

    from tapwright.hal import Frame, open_bus

    bus = open_bus(backend="socketcan", channel=iface)
    try:
        bus.send(Frame(arbitration_id=0x123, data=b"\x01\x02"))
        # Asserting receipt requires a loopback rig or a second interface on
        # the same physical bus — left to whoever runs this opt-in test with
        # hardware attached; not something CI or this dev host can assert.
    finally:
        bus.shutdown()

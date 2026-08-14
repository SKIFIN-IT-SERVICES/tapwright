# SPDX-License-Identifier: Apache-2.0

"""Shared test configuration across all verification tiers."""

from __future__ import annotations

import os
import platform
import subprocess

import pytest
from hypothesis import HealthCheck, settings

# T4 profiles. CI runs more examples than a local edit-run cycle should wait
# for; `dev` stays fast enough that nobody is tempted to skip the tier locally.
settings.register_profile("dev", max_examples=25, deadline=None)
settings.register_profile(
    "ci",
    max_examples=250,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


def _vcan_channel() -> str:
    return os.environ.get("TAPWRIGHT_TEST_CHANNEL", "vcan0")


def _vcan_available() -> bool:
    """Is a usable vcan interface up?

    vcan is a Linux kernel feature, so this is False on macOS and Windows by
    construction. That is a fact about the developer's laptop, not a gap in the
    project: CI runs the full suite on Linux, and C-8 is about needing no
    *hardware*, not about needing no kernel.
    """
    if platform.system() != "Linux":
        return False
    try:
        result = subprocess.run(
            ["ip", "link", "show", _vcan_channel()],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


@pytest.fixture(scope="session")
def vcan_channel() -> str:
    """The vcan interface tests should use."""
    return _vcan_channel()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip vcan and hardware tests when their substrate is absent.

    Done centrally rather than with a `skipif` in each module so that test files
    need no import from conftest — and so the skip *reason* tells a contributor
    on a fresh machine exactly which three commands fix it.
    """
    if not _vcan_available():
        skip_vcan = pytest.mark.skip(
            reason=(
                f"no vcan interface ({_vcan_channel()}). On Linux:\n"
                "  sudo modprobe vcan\n"
                "  sudo ip link add dev vcan0 type vcan\n"
                "  sudo ip link set up vcan0"
            )
        )
        for item in items:
            if "requires_vcan" in item.keywords:
                item.add_marker(skip_vcan)

    # Physical hardware never runs in CI: HAL-03/04/05/06 close at T3-on-vcan,
    # and a named human runs the same suite against real devices out of band,
    # recording the result in LOOPS.md. Opt in locally with TAPWRIGHT_HARDWARE=1.
    if not os.environ.get("TAPWRIGHT_HARDWARE"):
        skip_hw = pytest.mark.skip(
            reason="needs physical CAN hardware; set TAPWRIGHT_HARDWARE=1 to run"
        )
        for item in items:
            if "requires_hardware" in item.keywords:
                item.add_marker(skip_hw)

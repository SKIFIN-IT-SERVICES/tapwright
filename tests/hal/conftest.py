"""Shared fixtures for the hal/ (L0) test plan — issue #3.

https://github.com/SKIFIN-IT-SERVICES/tapwright/issues/3
"""

import platform
import socket

import pytest


def _vcan0_available() -> bool:
    """True only if this host can actually bind a raw CAN socket to vcan0.

    Per CONTRIBUTING.md#running-tests, vcan-dependent tests must skip
    cleanly (not fail) on macOS/Windows or any Linux host without vcan0
    brought up — this is the single check every such test routes through.
    """
    if platform.system() != "Linux":
        return False
    try:
        sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    except (AttributeError, OSError):
        return False
    try:
        sock.bind(("vcan0",))
    except OSError:
        return False
    finally:
        sock.close()
    return True


@pytest.fixture
def vcan_channel():
    """Yields the vcan0 channel name, or skips cleanly if unavailable."""
    if not _vcan0_available():
        pytest.skip("vcan0 not available on this platform/host — see CONTRIBUTING.md#running-tests")
    return "vcan0"

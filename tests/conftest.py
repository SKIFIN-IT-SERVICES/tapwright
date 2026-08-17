# SPDX-License-Identifier: Apache-2.0

"""Shared test configuration across all verification tiers."""

from __future__ import annotations

import contextlib
import os
import platform
import subprocess
from typing import TYPE_CHECKING, Any

import can
import isotp
import pytest
import udsoncan
import udsoncan.configs
from hypothesis import HealthCheck, settings
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection

if TYPE_CHECKING:
    from collections.abc import Generator

    from tapwright.diag.virtual_ecu import Scenario

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


class _RawCodec(udsoncan.DidCodec):
    """A DID codec that treats the payload as opaque bytes, of whatever
    length the server sent. udsoncan requires a codec per DID before it will
    decode a ReadDataByIdentifier response at all (see
    `docs/inf-05-simulator-reuse-evaluation.md`'s oracle discussion); the
    virtual ECU's own DID values are already plain bytes (`Scenario`'s
    `DIDConfig.value`), so no further interpretation belongs here — that
    would just be re-encoding the scenario's own configuration a second time.
    """

    def encode(self, *did_value: Any) -> bytes:
        (value,) = did_value
        return bytes(value)

    def decode(self, did_payload: bytes) -> bytes:
        return bytes(did_payload)

    def __len__(self) -> int:
        raise udsoncan.DidCodec.ReadAllRemainingData


@contextlib.contextmanager
def uds_client_for(scenario: Scenario, channel: str, **client_kwargs: Any) -> Generator[Client]:
    """A stock `udsoncan.Client` talking to a virtual ECU built from
    `scenario`, over `channel` — this project's own T3 differential oracle
    for INF-05 (`docs/inf-05-simulator-reuse-evaluation.md`). No Tapwright
    code sits in this path: the client's ISO-TP stack and UDS layer are both
    `udsoncan`/`can-isotp` used exactly as an external caller would use them.

    Request/response IDs are swapped relative to the scenario's, matching the
    ECU's own perspective (it *receives* on `request_id`, this client
    therefore *transmits* on it).
    """
    bus = can.Bus(interface="socketcan", channel=channel, receive_own_messages=False)
    stack = isotp.CanStack(
        bus=bus,
        address=isotp.Address(
            isotp.AddressingMode.Normal_11bits,
            rxid=scenario.response_id,
            txid=scenario.request_id,
        ),
        error_handler=lambda _error: None,
    )
    connection = PythonIsoTpConnection(stack)

    config = dict(udsoncan.configs.default_client_config)
    # 'default' is udsoncan's own wildcard key (see check_did_config /
    # fetch_codec_definition_from_config in udsoncan/common/dids.py) — needed
    # so a client can read a DID the *scenario* never configured, e.g.
    # test_read_unconfigured_did_returns_request_out_of_range: that case is
    # specifically about the server rejecting an unknown DID, which requires
    # the request to be sendable at all, not about the client already
    # knowing the DID doesn't exist.
    config["data_identifiers"] = {**dict.fromkeys(scenario.dids, _RawCodec), "default": _RawCodec}
    config.update(client_kwargs.pop("config_overrides", {}))

    try:
        with Client(connection, config=config, **client_kwargs) as client:
            yield client
    finally:
        bus.shutdown()


@pytest.fixture
def uds_client_factory() -> Any:
    """Fixture form of `uds_client_for`, injected without any cross-file
    import — `tests/` isn't a package, so test files reach this helper as a
    fixture rather than `from tests.conftest import ...`. Usage:

        def test_x(vcan_channel, uds_client_factory):
            with uds_client_factory(scenario, vcan_channel) as client:
                ...
    """
    return uds_client_for


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

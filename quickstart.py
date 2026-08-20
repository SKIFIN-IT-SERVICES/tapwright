# SPDX-License-Identifier: Apache-2.0

"""The container image's entrypoint (RUN-08, `FW-REQ-021`) — ADR-005's
"zero-hardware onboarding is first-class" promise, demonstrated with no
external ECU, no bench, and no host setup beyond the `--cap-add` flags
`docker run` was given: brings up a `vcan0` interface inside the
container's own network namespace, starts a `VirtualECU`, and completes
one UDS ReadDataByIdentifier round-trip through it.

    docker run --rm --cap-add=NET_ADMIN --cap-add=NET_RAW tapwright

`vcan0` has to be created fresh here rather than at build time: a
container's network namespace does not persist between `docker run`
invocations, so any interface created during `docker build` would be gone
by the time the container actually runs.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import udsoncan

from tapwright.diag.uds_client import open_uds_client
from tapwright.diag.virtual_ecu import DIDConfig, Scenario, VirtualECU
from tapwright.hal import open_bus

VCAN_CHANNEL = "vcan0"


def bring_up_vcan(channel: str) -> None:
    """Create and bring up `channel` inside this container's own network
    namespace. Requires CAP_NET_ADMIN — the kernel module itself must
    already be loaded on the *host* (a container shares the host kernel;
    no image can carry a kernel module of its own), which is why this
    raises an actionable message rather than a bare traceback when it
    fails: the fix is a `docker run` flag, not something inside the image.
    """
    result = subprocess.run(
        ["ip", "link", "add", "dev", channel, "type", "vcan"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"Could not create '{channel}': {result.stderr.strip()}\n\n"
            "This container needs CAP_NET_ADMIN and CAP_NET_RAW to bring up "
            "its own virtual CAN interface. Run with:\n\n"
            "    docker run --cap-add=NET_ADMIN --cap-add=NET_RAW ...\n\n"
            "(The vcan kernel module also has to be loadable on the host "
            "kernel already -- containers share it, they cannot load their "
            "own. On the host: sudo modprobe vcan)",
            file=sys.stderr,
        )
        sys.exit(1)

    subprocess.run(["ip", "link", "set", "up", channel], check=True)


class _RawCodec(udsoncan.DidCodec):
    """Treats a DID's payload as opaque bytes -- udsoncan requires a codec
    per DID before it will decode a ReadDataByIdentifier response at all.
    Not imported from tests/: this script has to stand alone as a real
    container entrypoint, not depend on the test tree.
    """

    def encode(self, *did_value: Any) -> bytes:
        (value,) = did_value
        return bytes(value)

    def decode(self, did_payload: bytes) -> bytes:
        return bytes(did_payload)

    def __len__(self) -> int:
        raise udsoncan.DidCodec.ReadAllRemainingData


def run_quickstart(channel: str) -> None:
    scenario = Scenario(dids={0xF190: DIDConfig(value=b"TAPWRIGHT-QUICKSTART")})

    with VirtualECU(scenario, channel=channel):
        bus = open_bus(backend="socketcan", channel=channel)
        try:
            client = open_uds_client(
                bus,
                rxid=scenario.response_id,
                txid=scenario.request_id,
                config={"data_identifiers": {0xF190: _RawCodec}},
            )
            with client:
                response = client.read_data_by_identifier(0xF190)
        finally:
            bus.shutdown()

    value = response.service_data.values[0xF190]
    print(f"quickstart OK: read DID 0xF190 = {value!r} from a virtual ECU, no hardware")


def main() -> int:
    bring_up_vcan(VCAN_CHANNEL)
    run_quickstart(VCAN_CHANNEL)
    return 0


if __name__ == "__main__":
    sys.exit(main())

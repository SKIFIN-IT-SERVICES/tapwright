# SPDX-License-Identifier: Apache-2.0

"""`VirtualECU` — the public entry point to the virtual UDS ECU responder.

    from tapwright.diag.virtual_ecu import VirtualECU, Scenario, DIDConfig

    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN...")})
    with VirtualECU(scenario, channel="vcan0"):
        ...  # drive it with any UDS client, e.g. udsoncan

This is the whole of `TOOL-REQ-026`'s "zero hardware" promise in code: no
python-can backend selection, no HAL layer, no bus abstraction — just a
scenario and a `vcan` interface name.
"""

from __future__ import annotations

from types import TracebackType

from .scenario import Scenario
from .transport import ECUTransport


class VirtualECU:
    """A UDS ECU simulated on a `vcan` interface, per `scenario`.

    Usable directly (`start()`/`stop()`) or as a context manager, which stops
    the responder on exit even if the `with` body raises — see
    `test_usable_as_a_context_manager` in the test plan for why that matters:
    a fixture that leaks state on a *failing* test is worse than one that
    leaks state on a passing one, because the failure case is the one tests
    exist to catch.
    """

    def __init__(self, scenario: Scenario, channel: str) -> None:
        self.scenario = scenario
        self.channel = channel
        self._transport = ECUTransport(scenario, channel)

    def start(self) -> None:
        self._transport.start()

    def stop(self) -> None:
        self._transport.stop()

    def __enter__(self) -> VirtualECU:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

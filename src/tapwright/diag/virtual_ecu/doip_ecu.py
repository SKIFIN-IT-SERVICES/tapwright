# SPDX-License-Identifier: Apache-2.0

"""`DoIPVirtualECU` — the DoIP-transport twin of `VirtualECU` (`ecu.py`).

    from tapwright.diag.virtual_ecu import DoIPVirtualECU, Scenario, DIDConfig

    scenario = Scenario(dids={0xF190: DIDConfig(value=b"VIN...")})
    with DoIPVirtualECU(scenario) as ecu:
        ...  # drive it with doipclient, or open_doip_uds_client() (DIAG-03)

Same `Scenario`/`ProtocolState` core as the CAN-side `VirtualECU` — only the
transport differs, per the reuse discipline decided on issue #15.
"""

from __future__ import annotations

from types import TracebackType

from .doip_transport import DoIPTransport
from .scenario import Scenario


class DoIPVirtualECU:
    """A UDS ECU simulated over DoIP, per `scenario`. See `VirtualECU`
    (`ecu.py`) for the CAN-transport equivalent — usage and lifecycle
    contract are identical (context manager, start()/stop()).
    """

    def __init__(
        self,
        scenario: Scenario,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        ecu_logical_address: int = 0x0001,
    ) -> None:
        self.scenario = scenario
        self.ecu_logical_address = ecu_logical_address
        self._transport = DoIPTransport(
            scenario, host=host, port=port, ecu_logical_address=ecu_logical_address
        )

    @property
    def port(self) -> int | None:
        """The bound TCP port — meaningful only after `start()`. Useful when
        constructed with `port=0` (the default), which asks the OS for a
        free port rather than risking a collision with another test.
        """
        return self._transport.bound_port

    def start(self) -> None:
        self._transport.start()

    def stop(self) -> None:
        self._transport.stop()

    def __enter__(self) -> DoIPVirtualECU:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

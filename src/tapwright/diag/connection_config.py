# SPDX-License-Identifier: Apache-2.0

"""The transport-agnostic construction point `docs/architecture.md` §4
requires (DIAG-04): a single `open_connection()`, dispatching on a config
object's *type* rather than a string a caller could typo.

    from tapwright.diag.connection_config import CanConnectionConfig, open_connection
    from tapwright.hal import open_bus

    bus = open_bus(backend="socketcan", channel="vcan0")
    config = CanConnectionConfig(bus=bus, rxid=0x7E0, txid=0x7E8)
    with open_connection(config) as client:
        response = client.read_data_by_identifier(0xF190)

Swapping `CanConnectionConfig` for `DoipConnectionConfig` is the entire
change needed to move to DoIP — `open_connection()`'s call site, and every
line of code that uses the returned `client`, stays identical. That
identity is DIAG-04's own oracle, exercised directly in
`tests/differential/test_connection_abstraction.py`.

"SOVD-shaped": a future `SovdConnectionConfig` (DIAG-07, Should) is meant to
slot into the `isinstance` dispatch below without changing
`open_connection()`'s signature or any code that already calls it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import isotp
from udsoncan.client import Client

from tapwright.hal import Bus

from .doip_client import open_doip_uds_client
from .uds_client import open_uds_client


@dataclass(frozen=True)
class CanConnectionConfig:
    """Construction parameters for a UDS-over-ISO-TP-over-CAN connection —
    everything `open_uds_client()` needs, held as data rather than passed
    positionally, so `open_connection()` can dispatch on this type alone.
    """

    bus: Bus
    rxid: int
    txid: int
    addressing_mode: isotp.AddressingMode = isotp.AddressingMode.Normal_11bits


@dataclass(frozen=True)
class DoipConnectionConfig:
    """Construction parameters for a UDS-over-DoIP connection — everything
    `open_doip_uds_client()` needs, held as data for the same reason.
    """

    ecu_ip_address: str
    ecu_logical_address: int
    tcp_port: int = 13400
    client_logical_address: int = 0xE00


ConnectionConfig = CanConnectionConfig | DoipConnectionConfig


def open_connection(
    transport_config: ConnectionConfig,
    *,
    config: dict[str, Any] | None = None,
    request_timeout: float | None = None,
) -> Client:
    """Open a `udsoncan.Client` over whichever transport `transport_config`
    describes. The caller never branches on transport — that's the point.
    """
    if isinstance(transport_config, CanConnectionConfig):
        return open_uds_client(
            transport_config.bus,
            rxid=transport_config.rxid,
            txid=transport_config.txid,
            addressing_mode=transport_config.addressing_mode,
            config=config,
            request_timeout=request_timeout,
        )
    if isinstance(transport_config, DoipConnectionConfig):
        return open_doip_uds_client(
            transport_config.ecu_ip_address,
            transport_config.ecu_logical_address,
            tcp_port=transport_config.tcp_port,
            client_logical_address=transport_config.client_logical_address,
            config=config,
            request_timeout=request_timeout,
        )
    raise TypeError(f"unsupported connection config type: {type(transport_config)!r}")

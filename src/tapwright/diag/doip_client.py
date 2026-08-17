# SPDX-License-Identifier: Apache-2.0

"""`open_doip_uds_client()` — the DoIP-transport twin of DIAG-02's
`open_uds_client()`.

    from tapwright.diag.doip_client import open_doip_uds_client

    with open_doip_uds_client("127.0.0.1", 0x0001, port=13400) as client:
        response = client.read_data_by_identifier(0xF190)

Unlike DIAG-01/DIAG-02, this loop writes **no connection adapter**:
`doipclient` ships its own official `udsoncan.connections.BaseConnection`
implementation, `doipclient.connectors.DoIPClientUDSConnector` — per
`AGENTS.md`'s reuse rule, that *is* the adapter. This factory only wires
`doipclient.DoIPClient` + that connector + `udsoncan.Client` together.

The returned object is the same `udsoncan.Client` type `open_uds_client()`
returns — this *is* `docs/architecture.md` §4's "one client object,
transport is a construction-time choice" property, now demonstrated across
two transports rather than merely asserted.
"""

from __future__ import annotations

from typing import Any

import udsoncan
import udsoncan.configs
from doipclient import DoIPClient
from doipclient.connectors import DoIPClientUDSConnector
from udsoncan.client import Client


def open_doip_uds_client(
    ecu_ip_address: str,
    ecu_logical_address: int,
    *,
    tcp_port: int = 13400,
    client_logical_address: int = 0xE00,
    config: dict[str, Any] | None = None,
    request_timeout: float | None = None,
) -> Client:
    """Build a `udsoncan.Client` talking UDS-over-DoIP to `ecu_ip_address`.

    `config` is merged over `udsoncan.configs.default_client_config` — most
    callers will at least need to supply `data_identifiers` (a DID -> codec
    map; `udsoncan` cannot decode a DID it has no codec for).
    """
    doip_layer = DoIPClient(
        ecu_ip_address,
        ecu_logical_address,
        tcp_port=tcp_port,
        client_logical_address=client_logical_address,
    )
    connection = DoIPClientUDSConnector(doip_layer, close_connection=True)

    client_config = dict(udsoncan.configs.default_client_config)
    if config:
        client_config.update(config)

    # See open_uds_client()'s matching comment: dict(default_client_config)
    # + .update() rebuilds a plain dict with ClientConfig's keys, but mypy
    # can't see the shape survived the round trip.
    return Client(connection, config=client_config, request_timeout=request_timeout)  # type: ignore[arg-type]

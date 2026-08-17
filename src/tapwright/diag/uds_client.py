# SPDX-License-Identifier: Apache-2.0

"""`open_uds_client()` — the transport-agnostic construction point
`docs/architecture.md` §4 requires (TOOL-REQ-027, ADR-004).

    from tapwright.diag.uds_client import open_uds_client
    from tapwright.hal import open_bus

    bus = open_bus(backend="socketcan", channel="vcan0")
    with open_uds_client(bus, rxid=0x7E0, txid=0x7E8) as client:
        response = client.read_data_by_identifier(0xF190)

The returned object is a plain `udsoncan.Client` — per `AGENTS.md`'s reuse
rule, that *is* the UDS client this project ships; nothing about UDS service
semantics is reimplemented here. Swapping to a DoIP transport later (DIAG-03)
means a different factory function producing the same `udsoncan.Client`
type, invisible to calling code — the "one client object" §4 requires,
achieved by construction-time choice rather than a custom client class.
"""

from __future__ import annotations

from typing import Any

import isotp
import udsoncan
import udsoncan.configs
from udsoncan.client import Client

from tapwright.hal import Bus

from .connection import TapwrightIsoTpConnection
from .isotp_transport import IsoTpTransport


def open_uds_client(
    bus: Bus,
    *,
    rxid: int,
    txid: int,
    addressing_mode: isotp.AddressingMode = isotp.AddressingMode.Normal_11bits,
    config: dict[str, Any] | None = None,
    request_timeout: float | None = None,
) -> Client:
    """Build a `udsoncan.Client` talking UDS-over-ISO-TP over `bus`.

    `config` is merged over `udsoncan.configs.default_client_config` — most
    callers will at least need to supply `data_identifiers` (a DID -> codec
    map; `udsoncan` cannot decode a DID it has no codec for).
    """
    transport = IsoTpTransport(bus, rxid=rxid, txid=txid, addressing_mode=addressing_mode)
    connection = TapwrightIsoTpConnection(transport)

    client_config = dict(udsoncan.configs.default_client_config)
    if config:
        client_config.update(config)

    # dict(default_client_config) + .update() rebuilds a plain dict with the
    # same keys as udsoncan's ClientConfig TypedDict, but mypy can't see the
    # shape survived the round trip — it did, this is just a TypedDict
    # ergonomics gap in how udsoncan's own config is meant to be extended.
    return Client(connection, config=client_config, request_timeout=request_timeout)  # type: ignore[arg-type]

# SPDX-License-Identifier: Apache-2.0

"""L2 — Diagnostics engine.

UDS (ISO 14229) client over ISO-TP and DoIP (ISO 13400), ODX/PDX read-only
import, and the virtual-ECU responder used for zero-hardware testing.

This module's public API is a deliberately constrained interface: it must
stay clean and scriptable enough for an external tool (in the spirit of
projects like Gallia) to wrap it later without forking it. See
ARCHITECTURE.md at the repository root before changing this module's
public surface.

Implemented so far: `virtual_ecu` (INF-05/DIAG-03, the zero-hardware UDS
responder — CAN via `ecu.py`/`transport.py`, DoIP via
`doip_ecu.py`/`doip_transport.py`, one shared `ProtocolState`),
`isotp_transport` (DIAG-01, ISO-TP over `hal.Bus`), `uds_client` +
`connection` (DIAG-02, the CAN-side client — `open_uds_client()`), and
`doip_client` (DIAG-03, the DoIP-side client — `open_doip_uds_client()`,
returning the same `udsoncan.Client` type). Submodules are accessed
directly (`tapwright.diag.uds_client`, etc.) rather than re-exported here,
so importing `tapwright.diag` itself stays cheap — it doesn't pull in
`can`/`isotp`/`udsoncan`/`doipclient` unless a submodule that actually
needs them is imported.
"""

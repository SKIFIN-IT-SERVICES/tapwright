# SPDX-License-Identifier: Apache-2.0

"""L2 — Diagnostics engine.

UDS (ISO 14229) client over ISO-TP and DoIP (ISO 13400), ODX/PDX read-only
import, and the virtual-ECU responder used for zero-hardware testing.

This module's public API is a deliberately constrained interface: it must
stay clean and scriptable enough for an external tool (in the spirit of
projects like Gallia) to wrap it later without forking it. See
ARCHITECTURE.md at the repository root before changing this module's
public surface.

Implemented so far: `virtual_ecu` (INF-05, the zero-hardware UDS responder)
and `isotp_transport` (DIAG-01, ISO-TP over `hal.Bus`). Both are accessed
directly (`tapwright.diag.virtual_ecu`, `tapwright.diag.isotp_transport`)
rather than re-exported here, so importing `tapwright.diag` itself stays
cheap — it doesn't pull in `can`/`isotp`/`udsoncan` unless a submodule that
actually needs them is imported. The UDS client (DIAG-02) and DoIP
transport (DIAG-03) are not yet built.
"""

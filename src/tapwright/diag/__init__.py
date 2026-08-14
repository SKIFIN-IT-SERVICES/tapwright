# SPDX-License-Identifier: Apache-2.0

"""L2 — Diagnostics engine.

UDS (ISO 14229) client over ISO-TP and DoIP (ISO 13400), ODX/PDX read-only
import, and the virtual-ECU responder used for zero-hardware testing.

This module's public API is a deliberately constrained interface: it must
stay clean and scriptable enough for an external tool (in the spirit of
projects like Gallia) to wrap it later without forking it. See
ARCHITECTURE.md at the repository root before changing this module's
public surface.

Not yet implemented — this is scaffolding for Milestones M1-M2.
"""

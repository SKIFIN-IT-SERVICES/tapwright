# SPDX-License-Identifier: Apache-2.0

"""L1 — Bus core.

Frame-level CAN/CAN-FD/LIN send and receive, basic cyclic stimulation. See
ARCHITECTURE.md at the repository root.

Frame-level send/recv lives in `tapwright.hal` (L0). Cyclic stimulation
(BUS-07, `TOOL-REQ-011`) is this module's own addition, layered on top:
`hal.Bus.send_periodic()` for the explicit-period path,
`start_cyclic_from_dbc()` here for the DBC-driven convenience.
"""

from .cyclic import start_cyclic_from_dbc

__all__ = ["start_cyclic_from_dbc"]

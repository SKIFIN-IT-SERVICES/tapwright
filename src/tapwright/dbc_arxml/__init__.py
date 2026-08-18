# SPDX-License-Identifier: Apache-2.0

"""L1 — DBC / ARXML / LDF / A2L decode.

Symbolic decode of bus traffic from DBC and ARXML (Classic + Adaptive
AUTOSAR) communication matrices, LDF for LIN, and A2L (ASAM MCD-2 MC) for
measurement/calibration variable descriptions. See ARCHITECTURE.md at the
repository root.

Implemented so far: `database.py` (BUS-01, `TOOL-REQ-014`) — `load_dbc()` +
`DbcDatabase`, decoding/encoding against `tapwright.hal.Frame` directly.
ARXML (`TOOL-REQ-015`), LDF (`TOOL-REQ-016`), and A2L (`TOOL-REQ-017`) are
not yet built (BUS-02 through BUS-04).
"""

from __future__ import annotations

from .database import DbcDatabase, load_dbc
from .errors import DatabaseLoadError, DbcArxmlError, UnknownMessageError

__all__ = [
    "DatabaseLoadError",
    "DbcArxmlError",
    "DbcDatabase",
    "UnknownMessageError",
    "load_dbc",
]

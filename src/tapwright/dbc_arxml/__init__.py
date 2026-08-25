# SPDX-License-Identifier: Apache-2.0

"""L1 — DBC / ARXML / LDF / A2L decode.

Symbolic decode of bus traffic from DBC and ARXML (Classic + Adaptive
AUTOSAR) communication matrices, LDF for LIN, and A2L (ASAM MCD-2 MC) for
measurement/calibration variable descriptions. See ARCHITECTURE.md at the
repository root.

Implemented so far: `database.py` — `load_dbc()` (BUS-01, `TOOL-REQ-014`)
and `load_arxml()` (BUS-02, `TOOL-REQ-015`), both returning `CanDatabase`
(one format-agnostic wrapper — `cantools` parses either source into the
same underlying type), decoding/encoding against `tapwright.hal.Frame`
directly. LDF (`TOOL-REQ-016`) and A2L (`TOOL-REQ-017`) are not yet built
(BUS-03/BUS-04).
"""

from __future__ import annotations

from .database import CanDatabase, load_arxml, load_dbc
from .errors import DatabaseLoadError, DbcArxmlError, UnknownMessageError

__all__ = [
    "CanDatabase",
    "DatabaseLoadError",
    "DbcArxmlError",
    "UnknownMessageError",
    "load_arxml",
    "load_dbc",
]

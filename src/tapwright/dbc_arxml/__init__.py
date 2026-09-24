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
directly. `a2l_import.py` — `load_a2l()` (BUS-04, `TOOL-REQ-017`),
returning `A2lDatabase` for read-only ECU variable name/address
resolution. **`a2l_import.py` wraps `pya2l` under an accepted licensing
risk — see that module's own docstring and `licences.toml`'s `pya2l`
entry before touching it.** LDF (`TOOL-REQ-016`) is not yet built
(BUS-03).
"""

from __future__ import annotations

from .a2l_import import A2lDatabase, load_a2l
from .database import CanDatabase, load_arxml, load_dbc
from .errors import (
    A2lLoadError,
    DatabaseLoadError,
    DbcArxmlError,
    NoAddressError,
    UnknownMessageError,
    UnknownVariableError,
)

__all__ = [
    "A2lDatabase",
    "A2lLoadError",
    "CanDatabase",
    "DatabaseLoadError",
    "DbcArxmlError",
    "NoAddressError",
    "UnknownMessageError",
    "UnknownVariableError",
    "load_a2l",
    "load_arxml",
    "load_dbc",
]

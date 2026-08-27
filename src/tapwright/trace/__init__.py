# SPDX-License-Identifier: Apache-2.0

"""L1/L3 — Trace read/write and query.

BLF, ASC, and MDF4 read and write — interop with the Vector-format
installed base is non-negotiable, not just self-consistency. See
ARCHITECTURE.md at the repository root.

Implemented so far: `io.py` (BUS-05, `TOOL-REQ-019`/`TOOL-REQ-020`) —
`write_blf()`/`read_blf()` and `write_asc()`/`read_asc()`, wrapping
`python-can`'s own reader/writer classes rather than reimplementing either
format. MDF4 (`TOOL-REQ-021`, BUS-06) is not yet built.
"""

from __future__ import annotations

from .errors import TraceError, TraceLoadError
from .io import read_asc, read_blf, write_asc, write_blf

__all__ = [
    "TraceError",
    "TraceLoadError",
    "read_asc",
    "read_blf",
    "write_asc",
    "write_blf",
]

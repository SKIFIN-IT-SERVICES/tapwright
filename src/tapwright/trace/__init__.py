# SPDX-License-Identifier: Apache-2.0

"""L1/L3 — Trace read/write and query.

BLF, ASC, and MDF4 read and write — interop with the Vector-format
installed base is non-negotiable, not just self-consistency. See
ARCHITECTURE.md at the repository root.

`io.py` wraps `python-can`'s own reader/writer classes rather than
reimplementing any format: `write_blf()`/`read_blf()` and
`write_asc()`/`read_asc()` (BUS-05, `TOOL-REQ-019`/`TOOL-REQ-020`),
`write_mdf4()`/`read_mdf4()` (BUS-06, `TOOL-REQ-021` — requires the
optional `mdf4` extra, `pip install tapwright[mdf4]`).
"""

from __future__ import annotations

from .errors import TraceError, TraceLoadError
from .io import read_asc, read_blf, read_mdf4, write_asc, write_blf, write_mdf4

__all__ = [
    "TraceError",
    "TraceLoadError",
    "read_asc",
    "read_blf",
    "read_mdf4",
    "write_asc",
    "write_blf",
    "write_mdf4",
]

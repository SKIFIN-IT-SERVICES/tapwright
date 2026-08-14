# SPDX-License-Identifier: Apache-2.0

"""TOML loading that works on Python 3.10.

``tomllib`` landed in 3.11; the support floor is 3.10 (FW-REQ-002, and the CI
matrix runs 3.10/3.11/3.12). One import shim beats repeating this in five
scripts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib


def load(path: Path) -> dict[str, Any]:
    """Parse a TOML file."""
    with path.open("rb") as handle:
        return tomllib.load(handle)

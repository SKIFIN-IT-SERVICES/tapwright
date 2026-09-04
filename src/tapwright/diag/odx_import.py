# SPDX-License-Identifier: Apache-2.0

"""ODX/PDX read-only import → DID/routine name resolution (DIAG-06,
`TOOL-REQ-025`).

Per `AGENTS.md`'s reuse rule, wraps `odxtools`' own `Database`/diag-layer
API (`odxtools.load_pdx_file()`/`load_odx_file()`) rather than
reimplementing ODX/PDX's XML schema parsing. Write/authoring is
explicitly out of scope, matching the requirement's own wording.

**Weak oracle, by the requirement's own design** (see the plan's own
note): "ODX semantic correctness cannot be fully machine-verified. The
loop closes on structural correctness; semantic spot-checks are a T5
human gate." `OdxDatabase` proves it can load a real ODX/PDX file and
resolve names structurally — it does not certify that a given real OEM
database's semantics are correct.

`resolve_service_name()` matches by `Request.coded_const_prefix()` — the
fixed byte sequence identifying a service's request (its SID plus any
constant DID/routine-ID bytes) — rather than `Request.decode()`, which
`odxtools` found directly during this loop's fixture authoring to only
*warn* on a coded-const mismatch rather than raise, making it unsuitable
for telling two services' requests apart.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree

import odxtools

from .errors import OdxLoadError, OdxUnknownEcuError, OdxUnknownServiceError

if TYPE_CHECKING:
    from odxtools.database import Database
    from odxtools.diaglayers.diaglayer import DiagLayer


class OdxDatabase:
    """A loaded ODX/PDX database. Always constructed via `load_pdx()`/
    `load_odx()` — never directly — so a missing, invalid, or malformed
    file raises `OdxLoadError` before any partially-loaded state exists.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def ecu_names(self) -> list[str]:
        """Short names of every diagnostic layer (ECU variant, base
        variant, or protocol) across every container in this database.
        """
        return [
            diag_layer.short_name
            for container in self._db.diag_layer_containers
            for diag_layer in container.diag_layers
        ]

    def resolve_service_name(self, ecu_name: str, raw_request: bytes) -> str:
        """The name of the diagnostic service in `ecu_name` whose request
        `raw_request` matches — resolving a raw DID/routine-ID read off
        the wire back to the name the ODX/PDX database gave it.
        """
        diag_layer = self._find_ecu(ecu_name)
        for service in diag_layer.services:
            if service.request is None:
                continue  # e.g. a response-only or malformed service definition
            prefix = bytes(service.request.coded_const_prefix())
            if raw_request.startswith(prefix):
                return service.short_name
        raise OdxUnknownServiceError(
            f"no service in ECU {ecu_name!r} matches request {raw_request.hex()!r}"
        )

    def _find_ecu(self, ecu_name: str) -> DiagLayer:
        for container in self._db.diag_layer_containers:
            for diag_layer in container.diag_layers:
                if diag_layer.short_name == ecu_name:
                    return diag_layer
        raise OdxUnknownEcuError(f"no ECU named {ecu_name!r} in this database")


def load_pdx(path: str | Path) -> OdxDatabase:
    """Load a PDX file (a zip container bundling one or more ODX
    documents)."""
    try:
        db = odxtools.load_pdx_file(path)
    except (FileNotFoundError, OSError, zipfile.BadZipFile) as exc:
        raise OdxLoadError(f"could not load PDX file {path!r}: {exc}") from exc
    return OdxDatabase(db)


def load_odx(path: str | Path) -> OdxDatabase:
    """Load a standalone ODX XML document (not a PDX zip container)."""
    try:
        db = odxtools.load_odx_file(path)
    except (FileNotFoundError, OSError, ElementTree.ParseError) as exc:
        raise OdxLoadError(f"could not load ODX file {path!r}: {exc}") from exc
    return OdxDatabase(db)

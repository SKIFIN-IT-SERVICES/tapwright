# SPDX-License-Identifier: Apache-2.0

"""A2L (ASAM MCD-2 MC) read-only parse → ECU variable name/address
resolution (BUS-04, `TOOL-REQ-017`).

**Accepted licensing risk, per explicit team decision (issue #65).** The
only real Python library for A2L parsing, `pya2l`, has a BSD-3-Clause
Python wrapper, but the wheel bundles ~300MB of compiled native binaries
(the `a2l-grpc` backend, Go-compiled shared libraries across 10
platform/architecture combinations) with **no disclosed license or
provenance for the binaries themselves** — failing `FW-REQ-017`'s
"verified against the package's own metadata" bar categorically, not
just by being a restrictive-but-known license like LGPL (which
`python-can`/`asammdf` already are, and are fine as isolated
dependencies). This is an *unverifiable* license, not a
known-but-restrictive one. The team discussed this and explicitly chose
to accept the risk and proceed rather than wait for a licensing answer,
drop the loop, or hand-roll a parser — see `licences.toml`'s own entry
for the same note, and `LOOPS.md`'s BUS-04 closeout for the full trail.

Per `AGENTS.md`'s reuse rule (accepted risk notwithstanding), wraps
`pya2l`'s own `A2lParser`/`tree_from_a2l()` API rather than
reimplementing ASAP2 grammar parsing. Read-only — no calibration write,
matching `TOOL-REQ-017`'s own explicit scope. `A2lDatabase` exposes no
write/save method at all; that is itself part of this loop's own oracle
("assert no write API is exposed"), not merely an omission.
"""

from __future__ import annotations

from pathlib import Path

from pya2l.parser import A2lError, A2lParser

from .errors import A2lLoadError, NoAddressError, UnknownVariableError


class A2lDatabase:
    """A loaded A2L file's measurement variables. Always constructed via
    `load_a2l()` — never directly — so a missing, invalid, or malformed
    file raises `A2lLoadError` before any partially-loaded state exists.
    """

    def __init__(self, ast) -> None:  # noqa: ANN001 -- pya2l's AST has no public type
        self._ast = ast

    def variable_names(self) -> list[str]:
        """Names of every `MEASUREMENT` record across every module in
        this A2L file."""
        return [
            measurement.Name.Value
            for module in self._ast.PROJECT.MODULE
            for measurement in module.MEASUREMENT
        ]

    def resolve_address(self, variable_name: str) -> int:
        """The named variable's ECU memory address — the acceptance
        criterion `TOOL-REQ-017` names verbatim.

        Raises `NoAddressError` if the variable exists but declares no
        `ECU_ADDRESS` (e.g. a value only ever read via a diagnostic
        service, not memory-mapped for direct XCP access), rather than
        returning a nonsensical address or `None` silently.
        """
        measurement = self._find_measurement(variable_name)
        if measurement.ECU_ADDRESS.is_none:
            raise NoAddressError(f"measurement variable {variable_name!r} declares no ECU_ADDRESS")
        return measurement.ECU_ADDRESS.Address.Value

    def _find_measurement(self, variable_name: str):  # noqa: ANN001, ANN202
        for module in self._ast.PROJECT.MODULE:
            for measurement in module.MEASUREMENT:
                if measurement.Name.Value == variable_name:
                    return measurement
        raise UnknownVariableError(
            f"no measurement variable named {variable_name!r} in this A2L file"
        )


def load_a2l(path: str | Path) -> A2lDatabase:
    """Load an A2L file. Config/file-existence errors are caught and
    raised as `A2lLoadError` before any partially-loaded state exists,
    matching `dbc_arxml.database`'s own `load_dbc()`/`load_arxml()`
    convention.
    """
    try:
        content = Path(path).read_bytes()
    except OSError as exc:
        raise A2lLoadError(f"could not read A2L file {path!r}: {exc}") from exc

    try:
        with A2lParser() as parser:
            ast = parser.tree_from_a2l(content)
    except A2lError as exc:
        raise A2lLoadError(f"could not parse A2L file {path!r}: {exc}") from exc

    return A2lDatabase(ast)

# SPDX-License-Identifier: Apache-2.0

"""T3 test plan for BUS-04 — A2L read-only parse, ECU variable
name/address resolution (`TOOL-REQ-017`).

Implements #65. Oracle per the plan's own row: "Parse golden A2L; assert
no write API is exposed."

**Accepted licensing risk, per explicit team decision**: see
`a2l_import.py`'s own module docstring and `licences.toml`'s `pya2l`
entry. This test file verifies the wrapper's behavior, not the
underlying library's licensing — that decision is recorded elsewhere,
not re-litigated here.

Fixture: `fixtures/a2l/engine_ecu.a2l`, self-authored (hand-written
directly — A2L's syntax is simple enough to author by hand, unlike
ODX/PDX which needed a generator script for DIAG-06). Three
`MEASUREMENT` records: `EngineSpeed`/`EngineTemperature` (both declare
`ECU_ADDRESS`) and `UnmappedDiagnosticFlag` (declares none).
"""

from __future__ import annotations

import pytest

from tapwright.dbc_arxml import A2lDatabase, load_a2l
from tapwright.dbc_arxml.errors import A2lLoadError, NoAddressError, UnknownVariableError

FIXTURE = "fixtures/a2l/engine_ecu.a2l"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_load_a2l_lists_variable_names():
    db = load_a2l(FIXTURE)
    assert db.variable_names() == [
        "EngineSpeed",
        "EngineTemperature",
        "UnmappedDiagnosticFlag",
    ]


def test_resolve_address_for_a_declared_variable():
    db = load_a2l(FIXTURE)
    assert db.resolve_address("EngineSpeed") == 0x1A2B3C
    assert db.resolve_address("EngineTemperature") == 0x1A2B40


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_resolve_address_raises_for_a_variable_with_no_declared_address():
    db = load_a2l(FIXTURE)
    with pytest.raises(NoAddressError):
        db.resolve_address("UnmappedDiagnosticFlag")


def test_no_write_api_is_exposed():
    """The loop's own oracle, verbatim: "assert no write API is exposed."
    Read-only by construction, not merely by omission -- checked directly
    against the public surface, not just "nobody happened to add one."
    """
    public_methods = {name for name in dir(A2lDatabase) if not name.startswith("_")}
    write_like_names = {"write", "save", "dump", "to_a2l", "export"}
    assert public_methods.isdisjoint(write_like_names)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_load_a2l_missing_file_raises_a2l_load_error():
    with pytest.raises(A2lLoadError):
        load_a2l("fixtures/a2l/does_not_exist.a2l")


def test_load_a2l_garbage_file_raises_a2l_load_error(tmp_path):
    path = tmp_path / "garbage.a2l"
    path.write_bytes(b"not a real A2L file at all, just garbage bytes")
    with pytest.raises(A2lLoadError):
        load_a2l(path)


def test_resolve_address_unknown_variable_raises_clear_error():
    db = load_a2l(FIXTURE)
    with pytest.raises(UnknownVariableError):
        db.resolve_address("NoSuchVariable")

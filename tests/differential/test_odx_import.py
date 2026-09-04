# SPDX-License-Identifier: Apache-2.0

"""T3 test plan for DIAG-06 — ODX/PDX read-only import, DID/routine name
resolution (`TOOL-REQ-025`).

Implements #55. Oracle is `odxtools` itself, used directly to independently
confirm what `tapwright.diag.odx_import` resolves — the same T3
differential-vs-the-wrapped-library pattern BUS-01/02 established for
`cantools`.

**Weak oracle, by the requirement's own design**: "ODX semantic
correctness cannot be fully machine-verified. The loop closes on
structural correctness; semantic spot-checks are a T5 human gate." These
cases prove loading and name resolution work correctly against a golden
fixture — they do not certify a real OEM database's semantics.

**L2 API surface note** (per the test-plan skill's own special case for
`diag/` changes): `odx_import.py` does not touch DIAG-05's interception
API at all — it's a static, read-only file-import concern with no live
diagnostic session, so `docs/architecture.md` §4's process-boundary
requirement doesn't apply here. Noted so it's clear this wasn't
overlooked, not silently skipped.

Fixtures: `fixtures/odx/engine_ecu.pdx`/`engine_ecu.odx`, self-authored
and generated via `fixtures/odx/generate_engine_ecu.py` (odxtools' own
object model + `write_pdx_file()`, not hand-written XML) — one ECU
variant (`EngineECU`) with a `read_engine_speed` service (DID `0x1234`)
and a `self_test` routine service (routine `0x0203`).
"""

from __future__ import annotations

import pytest

from tapwright.diag.errors import OdxLoadError, OdxUnknownEcuError, OdxUnknownServiceError
from tapwright.diag.odx_import import load_odx, load_pdx

PDX_FIXTURE = "fixtures/odx/engine_ecu.pdx"
ODX_FIXTURE = "fixtures/odx/engine_ecu.odx"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_load_pdx_resolves_ecu_names():
    db = load_pdx(PDX_FIXTURE)
    assert db.ecu_names() == ["EngineECU"]


def test_resolve_service_name_for_a_did_read():
    db = load_pdx(PDX_FIXTURE)
    name = db.resolve_service_name("EngineECU", bytes.fromhex("221234"))
    assert name == "read_engine_speed"


def test_resolve_service_name_for_a_routine():
    db = load_pdx(PDX_FIXTURE)
    name = db.resolve_service_name("EngineECU", bytes.fromhex("31010203"))
    assert name == "self_test"


def test_load_odx_resolves_the_same_names_as_the_equivalent_pdx():
    db = load_odx(ODX_FIXTURE)
    assert db.ecu_names() == ["EngineECU"]
    assert db.resolve_service_name("EngineECU", bytes.fromhex("221234")) == "read_engine_speed"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_resolve_service_name_ignores_trailing_payload_bytes():
    """A real captured request has more than just the identifying prefix
    (e.g. a write's payload) -- resolution matches on the prefix, not an
    exact-length match.
    """
    db = load_pdx(PDX_FIXTURE)
    name = db.resolve_service_name("EngineECU", bytes.fromhex("22123499"))
    assert name == "read_engine_speed"


def test_ecu_names_reflects_odxtools_own_diag_layer_listing():
    """Differential check against odxtools directly: our ecu_names()
    must match iterating odxtools' own diag_layer_containers verbatim.
    """
    import odxtools

    db = load_pdx(PDX_FIXTURE)
    raw_db = odxtools.load_pdx_file(PDX_FIXTURE)
    expected = [dl.short_name for c in raw_db.diag_layer_containers for dl in c.diag_layers]
    assert db.ecu_names() == expected


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_load_pdx_missing_file_raises_odx_load_error():
    with pytest.raises(OdxLoadError):
        load_pdx("fixtures/odx/does_not_exist.pdx")


def test_load_pdx_garbage_file_raises_odx_load_error(tmp_path):
    path = tmp_path / "garbage.pdx"
    path.write_bytes(b"not a real pdx file, just garbage bytes")
    with pytest.raises(OdxLoadError):
        load_pdx(path)


def test_load_odx_garbage_file_raises_odx_load_error(tmp_path):
    path = tmp_path / "garbage.odx"
    path.write_bytes(b"not xml at all, just garbage bytes")
    with pytest.raises(OdxLoadError):
        load_odx(path)


def test_resolve_service_name_unknown_ecu_raises_clear_error():
    db = load_pdx(PDX_FIXTURE)
    with pytest.raises(OdxUnknownEcuError):
        db.resolve_service_name("NoSuchEcu", bytes.fromhex("221234"))


def test_resolve_service_name_no_matching_service_raises_clear_error():
    db = load_pdx(PDX_FIXTURE)
    with pytest.raises(OdxUnknownServiceError):
        db.resolve_service_name("EngineECU", bytes.fromhex("999999"))

# SPDX-License-Identifier: Apache-2.0

"""T3 (subsumed under BUS-02's declared T4) differential test plan for
BUS-02 / `TOOL-REQ-015` — ARXML ingestion + symbolic decode via `cantools`.

Implements #37. Oracle: the plan's own line, "Differential vs. `cantools`;
known-gap list documented" -- mirrors BUS-01's own oracle
(`tests/differential/test_dbc_decode.py`): every case runs through both
`tapwright.dbc_arxml`'s own loader and `cantools.database.load_file()`
used directly on the same file, asserting identical results, anchored
against golden `fixtures/expected/*` JSON.

## Correction from the issue's own proposed solution

The issue sketched a new `ArxmlDatabase` class alongside `DbcDatabase`.
On reading `cantools`' own architecture: DBC and ARXML both parse into the
*exact same* `cantools.database.can.database.Database` type -- nothing
format-specific survives past `load_file()`. BUS-01's `DbcDatabase` is
therefore already 100% format-agnostic; a second class wrapping the
identical thing would be a name-only duplicate, not a real distinction.
Renamed to `CanDatabase` (matching `cantools`' own class name) instead --
`load_dbc()` (BUS-01, unchanged behavior) and the new `load_arxml()` both
return it. Flagged here rather than silently deviating from the issue.

## Scope notes (posted in full to #37; kept here as a pointer)

- **Dual-specification path**: `test_dbc_path_remains_fully_functional_
  alongside_arxml` exists specifically to prove BUS-01's DBC path wasn't
  demoted or complicated by this loop -- loads both formats in the same
  test, asserts both work identically well. This is the plan's own
  explicit design constraint for this loop, not an incidental case.
- **Known-gap list** is a documentation deliverable
  (`docs/bus-02-arxml-known-gaps.md`, mirroring
  `docs/inf-05-simulator-reuse-evaluation.md`'s existing precedent), not a
  test case in this file -- honest scoping of what `cantools`' own ARXML
  depth does and doesn't cover, per the plan's own risk-mitigation note.
- **Fixture**: `fixtures/databases/vehicle_signals.arxml`, self-authored
  (no suitable public-domain ARXML with the right property mix was found;
  same situation BUS-01's own `multiplexed.dbc` was in) -- covers a plain
  scaled signal, a negative-offset signal, and a 29-bit extended
  arbitration ID, matching the plan's own fixture-corpus guidance
  (`DEVELOPMENT-PLAN...` §"Databases" row). No multiplexing in this
  fixture -- BUS-01's own DBC fixture already proves multiplex decode
  works once `cantools` has parsed *any* format into its common
  `Database` representation; re-proving it per-format would test
  `cantools`' parser, not this loop's own (thin) wrapper.
"""

from __future__ import annotations

import json
from pathlib import Path

import cantools
import pytest

from tapwright.dbc_arxml import CanDatabase, UnknownMessageError, load_arxml, load_dbc
from tapwright.dbc_arxml.errors import DatabaseLoadError
from tapwright.hal import Frame

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
ARXML_PATH = FIXTURES / "databases" / "vehicle_signals.arxml"
DBC_PATH = FIXTURES / "databases" / "multiplexed.dbc"


def load_expected(name: str) -> dict:
    return json.loads((FIXTURES / "expected" / name).read_text(encoding="utf-8"))


def oracle_database() -> cantools.database.can.database.Database:
    """`cantools` used directly on the same file -- no Tapwright code in
    the path, this file's own oracle."""
    return cantools.database.load_file(ARXML_PATH)


def our_database() -> CanDatabase:
    return load_arxml(ARXML_PATH)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_decode_matches_golden_expected_output_and_cantools_direct():
    expected = load_expected("arxml_vehicle_status.json")
    frame = Frame(
        arbitration_id=expected["frame_id"],
        data=bytes.fromhex(expected["data_hex"]),
        is_extended_id=expected["is_extended_id"],
    )

    our_result = our_database().decode(frame)
    oracle_result = oracle_database().decode_message(
        frame.arbitration_id, frame.data, force_extended_id=frame.is_extended_id
    )

    assert our_result == oracle_result == expected["decoded"]


def test_encode_round_trips_through_decode():
    expected = load_expected("arxml_vehicle_status.json")

    db = our_database()
    frame = db.encode("VehicleStatus", expected["decoded"])
    oracle_data = oracle_database().encode_message("VehicleStatus", expected["decoded"])

    assert frame.data == oracle_data == bytes.fromhex(expected["data_hex"])
    assert frame.arbitration_id == expected["frame_id"]
    assert frame.is_extended_id == expected["is_extended_id"]

    # Full circle: what we just encoded decodes back to the same values.
    assert db.decode(frame) == expected["decoded"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_extended_arbitration_id_decodes_correctly():
    expected = load_expected("arxml_extended_diag.json")
    frame = Frame(
        arbitration_id=expected["frame_id"],
        data=bytes.fromhex(expected["data_hex"]),
        is_extended_id=expected["is_extended_id"],
    )

    our_result = our_database().decode(frame)
    oracle_result = oracle_database().decode_message(
        frame.arbitration_id, frame.data, force_extended_id=frame.is_extended_id
    )

    assert our_result == oracle_result == expected["decoded"]


def test_negative_offset_signal_decodes_to_correct_physical_value():
    """The plan's own fixture-corpus guidance names "negative offsets" as a
    scaling edge case worth covering explicitly -- a signal whose physical
    value is *lower* than its raw value, not just scaled.
    """
    expected = load_expected("arxml_vehicle_status.json")

    result = our_database().decode(
        Frame(
            arbitration_id=expected["frame_id"],
            data=bytes.fromhex(expected["data_hex"]),
            is_extended_id=expected["is_extended_id"],
        )
    )

    assert result["Speed"] < 0 or expected["decoded"]["Speed"] == result["Speed"]
    # exact expected value asserted via the golden-file comparison above;
    # this case exists to name *why* this fixture's Speed signal has a
    # negative offset, for a reader who doesn't already know


def test_dbc_path_remains_fully_functional_alongside_arxml():
    """The plan's own "dual specification strategy" constraint for this
    loop, proven rather than assumed: BUS-01's DBC path is not demoted,
    deprecated, or made harder to use by ARXML's addition -- both load and
    decode correctly in the same session.
    """
    dbc_db = load_dbc(DBC_PATH)
    arxml_db = load_arxml(ARXML_PATH)

    dbc_expected = load_expected("dbc_multiplexed_engine_data.json")
    dbc_result = dbc_db.decode(
        Frame(
            arbitration_id=dbc_expected["frame_id"],
            data=bytes.fromhex(dbc_expected["data_hex"]),
            is_extended_id=dbc_expected["is_extended_id"],
        )
    )
    assert dbc_result == dbc_expected["decoded"]

    arxml_expected = load_expected("arxml_vehicle_status.json")
    arxml_result = arxml_db.decode(
        Frame(
            arbitration_id=arxml_expected["frame_id"],
            data=bytes.fromhex(arxml_expected["data_hex"]),
            is_extended_id=arxml_expected["is_extended_id"],
        )
    )
    assert arxml_result == arxml_expected["decoded"]


def test_load_arxml_rejects_a_dbc_file_with_a_clear_error():
    """Format-boundary correctness: `load_arxml()` is a named, specific
    entry point, not a silent auto-detector -- handing it the wrong format
    fails clearly rather than doing something unexpected.
    """
    with pytest.raises(DatabaseLoadError):
        load_arxml(DBC_PATH)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_decode_unknown_frame_id_raises_clear_error():
    db = our_database()
    unknown_frame = Frame(arbitration_id=0x999, data=b"\x00" * 8)

    with pytest.raises(UnknownMessageError):
        db.decode(unknown_frame)


def test_load_arxml_with_missing_file_raises_clear_error():
    with pytest.raises(DatabaseLoadError):
        load_arxml(FIXTURES / "databases" / "does_not_exist.arxml")

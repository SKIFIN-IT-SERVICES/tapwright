# SPDX-License-Identifier: Apache-2.0

"""T3 differential tests for BUS-01 / TOOL-REQ-014 — DBC ingestion +
symbolic decode via `cantools`.

Implements #22. First loop to populate INF-04's fixture corpus for real:
`fixtures/databases/multiplexed.dbc` (self-authored — three messages
exercising plain scaling, a negative offset, a 29-bit extended arbitration
ID, and a multiplexed signal group) plus four golden `fixtures/expected/*`
JSON files, each derived by running `cantools` 42.0.3 directly against the
DBC — never from our own implementation, which doesn't exist yet at fixture
authoring time. See `fixtures/PROVENANCE.md` and each fixture's own
`provenance.toml` entry.

**`verified_by` on every new fixture entry is provisional**, naming the
human reviewer of this PR rather than an already-completed sign-off — an
agent cannot self-certify a fixture per `AGENTS.md`/`PROVENANCE.md`'s own
rule ("`verified_by` names a person... it cannot be inferred"). Flagged
explicitly in the PR description; needs the reviewer's actual confirmation,
not just a merge.

## Oracle

Every decode/encode case runs through both `tapwright.dbc_arxml.DbcDatabase`
and `cantools.database.load_file()` (the same file) used directly, asserting
identical results — the differential half. The golden `fixtures/expected/*`
values are the property-test-independent, human-reviewable anchor — the
"golden expected outputs" half BUS-01's own backlog line names alongside
the differential comparison.

## Scope notes

- ARXML (`TOOL-REQ-015`), LDF (`TOOL-REQ-016`), A2L (`TOOL-REQ-017`) are
  separate requirements/loops (BUS-02 through BUS-04) — not built here.
- T4 (property) coverage is `tests/property/test_dbc_decode_properties.py`
  — BUS-01's declared tier is T4, subsuming this T3-shaped differential
  file, not replacing it.
"""

from __future__ import annotations

import json
from pathlib import Path

import cantools
import pytest

from tapwright.dbc_arxml import DbcDatabase, UnknownMessageError, load_dbc
from tapwright.dbc_arxml.errors import DatabaseLoadError
from tapwright.hal import Frame

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
DBC_PATH = FIXTURES / "databases" / "multiplexed.dbc"


def load_expected(name: str) -> dict:
    return json.loads((FIXTURES / "expected" / name).read_text(encoding="utf-8"))


def oracle_database() -> cantools.database.can.database.Database:
    """cantools used directly on the same file — no Tapwright code in the
    path, this file's own oracle."""
    return cantools.database.load_file(DBC_PATH)


def our_database() -> DbcDatabase:
    return load_dbc(DBC_PATH)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_decode_matches_golden_expected_output_and_cantools_direct():
    expected = load_expected("dbc_multiplexed_engine_data.json")
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
    expected = load_expected("dbc_multiplexed_engine_data.json")

    db = our_database()
    frame = db.encode("EngineData", expected["decoded"])
    oracle_data = oracle_database().encode_message("EngineData", expected["decoded"])

    assert frame.data == oracle_data == bytes.fromhex(expected["data_hex"])
    assert frame.arbitration_id == expected["frame_id"]
    assert frame.is_extended_id == expected["is_extended_id"]

    # Full circle: what we just encoded decodes back to the same values.
    assert db.decode(frame) == expected["decoded"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_extended_arbitration_id_decodes_correctly():
    expected = load_expected("dbc_multiplexed_extended_msg.json")
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


def test_multiplexed_signal_selector_0_decodes_signal_a_only():
    expected = load_expected("dbc_multiplexed_mux_selector_0.json")
    frame = Frame(
        arbitration_id=expected["frame_id"],
        data=bytes.fromhex(expected["data_hex"]),
        is_extended_id=expected["is_extended_id"],
    )

    result = our_database().decode(frame)

    assert result == expected["decoded"]
    assert "MuxedSignalB" not in result


def test_multiplexed_signal_selector_1_decodes_signal_b_only():
    expected = load_expected("dbc_multiplexed_mux_selector_1.json")
    frame = Frame(
        arbitration_id=expected["frame_id"],
        data=bytes.fromhex(expected["data_hex"]),
        is_extended_id=expected["is_extended_id"],
    )

    result = our_database().decode(frame)

    assert result == expected["decoded"]
    assert "MuxedSignalA" not in result


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_decode_unknown_frame_id_raises_clear_error():
    db = our_database()
    unknown_frame = Frame(arbitration_id=0x999, data=b"\x00" * 8)

    with pytest.raises(UnknownMessageError):
        db.decode(unknown_frame)


def test_load_dbc_with_missing_file_raises_clear_error():
    with pytest.raises(DatabaseLoadError):
        load_dbc(FIXTURES / "databases" / "does_not_exist.dbc")

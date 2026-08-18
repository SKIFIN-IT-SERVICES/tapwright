# SPDX-License-Identifier: Apache-2.0

"""Test plan for BUS-01 / TOOL-REQ-014 — DBC ingestion + symbolic decode via
`cantools`.

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

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
DBC_PATH = FIXTURES / "databases" / "multiplexed.dbc"

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #22)")


def load_expected(name: str) -> dict:
    return json.loads((FIXTURES / "expected" / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_decode_matches_golden_expected_output_and_cantools_direct():
    """EngineData: plain scaling + a negative offset, matched against both
    the golden fixture and cantools called directly on the same DBC."""


@SKIP
def test_encode_round_trips_through_decode():
    """Encoding EngineData's decoded values back into bytes reproduces the
    original frame — the "encode" half of TOOL-REQ-014's decode/encode
    pairing, matched against cantools direct."""


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_extended_arbitration_id_decodes_correctly():
    """ExtendedMsg: a 29-bit extended ID, matched against the golden
    fixture and cantools direct (force_extended_id=True)."""


@SKIP
def test_multiplexed_signal_selector_0_decodes_signal_a_only():
    """MuxMessage with MuxSelector=0: only MuxedSignalA appears in the
    decode, matching cantools' own multiplex dispatch — not something we
    add on top of it."""


@SKIP
def test_multiplexed_signal_selector_1_decodes_signal_b_only():
    """Same raw payload as selector=0 except the selector byte, decoding to
    a completely different signal (different name, different scale) —
    proves the multiplex dispatch is followed, not positionally assumed.
    """


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_decode_unknown_frame_id_raises_clear_error():
    """Decoding a frame ID the DBC doesn't define raises a clear,
    dbc_arxml-specific error — not a bare KeyError surfaced from deep
    inside cantools."""


@SKIP
def test_load_dbc_with_missing_file_raises_clear_error():
    """Loading a nonexistent DBC path raises a clear, typed error rather
    than a bare FileNotFoundError with no context about which loop/module
    it came from — matching hal.errors'/diag.errors' established
    convention for this project."""

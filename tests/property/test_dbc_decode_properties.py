# SPDX-License-Identifier: Apache-2.0

"""T4 property test for BUS-01 — DBC's declared tier (`LOOPS.md`) is T4,
which subsumes the T3-shaped differential file
(`tests/differential/test_dbc_decode.py`), not replaces it.

One property: for arbitrary values within each signal's declared valid
range, `decode(encode(x)) == x`. `hypothesis` generates signal values
directly (not raw bytes) — the round-trip has to survive scaling,
byte-order packing, and (for EngineTemp) a negative offset, which a small
hand-picked example set is exactly the kind of thing likely to miss at a
boundary.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from tapwright.dbc_arxml import load_dbc

DBC_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "databases" / "multiplexed.dbc"

# EngineSpeed: 16-bit unsigned raw, scale 0.25, offset 0 -> 0..16383.75 rpm
# in steps of 0.25. EngineTemp: 8-bit unsigned raw, scale 1, offset -40 ->
# -40..215 degC, integer steps.
ENGINE_SPEED_VALUES = st.integers(min_value=0, max_value=65535).map(lambda raw: raw * 0.25)
ENGINE_TEMP_VALUES = st.integers(min_value=-40, max_value=215)


@settings(deadline=None)
@given(engine_speed=ENGINE_SPEED_VALUES, engine_temp=ENGINE_TEMP_VALUES)
def test_engine_data_round_trips_for_arbitrary_in_range_values(
    engine_speed: float, engine_temp: int
) -> None:
    """EngineSpeed (0..16383.75 rpm, step 0.25) and EngineTemp (-40..215
    degC) round-trip through encode() then decode() for hypothesis-
    generated values across their full declared ranges.
    """
    db = load_dbc(DBC_PATH)
    signals = {"EngineSpeed": engine_speed, "EngineTemp": engine_temp}

    frame = db.encode("EngineData", signals)
    decoded = db.decode(frame)

    assert decoded == signals

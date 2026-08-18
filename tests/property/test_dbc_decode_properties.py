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

import pytest

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #22)")


@SKIP
def test_engine_data_round_trips_for_arbitrary_in_range_values():
    """EngineSpeed (0..16383.75 rpm, step 0.25) and EngineTemp (-40..215
    degC) round-trip through encode() then decode() for hypothesis-
    generated values across their full declared ranges.
    """

# SPDX-License-Identifier: Apache-2.0

"""T4 property test for DIAG-02 — DIAG-02's declared tier (`LOOPS.md`) is T4,
which subsumes the T3 differential file
(`tests/differential/test_uds_client.py`), not replaces it.

One property, chosen to stress exactly the plumbing DIAG-02 adds: a DID
value written through `open_uds_client()`'s client, of varying length
(crossing the ISO-TP single/multi-frame boundary many times over a run),
reads back byte-identical. `hypothesis` generates the lengths and content;
a fixed seed corpus isn't enough to have caught the `is_extended_id` bug
DIAG-01 (#11) shipped with, and this tier exists precisely to widen the net
beyond what a human enumerates by hand.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #13)")


@SKIP
@settings(deadline=None)
@given(value=st.binary(min_size=1, max_size=60))
def test_write_then_read_did_round_trips_for_arbitrary_values(vcan_channel, value):
    """Any byte value, of any length within a generous bound, written then
    read back through our client, round-trips exactly — across the
    single-frame/multi-frame boundary many times over a hypothesis run.
    """

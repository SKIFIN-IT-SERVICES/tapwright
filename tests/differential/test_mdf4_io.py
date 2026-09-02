# SPDX-License-Identifier: Apache-2.0

"""T3/T4 test plan for BUS-06 — MDF4 read/write via `asammdf`
(`TOOL-REQ-021`).

Implements #51. Oracle is the plan's own line: "Core installs and passes
without the extra; extra round-trips MDF4" plus `TOOL-REQ-021`'s own
acceptance criterion: "Produces a valid MDF4 file (via `asammdf`) that
opens in a third-party MDF4-compliant tool." `asammdf` itself, used
directly (not through `tapwright`'s own wrapper), stands in for that
third-party tool — it's the reference implementation of the format, not
code this project wrote.

Per `AGENTS.md`'s reuse rule and the BUS-05 precedent (BLF/ASC wrapping
`can.io.BLFWriter`/`BLFReader`/`ASCWriter`/`ASCReader`), this wraps
`python-can`'s own `MF4Writer`/`MF4Reader` (`can.io.mf4`) — which already
implements CAN-frame-level MDF4 logging on top of `asammdf` — rather than
hand-rolling `asammdf.Signal`/`MDF.append()` calls directly. `python-can`
is already a required dependency; only `asammdf` itself is the new,
LGPL-isolated optional extra (`tapwright[mdf4]`, `FW-REQ-015`).

## `pytest.importorskip` — proving the "no extra" half of the oracle

Every case in this file skips cleanly via `pytest.importorskip("asammdf")`
at module level. This *is* how "the core installs and passes its full
suite without the extra" gets proven mechanically: a CI job that installs
`tapwright` without `[mdf4]` and runs the full suite must show these cases
skipped, not failed or errored. A second CI job installs `tapwright[mdf4]`
and must show them passing for real.

## A real finding from API research (kept here, not silently worked around)

`python-can`'s own `can.io.mf4.MF4Writer`/`MF4Reader` already raise a
clear `NotImplementedError` ("install python-can with the optional
dependency [mf4]") when `asammdf` isn't importable — better than the
BUS-05 `ASCReader` silent-failure gap. `test_missing_asammdf_...` monkeypatches
`can.io.mf4`'s own module-level `asammdf` binding to `None` to exercise
this without needing a second real environment, and asserts `tapwright`
translates it to a `TraceError` naming the extra, rather than leaking
`python-can`'s own message verbatim (a caller catching `tapwright.trace`
errors shouldn't need to know `python-can`'s internals to understand what
to install).

Round-tripped timestamps lose float precision (`0.1` -> observed
`0.09999990463256836` in manual research against `asammdf` 8.8.26) —
`pytest.approx` is used for timestamp comparisons rather than exact
equality, matching this format's real behavior rather than the byte-exact
oracle BUS-05 used for BLF.
"""

from __future__ import annotations

import can
import pytest

from tapwright.hal import Frame
from tapwright.trace.errors import TraceError, TraceLoadError

pytest.importorskip("asammdf")

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #51)")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_round_trips_frames_through_write_then_read(tmp_path):
    from tapwright.trace import read_mdf4, write_mdf4

    frames = [
        Frame(arbitration_id=0x100, data=b"\x01\x02", timestamp=0.0),
        Frame(arbitration_id=0x101, data=b"\xaa\xbb\xcc", timestamp=0.1),
    ]
    path = tmp_path / "trace.mf4"
    write_mdf4(frames, path)
    result = read_mdf4(path)

    assert len(result) == len(frames)
    for expected, actual in zip(frames, result):
        assert actual.arbitration_id == expected.arbitration_id
        assert actual.data == expected.data
        assert actual.timestamp == pytest.approx(expected.timestamp, abs=1e-4)


@SKIP
def test_written_file_opens_directly_with_asammdf(tmp_path):
    """The literal acceptance criterion: a third-party MDF4-compliant tool
    (here, `asammdf` used directly, not through `tapwright`) can open what
    `write_mdf4()` produces.
    """
    from asammdf import MDF

    from tapwright.trace import write_mdf4

    frames = [Frame(arbitration_id=0x200, data=b"\x01\x02\x03\x04")]
    path = tmp_path / "direct.mf4"
    write_mdf4(frames, path)

    with MDF(path) as mdf:
        assert mdf.version.startswith("4.")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_writing_zero_frames_round_trips_to_an_empty_list(tmp_path):
    from tapwright.trace import read_mdf4, write_mdf4

    path = tmp_path / "empty.mf4"
    write_mdf4([], path)
    assert read_mdf4(path) == []


@SKIP
def test_extended_id_frame_is_preserved(tmp_path):
    from tapwright.trace import read_mdf4, write_mdf4

    frames = [Frame(arbitration_id=0x1ABCDEF, data=b"\x01", is_extended_id=True)]
    path = tmp_path / "extended.mf4"
    write_mdf4(frames, path)
    result = read_mdf4(path)

    assert result[0].arbitration_id == 0x1ABCDEF
    assert result[0].is_extended_id is True


@SKIP
def test_fd_frame_is_preserved(tmp_path):
    from tapwright.trace import read_mdf4, write_mdf4

    frames = [Frame(arbitration_id=0x300, data=bytes(range(12)), is_fd=True)]
    path = tmp_path / "fd.mf4"
    write_mdf4(frames, path)
    result = read_mdf4(path)

    assert result[0].data == bytes(range(12))
    assert result[0].is_fd is True


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_reading_a_missing_file_raises_trace_load_error(tmp_path):
    from tapwright.trace import read_mdf4

    with pytest.raises(TraceLoadError):
        read_mdf4(tmp_path / "does_not_exist.mf4")


@SKIP
def test_reading_a_garbage_file_raises_trace_load_error(tmp_path):
    from tapwright.trace import read_mdf4

    path = tmp_path / "garbage.mf4"
    path.write_bytes(b"not an mdf file at all, just garbage bytes")

    with pytest.raises(TraceLoadError):
        read_mdf4(path)


@SKIP
def test_missing_asammdf_extra_raises_a_clear_tapwright_error(tmp_path, monkeypatch):
    """Simulates `tapwright` installed *without* `[mdf4]`: `can.io.mf4`'s
    own module-level `asammdf` binding is `None` in that environment. The
    wrapper must translate `python-can`'s own `NotImplementedError` into a
    `tapwright.trace` error naming the extra to install, not leak it
    verbatim.
    """
    from tapwright.trace import write_mdf4

    monkeypatch.setattr(can.io.mf4, "asammdf", None)

    with pytest.raises(TraceError, match="tapwright\\[mdf4\\]"):
        write_mdf4([Frame(arbitration_id=0x1, data=b"\x01")], tmp_path / "unused.mf4")

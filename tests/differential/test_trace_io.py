# SPDX-License-Identifier: Apache-2.0

"""T3 (subsumed under BUS-05's declared T4) differential test plan for
BUS-05 — BLF + ASC trace read/write via `python-can` (`TOOL-REQ-019`,
`TOOL-REQ-020`).

Implements #45. Oracle is the plan's own line: "Round-trip byte-fidelity
on recorded fixtures." Per `AGENTS.md`'s reuse rule, `python-can`
(already a required dependency) already implements both formats natively
(`can.io.BLFReader`/`BLFWriter`/`ASCReader`/`ASCWriter`) — every case here
writes through `tapwright.trace`'s own wrapper and reads back through
`python-can`'s reader classes directly (and vice versa), so a mismatch
between our wrapper and the format `python-can` itself produces/consumes
would show up immediately, the same differential-oracle shape BUS-01/02
established for `cantools`.

## Scope note (posted in full to #45; kept here as a pointer)

**Real Vector CANoe interop is not verified.** No CANoe-exported BLF/ASC
file is available in this environment to test against. Fixtures are
self-authored by writing known frames through `python-can`'s own
writer classes (which implement the published Vector formats) and reading
them back — proving *our* wrapper round-trips correctly through
`python-can`'s implementation, not that a real CANoe-produced file opens
correctly here or vice versa. Flagged as a known gap rather than silently
claimed as proven; closing it needs an actual CANoe export, which isn't
available to an agent.

## `hal.Frame` gains a `timestamp` field

Found while designing this plan: `Frame` had no timing field at all, but
BLF/ASC are fundamentally timestamped-trace formats — a trace without
per-frame timing isn't a meaningful trace. Added `timestamp: float = 0.0`
(a trailing field with a default, so every existing `Frame(...)` call site
is unaffected). Deliberately scoped narrowly: `hal.Bus.send()`/`recv()`
are *not* touched by this loop — populating live-capture timestamps there
is a separate concern (HAL-01/02's own already-closed loop) from
trace-file round-tripping, flagged as a natural follow-up rather than
addressed here.

## Format properties discovered while researching this plan (both formats)

- **Timestamps round-trip as relative deltas from the first message, not
  absolute values** — confirmed directly: writing messages timestamped
  1.5s and 2.0s reads back as 0.0s and 0.5s. Tests compare relative
  deltas, not absolute timestamps.
- **ASC embeds a wall-clock "date" header line at write time** — the raw
  file is not byte-identical across writes on different days (same class
  of non-determinism RUN-03 already found in `pytest-html`'s own
  template). Tests compare decoded frame content, not raw file bytes.
- Both formats round-trip CAN-FD frames correctly (`is_fd=True`),
  confirmed directly.
"""

from __future__ import annotations

import can
import pytest

from tapwright.hal import Frame
from tapwright.trace import TraceLoadError, read_asc, read_blf, write_asc, write_blf

FRAMES = [
    Frame(arbitration_id=0x123, data=b"\x01\x02\x03", is_extended_id=False),
    Frame(arbitration_id=0x1ABCDEF0, data=b"\xff" * 8, is_extended_id=True),
]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_blf_round_trips_through_our_own_writer_and_reader(tmp_path):
    path = tmp_path / "trace.blf"
    write_blf(FRAMES, path)
    result = read_blf(path)

    assert [(f.arbitration_id, f.data, f.is_extended_id) for f in result] == [
        (f.arbitration_id, f.data, f.is_extended_id) for f in FRAMES
    ]


def test_asc_round_trips_through_our_own_writer_and_reader(tmp_path):
    path = tmp_path / "trace.asc"
    write_asc(FRAMES, path)
    result = read_asc(path)

    assert [(f.arbitration_id, f.data, f.is_extended_id) for f in result] == [
        (f.arbitration_id, f.data, f.is_extended_id) for f in FRAMES
    ]


def test_blf_written_by_us_reads_correctly_via_python_can_directly(tmp_path):
    """The differential half: what we write, `python-can`'s own reader
    (not ours) also reads correctly -- proves our writer produces a
    genuinely standard BLF file, not just one our own reader happens to
    tolerate.
    """
    path = tmp_path / "trace.blf"
    write_blf(FRAMES, path)

    with can.io.BLFReader(path) as reader:
        oracle_result = list(reader)

    assert [(m.arbitration_id, bytes(m.data), m.is_extended_id) for m in oracle_result] == [
        (f.arbitration_id, f.data, f.is_extended_id) for f in FRAMES
    ]


def test_asc_written_by_python_can_directly_reads_correctly_via_us(tmp_path):
    """The other differential half: a file `python-can` itself produced
    (not ours) reads correctly through our own reader.
    """
    path = tmp_path / "trace.asc"
    with can.io.ASCWriter(path) as writer:
        for frame in FRAMES:
            writer.on_message_received(
                can.Message(
                    arbitration_id=frame.arbitration_id,
                    data=frame.data,
                    is_extended_id=frame.is_extended_id,
                )
            )

    result = read_asc(path)
    assert [(f.arbitration_id, f.data, f.is_extended_id) for f in result] == [
        (f.arbitration_id, f.data, f.is_extended_id) for f in FRAMES
    ]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("write_fn", "read_fn", "ext"),
    [(write_blf, read_blf, "blf"), (write_asc, read_asc, "asc")],
)
def test_can_fd_frame_round_trips(tmp_path, write_fn, read_fn, ext):
    path = tmp_path / f"trace.{ext}"
    fd_frame = Frame(arbitration_id=0x321, data=b"\xaa" * 20, is_extended_id=False, is_fd=True)

    write_fn([fd_frame], path)
    (result,) = read_fn(path)

    assert result.is_fd is True
    assert result.data == fd_frame.data


@pytest.mark.parametrize(
    ("write_fn", "read_fn", "ext"),
    [(write_blf, read_blf, "blf"), (write_asc, read_asc, "asc")],
)
def test_empty_trace_round_trips_to_zero_frames_not_a_crash(tmp_path, write_fn, read_fn, ext):
    path = tmp_path / f"trace.{ext}"
    write_fn([], path)
    assert read_fn(path) == []


@pytest.mark.parametrize(
    ("write_fn", "read_fn", "ext"),
    [(write_blf, read_blf, "blf"), (write_asc, read_asc, "asc")],
)
def test_relative_timing_between_frames_is_preserved(tmp_path, write_fn, read_fn, ext):
    """Documents and locks in the relative-timestamp behavior found while
    researching this plan -- absolute timestamps are not preserved by
    either format, but the *delta* between frames must be.
    """
    path = tmp_path / f"trace.{ext}"
    early = Frame(arbitration_id=0x1, data=b"\x01", timestamp=1.5)
    late = Frame(arbitration_id=0x2, data=b"\x02", timestamp=2.0)

    write_fn([early, late], path)
    first, second = read_fn(path)

    assert second.timestamp - first.timestamp == pytest.approx(0.5, abs=1e-3)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("read_fn", [read_blf, read_asc])
def test_reading_a_missing_file_raises_clear_error(tmp_path, read_fn):
    with pytest.raises(TraceLoadError):
        read_fn(tmp_path / "does_not_exist")


@pytest.mark.parametrize("read_fn,ext", [(read_blf, "blf"), (read_asc, "asc")])
def test_reading_a_corrupted_file_raises_clear_error_not_a_crash(tmp_path, read_fn, ext):
    path = tmp_path / f"garbage.{ext}"
    path.write_bytes(b"this is not a valid trace file at all")

    with pytest.raises(TraceLoadError):
        read_fn(path)

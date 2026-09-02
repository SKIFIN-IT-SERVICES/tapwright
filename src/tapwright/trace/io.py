# SPDX-License-Identifier: Apache-2.0

"""BLF + ASC + MDF4 trace read/write via `python-can` (BUS-05
`TOOL-REQ-019`/`TOOL-REQ-020`; BUS-06 `TOOL-REQ-021`).

Per `AGENTS.md`'s reuse rule, this wraps `can.io.BLFReader`/`BLFWriter`/
`ASCReader`/`ASCWriter`/`MF4Reader`/`MF4Writer` (`python-can` is already a
required dependency) rather than reimplementing any of these formats. The
only thing this module adds is bridging to/from `tapwright.hal.Frame`.

`ASCReader.__iter__()` silently returns zero messages for a file that
isn't a valid ASC trace at all (confirmed directly: feeding it arbitrary
non-ASC text raises nothing and just yields an empty iterator) — exactly
the "silent failure" this project's own philosophy rejects (see
`hal.errors.CapabilityError`'s own docstring, `TOOL-REQ-009`). `read_asc()`
checks for the header line `ASCWriter` always writes before handing off to
`python-can`, so a non-ASC file raises `TraceLoadError` instead of quietly
looking like an empty trace.

MDF4 needs `asammdf` (LGPL-3.0), which `python-can`'s own `can.io.mf4`
module already imports only under a guarded `try`/`except ImportError` —
ships as tapwright's own optional `mdf4` extra (`FW-REQ-015`, `FW-REQ-019`;
dependency-only, never vendored, matching the `python-can` precedent from
HAL-08). `write_mdf4()`/`read_mdf4()` translate `python-can`'s own
`NotImplementedError` (raised when `asammdf` isn't installed) into
`TraceError`, so a caller doesn't need to know `python-can`'s internals to
learn what to install.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from pathlib import Path

import can

from tapwright.hal import Frame

from .errors import TraceError, TraceLoadError

_MDF_EXCEPTIONS: tuple[type[BaseException], ...]
try:
    from asammdf.blocks.utils import MdfException  # type: ignore[import-not-found]

    _MDF_EXCEPTIONS = (MdfException,)
except ImportError:  # the mdf4 extra isn't installed; nothing to catch below
    _MDF_EXCEPTIONS = ()


def _frame_to_message(frame: Frame) -> can.Message:
    return can.Message(
        arbitration_id=frame.arbitration_id,
        data=frame.data,
        is_extended_id=frame.is_extended_id,
        is_fd=frame.is_fd,
        timestamp=frame.timestamp,
    )


def _message_to_frame(message: can.Message) -> Frame:
    return Frame(
        arbitration_id=message.arbitration_id,
        data=bytes(message.data),
        is_extended_id=message.is_extended_id,
        is_fd=message.is_fd,
        timestamp=message.timestamp,
    )


def write_blf(frames: Iterable[Frame], path: str | Path) -> None:
    """Write `frames` to a BLF trace file."""
    with can.io.BLFWriter(path) as writer:
        for frame in frames:
            writer.on_message_received(_frame_to_message(frame))


def read_blf(path: str | Path) -> list[Frame]:
    """Read every frame from a BLF trace file, in recorded order."""
    try:
        with can.io.BLFReader(path) as reader:
            return [_message_to_frame(message) for message in reader]
    except (OSError, can.CanError, struct.error) as exc:
        raise TraceLoadError(f"could not read BLF file {path!r}: {exc}") from exc


def write_asc(frames: Iterable[Frame], path: str | Path) -> None:
    """Write `frames` to an ASC trace file."""
    with can.io.ASCWriter(path) as writer:
        for frame in frames:
            writer.on_message_received(_frame_to_message(frame))


def read_asc(path: str | Path) -> list[Frame]:
    """Read every frame from an ASC trace file, in recorded order."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            first_line = fh.readline()
    except OSError as exc:
        raise TraceLoadError(f"could not read ASC file {path!r}: {exc}") from exc

    if not first_line.startswith("date "):
        raise TraceLoadError(
            f"{path!r} does not look like an ASC trace (expected a 'date' header line)"
        )

    try:
        with can.io.ASCReader(path) as reader:
            return [_message_to_frame(message) for message in reader]
    except (OSError, can.CanError) as exc:
        raise TraceLoadError(f"could not read ASC file {path!r}: {exc}") from exc


def write_mdf4(frames: Iterable[Frame], path: str | Path) -> None:
    """Write `frames` to an MDF4 trace file. Requires the `mdf4` optional
    extra (`pip install tapwright[mdf4]`) — raises `TraceError` naming it
    if `asammdf` isn't installed.
    """
    try:
        with can.io.MF4Writer(path) as writer:
            for frame in frames:
                writer.on_message_received(_frame_to_message(frame))
    except NotImplementedError as exc:
        raise TraceError(
            "MDF4 support requires the 'mdf4' optional extra: pip install tapwright[mdf4]"
        ) from exc


def read_mdf4(path: str | Path) -> list[Frame]:
    """Read every frame from an MDF4 trace file, in recorded order.
    Requires the `mdf4` optional extra; see `write_mdf4()`.
    """
    try:
        with can.io.MF4Reader(path) as reader:
            return [_message_to_frame(message) for message in reader]
    except NotImplementedError as exc:
        raise TraceError(
            "MDF4 support requires the 'mdf4' optional extra: pip install tapwright[mdf4]"
        ) from exc
    except (OSError, can.CanError, *_MDF_EXCEPTIONS) as exc:  # type: ignore[misc]
        raise TraceLoadError(f"could not read MDF4 file {path!r}: {exc}") from exc

# SPDX-License-Identifier: Apache-2.0

"""DBC ingestion + symbolic decode via `cantools` (BUS-01, `TOOL-REQ-014`).

Per `AGENTS.md`'s reuse rule (`cantools`: MIT — "reuse; contribute upstream
fixes... rather than forking"), this wraps `cantools.database.load_file()`'s
`Database` rather than reimplementing DBC parsing. The only thing this
module adds is bridging decode/encode to `tapwright.hal.Frame`, so a caller
never has to hand-assemble the frame-id/data-bytes/extended-id triple
`cantools`'s own API expects separately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cantools
import cantools.database

from tapwright.hal import Frame

from .errors import DatabaseLoadError, UnknownMessageError


class DbcDatabase:
    """A loaded DBC database, decoding/encoding against `hal.Frame` rather
    than cantools' own separate frame-id/data/extended-id arguments.

    Always constructed via `load_dbc()` — never directly — so a missing or
    invalid file raises `DatabaseLoadError` before any partially-loaded
    state exists.
    """

    def __init__(self, db: cantools.database.can.database.Database) -> None:
        self._db = db

    def decode(self, frame: Frame) -> dict[str, Any]:
        """Decode `frame` to named signals with physical values —
        `TOOL-REQ-014`'s acceptance criterion, verbatim.

        `force_extended_id` is passed through from `frame.is_extended_id`:
        cantools' own `decode_message()` raises a bare `KeyError` for an
        extended-ID message otherwise, since its internal frame-ID lookup
        table is keyed differently for standard vs. extended IDs — found
        while authoring this loop's own fixture, before this method existed
        (see `fixtures/expected/dbc_multiplexed_extended_msg.json`'s notes).
        """
        try:
            # decode_message()'s return type also covers container messages
            # (a Sequence of tuples), returned only when decode_containers=
            # True — we never pass that, so the dict branch is the only one
            # reachable here; mypy can't see that from the signature alone.
            return self._db.decode_message(  # type: ignore[return-value]
                frame.arbitration_id, frame.data, force_extended_id=frame.is_extended_id
            )
        except KeyError as exc:
            raise UnknownMessageError(
                f"no message with frame ID {frame.arbitration_id:#x} "
                f"(extended={frame.is_extended_id}) in this database"
            ) from exc

    def encode(self, message_name: str, signals: dict[str, Any]) -> Frame:
        """Encode `signals` into a `Frame` for the named message — resolving
        the arbitration ID and extended-ID flag from the database's own
        message definition, so the caller doesn't have to know them.
        """
        try:
            message = self._db.get_message_by_name(message_name)
        except KeyError as exc:
            raise UnknownMessageError(
                f"no message named {message_name!r} in this database"
            ) from exc

        data = self._db.encode_message(
            message_name, signals, force_extended_id=message.is_extended_frame
        )
        return Frame(
            arbitration_id=message.frame_id,
            data=data,
            is_extended_id=message.is_extended_frame,
        )


def load_dbc(path: str | Path) -> DbcDatabase:
    """Load a DBC file. Config/file-existence errors are caught and raised
    as `DatabaseLoadError` before any partially-loaded state exists, per
    the same "validate before touching a resource" discipline `hal.open_bus`
    already established.
    """
    try:
        db = cantools.database.load_file(path)
    except (FileNotFoundError, OSError) as exc:
        raise DatabaseLoadError(f"could not load DBC file {path!r}: {exc}") from exc

    if not isinstance(db, cantools.database.can.database.Database):
        raise DatabaseLoadError(
            f"{path!r} did not load as a CAN database (got {type(db).__name__})"
        )

    return DbcDatabase(db)

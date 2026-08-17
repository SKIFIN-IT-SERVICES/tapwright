# SPDX-License-Identifier: Apache-2.0

"""The backend-agnostic CAN/CAN-FD frame type nothing above hal/ should ever
need a backend-specific equivalent of."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Frame:
    """A single CAN or CAN-FD frame.

    arbitration_id: the CAN ID — 11-bit standard, or 29-bit when
        is_extended_id is set.
    data: the payload — up to 8 bytes for classic CAN, up to 64 for CAN-FD.
    is_extended_id: True for a 29-bit extended arbitration ID.
    is_fd: True for a CAN-FD frame.
    """

    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    is_fd: bool = False

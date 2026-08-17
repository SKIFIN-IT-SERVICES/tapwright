# SPDX-License-Identifier: Apache-2.0

"""Errors raised at the L0 hardware-abstraction boundary.

Every failure the hal/ public API raises is a HalError subclass — a caller
never has to catch a backend-internal exception type to handle a HAL
failure, per TOOL-REQ-009's "clear error, not a silent failure or crash."
"""

from __future__ import annotations


class HalError(Exception):
    """Base class for every error raised by tapwright.hal's public API."""


class BusConfigError(HalError):
    """Invalid open_bus() configuration — an unknown backend or a missing
    required field. Always raised before any OS-level resource is touched."""


class BusClosedError(HalError):
    """A bus handle was used after shutdown()."""


class CapabilityError(HalError):
    """An operation was attempted that the bus wasn't opened to support —
    e.g. sending a CAN-FD frame on a bus opened without fd=True
    (TOOL-REQ-009)."""

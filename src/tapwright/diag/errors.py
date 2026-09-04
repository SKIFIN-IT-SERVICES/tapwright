# SPDX-License-Identifier: Apache-2.0

"""Errors raised at the L2 diagnostics boundary.

Mirrors `hal.errors`' convention: every failure `diag/`'s public API raises
is a `DiagError` subclass, so a caller never has to catch a
transport/protocol-library-internal exception type to handle a diagnostics
failure.
"""

from __future__ import annotations


class DiagError(Exception):
    """Base class for every error raised by tapwright.diag's public API."""


class TransportClosedError(DiagError):
    """A transport handle was used after close()."""


class TransportConfigError(DiagError):
    """Invalid transport configuration — raised before any OS-level
    resource is touched, matching hal.errors.BusConfigError's contract."""


class TransportProtocolError(DiagError):
    """The underlying transport protocol detected a malformed exchange
    (e.g. an out-of-sequence ISO-TP Consecutive Frame) — surfaced here
    rather than silently producing a wrong or incomplete payload, per the
    "silently wrong decode" failure mode the verification ladder (plan §3)
    exists to catch."""


class OdxLoadError(DiagError):
    """An ODX/PDX file could not be read — missing, unreadable, or not a
    valid ODX/PDX file (DIAG-06)."""


class OdxUnknownEcuError(DiagError):
    """No ECU with the given name exists in this ODX/PDX database."""


class OdxUnknownServiceError(DiagError):
    """No diagnostic service in the named ECU matches the given raw
    request bytes."""

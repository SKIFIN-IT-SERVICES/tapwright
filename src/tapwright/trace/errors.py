# SPDX-License-Identifier: Apache-2.0

"""Errors raised at the L1 trace read/write boundary.

Mirrors `hal.errors`'/`dbc_arxml.errors`' convention: every failure this
module's public API raises is a `TraceError` subclass, so a caller never
has to catch a `python-can`-internal exception type to handle a trace
read/write failure.
"""

from __future__ import annotations


class TraceError(Exception):
    """Base class for every error raised by tapwright.trace's public API."""


class TraceLoadError(TraceError):
    """A trace file could not be read — missing, unreadable, or not a
    valid BLF/ASC file."""

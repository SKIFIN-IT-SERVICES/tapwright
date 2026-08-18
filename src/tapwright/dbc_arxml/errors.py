# SPDX-License-Identifier: Apache-2.0

"""Errors raised at the L1 DBC/ARXML decode boundary.

Mirrors `hal.errors`'/`diag.errors`' convention: every failure this module's
public API raises is a `DbcArxmlError` subclass, so a caller never has to
catch a `cantools`-internal exception type to handle a decode failure.
"""

from __future__ import annotations


class DbcArxmlError(Exception):
    """Base class for every error raised by tapwright.dbc_arxml's public API."""


class DatabaseLoadError(DbcArxmlError):
    """A database file could not be loaded — missing, unreadable, or not a
    valid DBC/ARXML file."""


class UnknownMessageError(DbcArxmlError):
    """A frame ID or message name has no corresponding message in the
    loaded database — raised here rather than surfacing a bare KeyError
    from deep inside cantools."""

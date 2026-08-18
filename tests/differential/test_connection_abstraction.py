# SPDX-License-Identifier: Apache-2.0

"""Test plan for DIAG-04 — the transport-agnostic connection abstraction.

Implements #17. Unlike every prior DIAG loop, this one's oracle isn't a
differential comparison against a reference library — it's the
parametrization itself succeeding: **one test body, run twice (CAN and
DoIP), with no per-transport branching in the body**. That literal
unmodified-reuse is `docs/architecture.md` §4's "construction-time choice,
invisible to the calling code" property, demonstrated rather than argued.

`connection_config` (below) is the fixture doing the actual work: it builds
either a `CanConnectionConfig` + a running `VirtualECU` on `vcan`, or a
`DoipConnectionConfig` + a running `DoIPVirtualECU` over TCP — and yields a
callable that opens a client from whichever config it built. Every test
function calls that callable and asserts on the client, never on which
transport is underneath.

The CAN parametrization is marked `requires_vcan` (per-parameter, via
`pytest.param(..., marks=...)`) so it skips cleanly off-Linux; the DoIP
parametrization always runs, same as every other DIAG-03 test.

## Scope note

`open_connection()` dispatches on the config object's *type*
(`CanConnectionConfig` vs. `DoipConnectionConfig`) — not a string literal
like `transport="can"` — so a caller can't typo a transport name into
something that silently falls through to a default. Named "SOVD-shaped" in
the plan and on #17: a future `SovdConnectionConfig` (DIAG-07) slots into
the same `open_connection()` dispatch without touching its signature or any
code that already calls it.

**L2 API-cleanliness note** (test-plan skill step 5): this loop is squarely
about `docs/architecture.md` §4's first bullet (transport-agnostic client
interface) — that's the whole point of the oracle here, not a side note.
The second bullet (request/response interception point) still doesn't
exist and isn't built by this loop either; `open_connection()`'s shape
doesn't preclude adding it later, same conclusion DIAG-01/02/03 each
reached for their own pieces.
"""

from __future__ import annotations

import pytest

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #17)")


@pytest.fixture(
    params=[
        pytest.param("can", marks=pytest.mark.requires_vcan),
        pytest.param("doip"),
    ]
)
def connection_config(request):
    """Yields a zero-argument callable: `open_client() -> udsoncan.Client`,
    built from whichever transport this parametrization instance is —
    every test below calls it without knowing or caring which.

    Implementation pending (issue #17) — every test that depends on this
    fixture is `@SKIP`-marked, so pytest's skip happens before fixture
    setup and this incomplete body is never actually invoked.
    """


# ---------------------------------------------------------------------------
# Happy path — the oracle itself: one body, both transports
# ---------------------------------------------------------------------------


@SKIP
def test_read_did_over_either_transport(connection_config):
    """RDBI succeeds identically whichever transport `connection_config`
    built — the literal "same test body, unmodified" proof."""


@SKIP
def test_write_then_read_did_over_either_transport(connection_config):
    """WDBI then RDBI round-trips identically over either transport."""


@SKIP
def test_change_session_over_either_transport(connection_config):
    """DiagnosticSessionControl succeeds identically over either transport,
    unlocking a session-gated DID afterward."""


# ---------------------------------------------------------------------------
# Error cases — the abstraction must not leak transport-specific exceptions
# ---------------------------------------------------------------------------


@SKIP
def test_read_unconfigured_did_raises_over_either_transport(connection_config):
    """An unconfigured DID raises the same udsoncan.NegativeResponseException
    with the same NRC over either transport — the error path is
    transport-agnostic too, not just the happy path."""


@SKIP
def test_connection_closed_raises_over_either_transport(connection_config):
    """Using a client after close() raises the same RuntimeError over
    either transport — DIAG-02's and DIAG-03's lifecycle contracts agree."""

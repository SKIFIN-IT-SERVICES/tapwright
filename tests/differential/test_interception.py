# SPDX-License-Identifier: Apache-2.0

"""Test plan for DIAG-05 — request/response interception hooks, working
across a process boundary.

Implements #25. The oracle (plan §2.1, DIAG-05's own backlog line, verbatim):
"A third-party wrapper can observe and modify a request/response without
forking, from a separate process." Every case below spawns a genuine OS
subprocess (`_interception_observer.py`, imports nothing from `tapwright`)
as the "third party" — not an in-process mock, not a thread. That subprocess
speaks only the plain newline-delimited-JSON protocol
`InterceptingConnection` publishes over a TCP socket.

## Design, decided while writing this plan (not yet built)

`tapwright.diag.interception.InterceptingConnection` wraps *any* existing
`BaseConnection` (transport-agnostic by construction, same property DIAG-04
established) and publishes every outbound request / inbound response to at
most one connected observer. With no observer attached — the default,
overwhelmingly common case — publishing is a single non-blocking `accept()`
call that returns immediately: **zero added latency**, which
`test_no_observer_attached_is_pure_passthrough` exists specifically to prove
isn't just claimed but measured. An observer that connects mid-session stays
connected across multiple messages (matching realistic fuzzer usage:
attach once, observe/mutate many messages) rather than one connection per
message.

## Scope notes

- Single observer at a time — multi-observer fan-out is a fast-follow, not
  required by this loop's oracle.
- **L2 API-cleanliness note** (test-plan skill step 5): this loop *is*
  `docs/architecture.md` §4's second bullet, the one every prior DIAG loop
  noted as "not built yet, but not precluded." It's transport-agnostic by
  construction (wraps whatever `BaseConnection` DIAG-04's `open_connection()`
  produced), so it doesn't reopen or special-case CAN vs. DoIP.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.requires_vcan

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #25)")

OBSERVER_SCRIPT = Path(__file__).resolve().parent / "_interception_observer.py"


def spawn_observer(port: int, *args: str) -> subprocess.Popen:
    """A real OS subprocess — the "separate process" the oracle requires."""
    return subprocess.Popen(
        [sys.executable, str(OBSERVER_SCRIPT), str(port), *args],
        stdout=subprocess.PIPE,
        text=True,
    )


def read_observer_messages(proc: subprocess.Popen, count: int) -> list[dict]:
    """Read `count` JSON lines from the observer's stdout. Relies on the
    observer script's own 5s socket timeout to bound how long a hung
    exchange can block this — implementation detail to firm up in
    tdd-develop, not decided further at test-plan stage.
    """
    assert proc.stdout is not None
    messages = []
    for _ in range(count):
        line = proc.stdout.readline()
        if not line:
            break
        messages.append(json.loads(line))
    return messages


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@SKIP
def test_observer_process_observes_request_and_response_without_modifying():
    """A subprocess observer with no replacement rules sees both the
    request and response payloads, byte-for-byte, and the UDS call still
    returns the real ECU's value — pure observation, no mutation.
    """


@SKIP
def test_observer_process_can_replace_a_response():
    """A subprocess observer configured to replace the response payload
    causes the client-facing UDS call to return the *substituted* value,
    not the real ECU's — proving mutation, not just observation.
    """


@SKIP
def test_observer_process_can_replace_a_request():
    """A subprocess observer configured to replace the outbound request
    payload causes the ECU to actually receive and respond to the
    *substituted* request — proven via a scenario with two differently-
    valued DIDs: the client asks for one, the observer rewrites the request
    to ask for the other, and the returned value is the other DID's.
    """


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@SKIP
def test_no_observer_attached_is_pure_passthrough():
    """The default, overwhelmingly common case: no subprocess spawned at
    all. The UDS call behaves identically to an unwrapped connection, and
    with negligible added latency — measured, not just asserted correct.
    """


@SKIP
def test_observer_disconnecting_mid_session_falls_back_to_passthrough():
    """An observer that exits after observing only the request (closing its
    socket before the response is published) doesn't break the response
    half of the same exchange — the interception point notices the closed
    connection and falls back to passthrough rather than erroring.
    """


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@SKIP
def test_unresponsive_observer_does_not_block_traffic_forever():
    """A subprocess observer that connects but never replies (`--silent`)
    must not hang the real UDS exchange indefinitely — a misbehaving
    external process must not become a denial-of-service on the diagnostic
    session. Bounded wait, then passthrough; the real ECU value still comes
    back, just after a capped delay.
    """


@SKIP
def test_malformed_observer_reply_is_ignored_not_crashing():
    """A subprocess observer that replies with invalid JSON (`--garbage`)
    doesn't crash the connection — falls back to unmodified passthrough for
    that message, same as an unresponsive one.
    """


@SKIP
def test_interception_wraps_a_doip_connection_identically():
    """InterceptingConnection wraps whatever BaseConnection DIAG-04's
    open_connection() produced — proven once here against a DoIP-backed
    client, not re-running the full observe/replace matrix a second time
    (DIAG-04 already established transport-agnosticism as a property of
    open_connection() itself; this only confirms interception doesn't
    special-case CAN).
    """

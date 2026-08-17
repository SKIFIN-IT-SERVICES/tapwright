# SPDX-License-Identifier: Apache-2.0

"""Scenario configuration for the virtual ECU (INF-05, TOOL-REQ-026).

A `Scenario` is the "scenario-configurable" half of INF-05's goal: everything
about what the virtual ECU does — its DIDs, DTCs, security levels, arbitration
IDs, and injected failures — is data passed in here, not hardcoded in the
protocol state machine. `ProtocolState` (see `protocol.py`) only ever reads a
`Scenario`; it never special-cases behaviour by branching on scenario content
outside what these fields already describe.

Security levels store a fixed `key` constant for test purposes. This is
mechanics only, never derivation — see C-10 / DIAG-08 / AGENTS.md §4. A real
ECU's key is normally computed from the seed via a manufacturer-specific
algorithm; ours is a value the scenario author chose in advance, exactly the
way a test fixture works everywhere else in this project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

FailureKind = Literal["nrc", "timeout", "truncated", "oversized"]


@dataclass(frozen=True)
class DIDConfig:
    """One Data Identifier's configured value and access rules."""

    value: bytes
    session_gate: int | None = None
    """If set, this DID is only readable/writable in the given session
    (e.g. 0x03 for extendedDiagnosticSession). None means available in any
    session."""
    read_only: bool = False


@dataclass(frozen=True)
class SecurityLevelConfig:
    """One SecurityAccess level's seed and the key that unlocks it.

    `key` is an arbitrary scenario-chosen constant, never derived from `seed`
    by any algorithm — see the module docstring and C-10.
    """

    seed: bytes
    key: bytes


@dataclass(frozen=True)
class DTC:
    """One entry in the ECU's DTC table, as ReadDTCInformation reports it."""

    code: bytes
    """3-byte DTC code, e.g. b"\\x01\\x23\\x45"."""
    status: int
    """1-byte status mask (ISO 14229 Table 224)."""


@dataclass(frozen=True)
class FailureInjection:
    """A configured misbehaviour, matched against an incoming request.

    `selector` is a DID (for RDBI/WDBI, service IDs 0x22/0x2E) or a
    sub-function (for every other service). `None` matches any selector for
    that service. Matching is exact otherwise — see
    `test_failure_injection_is_scoped_to_its_configured_trigger_only` in the
    test plan: an injection for one (service, selector) pair must never fire
    for a different one.
    """

    service_id: int
    selector: int | None
    kind: FailureKind
    nrc: int = 0x10
    """Used when kind == "nrc" — the code returned as [0x7F, sid, nrc]."""
    declared_length: int = 100
    """Used when kind == "truncated" — the length claimed in a First Frame
    that the responder then never completes."""
    extra_bytes: int = 100
    """Used when kind == "oversized" — how many extra bytes of padding are
    appended beyond the DID's configured value."""


@dataclass
class Scenario:
    """Everything the virtual ECU needs to answer requests and misbehave on
    command. See the module docstring for the design principle: this is the
    only place scenario-specific data lives.
    """

    request_id: int = 0x7E0
    response_id: int = 0x7E8
    initial_session: int = 0x01
    dids: dict[int, DIDConfig] = field(default_factory=dict)
    security_levels: dict[int, SecurityLevelConfig] = field(default_factory=dict)
    dtcs: list[DTC] = field(default_factory=list)
    failure_injections: list[FailureInjection] = field(default_factory=list)

    def matching_injection(self, service_id: int, selector: int | None) -> FailureInjection | None:
        """The injection configured for this exact (service, selector) pair,
        or one configured with selector=None matching any selector for that
        service. Exact matches take priority over wildcard ones.
        """
        wildcard: FailureInjection | None = None
        for injection in self.failure_injections:
            if injection.service_id != service_id:
                continue
            if injection.selector == selector:
                return injection
            if injection.selector is None:
                wildcard = injection
        return wildcard

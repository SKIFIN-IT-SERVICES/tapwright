<!--
Provenance: adapted from Tapwright's internal planning repository (private),
which is not part of this project. Source-file citations below (e.g.
`05-testing-tools-deep-dive/major-platforms-deep-dive.md`) refer to internal
market/technical research that isn't included in this repository — treat
them as provenance/context, not as links you can follow. Everything you
need to act on a requirement is in the requirement row itself.
-->

# Tooling Requirements — Functional Requirement Catalog

**Prepared 2026-07-30.** This is the canonical, numbered catalog of **what the product must do** — organized by the L0–L3 layers defined in [`architecture.md`](architecture.md). [`phase-1-requirements.md`](phase-1-requirements.md) cites these IDs (`TOOL-REQ-xxx`) rather than restating functionality; `architecture.md` uses this catalog to derive module boundaries.

**How to read this document:**
- **Priority** follows MoSCoW: **Must** (v0.1 is not credible without it), **Should** (materially weakens the pitch if missing but doesn't block launch), **Could** (nice-to-have, cut first under time pressure), **Won't** (explicitly deferred — stated so it isn't silently forgotten or re-litigated).
- **Phase** tags where the requirement is exercised: **P0-spike** (Phase 0 validation prototype only), **P1-v0.1** (the Phase 1 OSS wedge release), **Fast-follow** (6–18 months post-v0.1), **Later** (watch, not architected for yet).
- Every requirement cites its source; standards versions and constraints are inherited from [`input-variables.md`](input-variables.md) (`IV-xxx`) rather than restated.
- L4–L5 (security/compliance) are explicitly **out of scope** for this catalog — see §5 for the one architectural constraint they impose on L2 now.

---

## L0 — Hardware Abstraction

Purpose: run identically against whatever CAN interface a team already owns, and against nothing at all (pure virtual bus) for CI/demo. This is the layer that makes the "no hardware to try it" and "runs on hardware teams already own" claims true.

| ID | Requirement | Priority | Phase | Acceptance Criteria | Source |
|---|---|---|---|---|---|
| TOOL-REQ-001 | Multi-backend hardware abstraction layer, built on `python-can` | Must | P0-spike, P1-v0.1 | Works unmodified across ≥3 distinct backends without app-level code changes (interface swap is a config change only) | internal spike plan; `IV-HW-06` |
| TOOL-REQ-002 | SocketCAN backend (Linux-native) | Must | P0-spike, P1-v0.1 | `candump`-equivalent traffic visible through the abstraction on a real Linux CAN interface | internal research, "Minimum credible feature set" #7 |
| TOOL-REQ-003 | `gs_usb` backend (CANable 2.0 / candleLight-class devices) | Must | P0-spike, P1-v0.1 | CANable 2.0 ($35, `IV-HW-02`) sends/receives CAN and CAN-FD frames with zero manual driver installation on Linux | internal research (gs_usb kernel driver: CAN-FD + 1µs HW timestamps native) |
| TOOL-REQ-004 | PEAK PCANBasic backend | Should | P1-v0.1 | Interoperates with a PEAK PCAN-USB/PCAN-USB FD device | `IV-HW-06` |
| TOOL-REQ-005 | Kvaser `canlib` backend | Must | P0-spike, P1-v0.1 | Kvaser Leaf v3 ($410, `IV-HW-03`) proves the abstraction against a second, commercially-licensed vendor stack | `IV-HW-03` |
| TOOL-REQ-006 | Vector XL API backend | Should | Fast-follow | Interoperates with a Vector VN-series interface — signals credibility to the installed base without requiring it | internal research, "must replicate" |
| TOOL-REQ-007 | TOSUN backend | Could | Fast-follow | Interoperates with a TOSUN interface (China-market credibility) | `IV-HW-06` |
| TOOL-REQ-008 | `vcan` (SocketCAN virtual CAN) support | Must | P0-spike, P1-v0.1 | Full test suite and demo flow runs against `vcan` with zero physical hardware attached — this is the CI and onboarding path | `IV-HW-04`; "the 'no hardware to try it' trick" |
| TOOL-REQ-009 | Backend capability detection / graceful degradation | Should | P1-v0.1 | Attempting a CAN-FD operation on a classic-CAN-only interface produces a clear error, not a silent failure or crash | derived — standard HAL hygiene |

---

## L1 — Bus + Measurement Core

Purpose: symbolic decode of what's on the bus, and read/write of the file formats the industry already exchanges. Interop with the Vector-format installed base is explicitly non-negotiable.

| ID | Requirement | Priority | Phase | Acceptance Criteria | Source |
|---|---|---|---|---|---|
| TOOL-REQ-010 | CAN / CAN-FD send and receive | Must | P0-spike, P1-v0.1 | Round-trips a frame across two `vcan`-connected processes | `IV-STD-D1-04` |
| TOOL-REQ-011 | Cyclic / periodic message transmission (basic stimulation) | Must | P1-v0.1 | A configured signal transmits at a fixed period within ±5% jitter on `vcan`; this is the minimum viable building block for the virtual-ECU responder (TOOL-REQ-024) | derived from TOOL-REQ-024's dependency |
| TOOL-REQ-012 | Full multi-node restbus simulation (CANoe-class network simulation, node behavior scripting) | Should | Fast-follow | Not required for v0.1 — v0.1 needs cyclic stimulation (TOOL-REQ-011) and a single virtual-ECU responder (TOOL-REQ-024), not a general restbus designer | internal spike plan, "IS NOT: GUI restbus designer" |
| TOOL-REQ-013 | LIN send/receive (basic) | Should | Fast-follow | Cheap-to-add network-simulation completeness; not required for the UDS/DoIP-in-CI pain slice | `IV-STD-D1-05`; "NOT in v0.1: LIN scheduling depth" |
| TOOL-REQ-014 | DBC ingestion + symbolic decode | Must | P0-spike, P1-v0.1 | A CAN frame decodes to named signals with physical values, using a real DBC file (via `cantools`) | `IV-STD-D1-07` |
| TOOL-REQ-015 | ARXML ingestion (Classic + Adaptive) + symbolic decode | Must | P1-v0.1 | A CAN frame decodes correctly using an ARXML-sourced communication matrix (via `cantools`, contributing back gaps in ARXML depth as needed) | `IV-STD-D1-08` |
| TOOL-REQ-016 | LDF ingestion | Could | Fast-follow | Parses a LIN description file; low priority until LIN (TOOL-REQ-013) is prioritized | `IV-STD-D1-09` |
| TOOL-REQ-017 | A2L (ASAP2) parsing | Should | Fast-follow | Resolves a named ECU variable to its memory address from an A2L file; enables XCP read (TOOL-REQ-018) | `IV-STD-D1-10` |
| TOOL-REQ-018 | XCP read access | Could | Fast-follow | Reads a measurement value via XCP given an A2L-resolved address; XCP **write**/calibration is explicitly out of scope (INCA/CANape territory) | "NOT in v0.1: calibration/XCP write" |
| TOOL-REQ-019 | BLF read + write | Must | P1-v0.1 | A trace recorded by the product opens correctly in Vector CANoe/CANalyzer, and a BLF file exported from CANoe decodes correctly in this product | `IV-STD-D1-12`; "interop with the installed base is non-negotiable" |
| TOOL-REQ-020 | ASC read + write | Must | P1-v0.1 | Same round-trip guarantee as TOOL-REQ-019, for the ASC text-trace format | `IV-STD-D1-12` |
| TOOL-REQ-021 | MDF4 read + write | Must | P1-v0.1 | Produces a valid MDF4 file (via `asammdf`) that opens in a third-party MDF4-compliant tool | `IV-STD-D1-11` |

---

## L2 — Diagnostics Engine

Purpose: the single most-automated test workflow in practice. This layer is Phase 1's centerpiece — it is also the layer with a hard forward-compatibility constraint (§5) because it becomes the security-fuzzing spine in a later phase.

| ID | Requirement | Priority | Phase | Acceptance Criteria | Source |
|---|---|---|---|---|---|
| TOOL-REQ-022 | UDS client over ISO-TP | Must | P0-spike, P1-v0.1 | Reads a DID (0x22) from a real or virtual ECU over CAN, using `udsoncan` + `python-can-isotp` | `IV-STD-D1-01`, `IV-STD-D1-02` |
| TOOL-REQ-023 | UDS client over DoIP | Must | P1-v0.1 | Reads a DID over Ethernet/DoIP against a real or virtual ECU, using `udsoncan` + `doipclient` | `IV-STD-D1-03` |
| TOOL-REQ-024 | Core UDS service coverage | Must | P0-spike (subset), P1-v0.1 (full) | Implements: 0x10 (DiagnosticSessionControl), 0x27/0x29 (SecurityAccess — hook points, not a crypto implementation), 0x22/0x2E (Read/WriteDataByIdentifier), 0x19 (ReadDTCInformation), 0x31 (RoutineControl), 0x34–0x37 (transfer/flash sequence) | internal spike plan v0.1 checklist |
| TOOL-REQ-025 | ODX/PDX import — **read-only** | Should | P1-v0.1 | Consumes an existing OEM diagnostic database (.odx/.pdx) to resolve DID/routine names; write/authoring is explicitly out of scope | `IV-STD-D1-15`; "ODX/PDX import (read-only v0.1)" |
| TOOL-REQ-026 | Virtual UDS ECU responder on `vcan` | Must | P0-spike, P1-v0.1 | A `pip install`-only user can run a full read-DID round trip against a simulated ECU with zero hardware; this target doubles as the CI test fixture and the GitHub Actions demo | "the 'no hardware to try it' trick" |
| TOOL-REQ-027 | Clean, scriptable L2 API (architectural, not user-facing) | Must | P1-v0.1 | A third-party fuzzing harness (e.g. Gallia-style) can drive UDS/DoIP requests through L2's public API without forking or monkey-patching it | §5 below |

---

## L3 — Test Authoring & CI Runner

Purpose: this is the layer that makes "one engine, laptop to CI container" true instead of the CANoe DE/SE fragmentation pattern, and where "everything is a pytest test, not a proprietary binary config" delivers the git-diffability leapfrog.

| ID | Requirement | Priority | Phase | Acceptance Criteria | Source |
|---|---|---|---|---|---|
| TOOL-REQ-028 | `pytest`-native plugin with `ecu`, `bus`, `uds` fixtures | Must | P0-spike, P1-v0.1 | A test author writes `def test_x(uds): ...` with zero custom test-runner boilerplate | internal spike plan v0.1 checklist |
| TOOL-REQ-029 | Deterministic wait helpers (`wait_for_signal` / `wait_for_message` / `wait_for_response`) | Must | P1-v0.1 | A test polling for a bus event does not require hand-rolled sleep/retry loops and does not flake under normal CI timing variance | same |
| TOOL-REQ-030 | Headless Linux + container execution, **same engine as desktop** | Must | P1-v0.1 | The identical package that runs interactively on a developer laptop also runs unattended inside a container with no separate "server edition" build — this is the explicit anti-pattern to avoid (see CANoe DE vs. CANoe Server Edition as separate SKUs) | internal research (CANoe SE as a cautionary pattern) |
| TOOL-REQ-031 | HTML report with pass/fail, timing, decoded frames | Must | P1-v0.1 | A completed test run produces a human-readable HTML report without additional configuration | internal spike plan v0.1 checklist |
| TOOL-REQ-032 | JSON / ATX-style machine-readable report | Should | P1-v0.1 | A completed test run also produces a JSON report suitable for later ingestion by a results warehouse (a later-layer concern, not built now — just don't block it) | same |
| TOOL-REQ-033 | GitHub Actions example/template against the virtual ECU | Must | P1-v0.1 | A copy-pasteable workflow file runs the full UDS test suite against TOOL-REQ-026's virtual ECU in a stock GitHub Actions runner | "runs headless in CI" |
| TOOL-REQ-034 | GitLab CI example/template | Should | P1-v0.1 | Same as TOOL-REQ-033 for GitLab CI | same |
| TOOL-REQ-035 | Everything-as-text: tests are `.py`, config is YAML/TOML | Must | P1-v0.1 | A test suite and its configuration are fully expressible as text files that `git diff` renders meaningfully — no binary or opaque project file is required to run or review a test | "Everything-as-text" (leapfrog vs. CANoe's binary configs) |

---

## Explicitly Out of Scope for Phase 0/1 (Won't)

Stated so it is not silently forgotten or re-litigated mid-build:

| Item | Why |
|---|---|
| GUI restbus-simulation designer | v0.1 needs cyclic stimulation + one virtual ECU, not a general network-simulation authoring UI |
| SOME/IP + SOME/IP-SD | Fast-follow (`IV-STD-FF-01`) |
| Calibration workflows / XCP write | INCA/CANape territory — deliberately not competing here |
| SOVD client | Fast-follow, cheap but not day-1 (`IV-STD-FF-02`) |
| LIN scheduling depth | Basic LIN send/receive is Should/Fast-follow (TOOL-REQ-013); full schedule-table authoring is out |
| Own hardware | Deferred, gated on proven software pull (`IV-HW-05`) |
| Hard-real-time HIL I/O | dSPACE/NI territory — partner, don't compete |
| Protocol conformance suites (TC8, LIN CT) | Defer indefinitely; low leverage for the wedge |
| FlexRay depth | Legacy, declining, no new-design momentum |
| Any AUTOSAR BSW stack functionality | Wrong business entirely — this is a testing tool, not a stack (`IV-REG-03`) |

---

## §5. The One Constraint L4–L5 Impose on L2 Now

L4 (security testing) and L5 (compliance/orchestration) are **not** built in this repository and are not further specified in this document — see [`architecture.md`](architecture.md#licensing-model). But internal planning establishes that a future L4 security-fuzzing layer will be built as **Gallia (UDS/DoIP scanning, Apache-2.0) + CaringCaribou/boofuzz (fuzzing) wrapped around this same L2 engine** — not a fork of it. That is the entire justification for TOOL-REQ-027 (clean, scriptable L2 API): if L2's diagnostics engine is built with a tangled or private API now because "the fuzzer is years away," a future security layer becomes a rewrite instead of an extension. TOOL-REQ-027 is therefore rated **Must**, not **Should**, despite having no user-visible effect in Phase 0/1.

---

## Traceability Index

| Layer | ID range | Count | Depends on (`IV-xxx`) |
|---|---|---|---|
| L0 Hardware abstraction | TOOL-REQ-001–009 | 9 | `IV-HW-*` |
| L1 Bus + measurement core | TOOL-REQ-010–021 | 12 | `IV-STD-D1-04` to `-12` |
| L2 Diagnostics engine | TOOL-REQ-022–027 | 6 | `IV-STD-D1-01` to `-03`, `-15`; `IV-REG-08` |
| L3 Test authoring & CI runner | TOOL-REQ-028–035 | 8 | `IV-LIC-*` |

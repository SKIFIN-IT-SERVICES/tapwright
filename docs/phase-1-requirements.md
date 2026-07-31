<!--
Provenance: adapted from Tapwright's internal planning repository (private).
Team/budget figures are omitted (see §1) — everything else is the full spec.
-->

# Phase 1 Requirements — OSS Wedge (v0.1)

**Prepared 2026-07-30.** This is the fullest, most formal spec for what this repository builds. It's organized by milestones M1–M6 (weeks 0–26); each milestone lists exactly which `TOOL-REQ-xxx` ([`tooling-requirements.md`](tooling-requirements.md)) and `FW-REQ-xxx` ([`framework-requirements.md`](framework-requirements.md)) IDs it satisfies, plus milestone-specific acceptance criteria and an exit deliverable. See [`ROADMAP.md`](../ROADMAP.md) at the repo root for the short public version of this same plan.

---

## 1. Objectives & Scope

**What v0.1 IS:** a Linux-first, pytest-native, CI-runnable **UDS/DoIP diagnostic test runner + DBC/ARXML-aware trace analyzer** that reads the industry's existing files (DBC, ARXML, BLF, ASC, MDF4) and runs on hardware teams already own — not a CANoe clone, not a restbus designer, not a calibration tool.

**What v0.1 IS NOT:** see §5 (out of scope), inherited in full from [`tooling-requirements.md`](tooling-requirements.md)'s "Explicitly Out of Scope" table.

**Why this slice:** UDS/DoIP is the single most-automated test workflow in practice, needs no AUTOSAR license (`IV-REG-01`), is TCL1 (`IV-REG-03`), and is the natural on-ramp to a future paid security layer ([`architecture.md`](architecture.md) ADR-004) — a fuzzer that eventually monetizes this product wraps the same L2 engine v0.1 builds.

**Timeline:** Weeks 0–26 (= `IV-BUS-06`, Months 3–8). Team and budget for this phase are tracked in internal project planning, not published here.

---

## 2. Functional Requirements by Milestone

### M1 — Spike (Weeks 0–3)

Goal: prove the core library glue works before building product structure around it.

| Satisfies | Requirement (from) | Milestone-specific acceptance criteria |
|---|---|---|
| TOOL-REQ-001, -002, -003 or -005 | L0 abstraction over SocketCAN + one real interface | `python-can` + `udsoncan` + `python-can-isotp` glue proven against `vcan` and one of CANable 2.0 / Kvaser Leaf v3 |
| TOOL-REQ-008 | `vcan` support | Zero-hardware path works from day one of the milestone, not retrofitted later |
| TOOL-REQ-010 | CAN send/receive | Frame round-trips correctly |
| TOOL-REQ-022 | UDS over ISO-TP | A single `0x22` (ReadDataByIdentifier) round trip succeeds against a real or virtual target |
| FW-REQ-050 | Apache-2.0 + SPDX headers | Applied from the repo's first commit, not added later — **done** |

**Exit deliverable:** a working, ugly proof that the L0→L2 chain functions end-to-end. This milestone is allowed to be scrappy; M2 is not.

### M2 — Core Diagnostics (Weeks 3–8)

Goal: the full UDS/DoIP + decode engine, built to the architectural standard the rest of the product depends on.

| Satisfies | Requirement | Milestone-specific acceptance criteria |
|---|---|---|
| TOOL-REQ-001, -004, -005, -009 | Full L0 multi-backend abstraction, incl. PEAK, with graceful capability detection | ≥3 backends proven, informed by Phase 0's spike findings, not repeating the spike from scratch |
| TOOL-REQ-011 | Cyclic/periodic transmission | Powers the virtual-ECU responder built in M4 |
| TOOL-REQ-014, -015 | DBC + ARXML (Classic+Adaptive) ingestion and symbolic decode | A real DBC and a real ARXML file both decode a CAN frame to named signals correctly |
| TOOL-REQ-023 | UDS over DoIP | A `0x22` round trip succeeds over DoIP against a real or virtual target |
| TOOL-REQ-024 | Full core UDS service set | 0x10, 0x22/0x2E, 0x19, 0x27/0x29 (hook points), 0x31, 0x34–37 all implemented |
| **TOOL-REQ-027** | **Clean, scriptable L2 API** | **This is the milestone where the architectural discipline in [`architecture.md`](architecture.md) §4 and ADR-004 must actually be applied — verify against that section before declaring M2 done, not after.** |
| TOOL-REQ-028, -029 | pytest fixtures + deterministic wait helpers | `def test_x(uds): ...` works with zero custom runner boilerplate; polling helpers don't flake under normal CI timing variance |

**Exit deliverable:** the diagnostics engine a design partner could plausibly point at a real ECU.

### M3 — Trace + Report (Weeks 8–12)

Goal: interop with the installed base's file formats, and make results legible.

| Satisfies | Requirement | Milestone-specific acceptance criteria |
|---|---|---|
| TOOL-REQ-019 | BLF read+write | Round-trips correctly with Vector CANoe/CANalyzer (verify against a real CANoe-produced BLF file if available; otherwise against published format spec) |
| TOOL-REQ-020 | ASC read+write | Same round-trip guarantee |
| TOOL-REQ-021 | MDF4 read+write | Produces a valid MDF4 file that opens in a third-party MDF4-compliant tool |
| TOOL-REQ-031 | HTML report | Pass/fail, timing, decoded frames all present without extra configuration |
| TOOL-REQ-032 | JSON report | Machine-readable, structured for later results-warehouse ingestion (not built now — just don't block it) |

**Exit deliverable:** a test run against real bus traffic produces a report a non-expert can read, and a trace file Vector's own tools can open.

### M4 — CI Story (Weeks 12–16)

Goal: this is the milestone that makes "CI-native" true rather than aspirational.

| Satisfies | Requirement | Milestone-specific acceptance criteria |
|---|---|---|
| TOOL-REQ-026 | Virtual UDS ECU on `vcan` | A `pip install`-only user runs the full read-DID loop on a bare laptop |
| TOOL-REQ-030 | Headless Linux + container execution, same engine as desktop | The identical package runs unattended in a container — verify explicitly that no separate build artifact exists for CI (this is ADR-001's test) |
| TOOL-REQ-033 | GitHub Actions example | Copy-pasteable workflow runs the full UDS suite against the M4 virtual ECU on a stock runner — **skeleton done**, see `.github/workflows/ci.yml` |
| TOOL-REQ-034 | GitLab CI example | Same, for GitLab CI |
| FW-REQ-021 | Container image | Published, not just documented as a future step |
| FW-REQ-066 | Documentation site live | Required by end of this milestone |

**Exit deliverable:** a stranger can find the repo, `pip install`, and get a green CI run against the virtual ECU inside one sitting — this is the adoption unlock the whole thesis depends on.

### M5 — ODX + Polish (Weeks 16–22)

Goal: the "build in public" launch readiness milestone.

| Satisfies | Requirement | Milestone-specific acceptance criteria |
|---|---|---|
| TOOL-REQ-025 | ODX/PDX read-only import | Resolves DID/routine names from a real OEM diagnostic database file |
| TOOL-REQ-035 | Everything-as-text | Full audit: no binary or opaque project file is required anywhere in the test-authoring or config path |
| FW-REQ-020 | `pip install`-able PyPI package | Published and installable by an external user, not just locally buildable |
| FW-REQ-061, -062, -063 | `CONTRIBUTING.md`, Code of Conduct, issue/PR templates | Published before the public launch announcement — **done** |
| FW-REQ-064 | Semantic Versioning + CHANGELOG | In place for the launch tag — **done** |

**Exit deliverable:** the public "build in public" launch — targeting the python-can/cantools/SavvyCAN community.

### M6 — Design-Partner Pilot (Weeks 20–26, overlaps M5)

Goal: deploy in a real workflow and let real friction — not internal assumptions — shape the paid tier.

| Requirement | Milestone-specific acceptance criteria |
|---|---|
| P1-REQ-M6-01 | A design partner deploys v0.1 into a real Indian EV OEM or ARAI/ICAT-adjacent lab workflow |
| P1-REQ-M6-02 | Pains and gaps surfaced during the pilot are logged and explicitly mapped to future L3-paid or L4/L5 features — not silently absorbed as "known issues" |
| P1-REQ-M6-03 | Pilot engagement is the primary input for converting the design partner into the first paid support contract later |

---

## 3. Non-Functional Requirements

Inherited from [`architecture.md`](architecture.md) §6 (`NFR-001`–`NFR-006`) — not restated here. Of particular relevance to acceptance testing: **NFR-003** (test determinism — the virtual ECU + wait helpers from M2/M4 must not produce flaky CI) and **NFR-005** (time-to-first-green-test — the M4 exit deliverable is effectively this NFR's acceptance test).

---

## 4. Dependencies

The full build-vs-reuse table with license status lives in [`framework-requirements.md`](framework-requirements.md) §2 (`FW-REQ-010`–`018`). Flag for planning: `FW-REQ-012` and `FW-REQ-015` mark `python-can-isotp` and `asammdf`'s licenses as **[EST — verify before shipping]** — this verification should happen in M1/M2, not discovered at M5 packaging time.

---

## 5. Out of Scope

Inherited in full from [`tooling-requirements.md`](tooling-requirements.md) "Explicitly Out of Scope" table — GUI restbus designer, SOME/IP, calibration/XCP write, SOVD client, LIN scheduling depth, own hardware, hard-real-time HIL I/O, protocol conformance suites, FlexRay depth, any AUTOSAR BSW stack functionality. Not restated here; treat that table as authoritative for scope disputes.

---

## 6. Exit Gate

| ID | Gate | Threshold |
|---|---|---|
| P1-REQ-GATE | v0.1 → paid tier (later, not this repo's target) | `IV-KPI-02` — ≥500 engaged users **AND** the design partner (M6) using the product in anger, not just piloting it passively |
| P1-REQ-KILL | Month-6 kill/re-aim checkpoint | `IV-KPI-03` — if <500 engaged users AND no design partner willing to pay by month 6, re-aim rather than abandoning the underlying gap |

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| M2's L2 API-cleanliness requirement (TOOL-REQ-027) gets deprioritized under milestone time pressure since it has no user-visible payoff | High | Called out explicitly, in bold, in the M2 table above — this is the single highest-leverage "invisible" requirement in the whole document set |
| `python-can-isotp` / `asammdf` license verification (FW-REQ-012/015) slips late, forcing a scramble if either turns out to require isolation | Medium | Explicitly sequenced into M1/M2 in §4 above, not left until packaging (M5) |
| Design-partner pilot (M6) surfaces friction too late to influence the M1–M5 build | Medium | M6 deliberately overlaps M5 rather than starting after it |
| Scope creep from the "Should"/"Could" items in `tooling-requirements.md` displacing "Must" items under the 26-week timeline | Medium | MoSCoW priority in the source catalog is the tie-breaker; a milestone is not "done" until its Must items are done, regardless of how much Should/Could work happened |

---

## Traceability Index

| Milestone | Weeks | Primary TOOL-REQ / FW-REQ IDs |
|---|---|---|
| M1 Spike | 0–3 | TOOL-REQ-001–003/005, 008, 010, 022; FW-REQ-050 |
| M2 Core diagnostics | 3–8 | TOOL-REQ-001, 004, 005, 009, 011, 014, 015, 023, 024, **027**, 028, 029 |
| M3 Trace + report | 8–12 | TOOL-REQ-019–021, 031, 032 |
| M4 CI story | 12–16 | TOOL-REQ-026, 030, 033, 034; FW-REQ-021, 066 |
| M5 ODX + polish | 16–22 | TOOL-REQ-025, 035; FW-REQ-020, 061–064 |
| M6 Design-partner pilot | 20–26 | P1-REQ-M6-01–03 |

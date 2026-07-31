<!--
Provenance: adapted from Tapwright's internal planning repository (private).
Source-file citations refer to internal research not included here — treat
as provenance/context, not links. This is the full, detailed architecture
spec; the repo-root ARCHITECTURE.md is a shorter public-facing summary of
the same material — read this one if you're implementing, that one if
you're evaluating the project.
-->

# Architecture (full spec)

**Prepared 2026-07-30.** This document synthesizes [`input-variables.md`](input-variables.md), [`tooling-requirements.md`](tooling-requirements.md), and [`framework-requirements.md`](framework-requirements.md) into a system design: module boundaries, data flow, deployment model, non-functional requirements, and the load-bearing architecture decisions (as ADRs). It does not restate requirement content — it cites `IV-xxx`/`TOOL-REQ-xxx`/`FW-REQ-xxx` and explains how they compose into one system.

---

## 1. Guiding Principle

> **One engine. Laptop, headless Linux bench, and CI container are three ways of *invoking* the same package — never three separate products.**

This is the single architectural principle every other decision in this document serves. It is stated first because it is also the principle the incumbents most visibly violate: Vector CANoe fractures into CANoe Desktop Edition and CANoe Server Edition as separate SKUs with separate licenses; dSPACE needs four-plus separate tools/licenses to close one automated HIL loop. TOOL-REQ-030 makes this a hard functional requirement; this document makes it an architectural one.

---

## 2. Layered Module Map

```
┌──────────────────────────────────────────────────────────────────┐
│  L5  Compliance & orchestration       — SEPARATE REPO (§9, ADR-005)│
│      R155/ISO 21434 evidence · regression-on-OTA · fleet sched.   │
├──────────────────────────────────────────────────────────────────┤
│  L4  Security testing                 — SEPARATE REPO (§9, ADR-005)│
│      UDS/DoIP fuzzing, wraps Gallia/CaringCaribou/boofuzz          │
╞══════════════════ this repository's build boundary ═══════════════╡
│  L3  runner/  report/  trace/         — pytest plugin, HTML/JSON  │
│      reports, BLF/ASC/MDF4 trace read+write, CI examples          │
├──────────────────────────────────────────────────────────────────┤
│  L2  diag/                            — UDS (ISO 14229) client,   │
│      DoIP (ISO 13400) transport, ODX/PDX read, virtual-ECU target │
├──────────────────────────────────────────────────────────────────┤
│  L1  buses/  dbc_arxml/               — CAN/CAN-FD/LIN restbus    │
│      (basic cyclic stim), DBC/ARXML/LDF decode, A2L parse         │
├──────────────────────────────────────────────────────────────────┤
│  L0  hal/                             — SocketCAN, gs_usb, PEAK,  │
│      Kvaser, Vector XL, TOSUN via python-can; vcan virtual bus    │
└──────────────────────────────────────────────────────────────────┘
```

The build-boundary line is the single most important line on this diagram: **L0–L3 is this repository's entire scope.** L4–L5 exist on the diagram only because L2 must be designed to support them later without a fork (ADR-004) — nothing above the line is built, imported, or referenced by this package.

### 2.1 Module responsibilities

| Module | Layer | Responsibility | Key requirements satisfied |
|---|---|---|---|
| `hal/` | L0 | One abstraction, N backends; owns the vendor-specific driver calls so nothing above it ever branches on interface vendor | TOOL-REQ-001–009 |
| `buses/` | L1 | Frame-level send/receive, cyclic stimulation, symbolic decode orchestration | TOOL-REQ-010–013 |
| `dbc_arxml/` | L1 | DBC/ARXML/LDF/A2L parsing — thin wrappers around `cantools` (FW-REQ-011) | TOOL-REQ-014–018 |
| `diag/` | L2 | UDS/DoIP client, ODX import, virtual-ECU responder, the Gallia-wrappable public API | TOOL-REQ-022–027 |
| `runner/` | L3 | pytest plugin: fixtures, wait helpers, CI entrypoints | TOOL-REQ-028–030, 033–035 |
| `report/` | L3 | HTML/JSON report generation | TOOL-REQ-031–032 |
| `trace/` | L1/L3 boundary | BLF/ASC/MDF4 read+write, query/filter over recorded traffic | TOOL-REQ-019–021 |

---

## 3. Data Flow

```
  Input files                     Runtime engine                    Output
  ───────────                     ──────────────                    ──────
  DBC / ARXML / LDF ──┐
  A2L ─────────────────┼──▶  dbc_arxml/ (decode)  ──┐
  ODX / PDX ───────────┘                            │
                                                      ▼
  Physical bus ──▶ hal/ (backend) ──▶ buses/ (frames) ──▶ diag/ (UDS/DoIP) ──▶ runner/ (pytest)
  or vcan ──────────▶                                                              │
  (TOOL-REQ-008)                                                                   ├──▶ report/ (HTML/JSON)
                                                                                    │
  BLF / ASC / MDF4 ◀── trace/ (write) ◀──────────────────────────────────────────┘
       (recorded)         │
                           └──▶ trace/ (read/query) ──▶ (fed back into dbc_arxml/ for symbolic re-decode)
```

Two entry points into the runtime engine are equally first-class: a **physical bus** through `hal/`, or **`vcan`** with no hardware at all (TOOL-REQ-008, TOOL-REQ-026). Nothing downstream of `buses/` can tell the difference — this is what makes the "no hardware to try it" claim architecturally true rather than a marketing simplification.

---

## 4. The L2 API Contract (the one interface this document specifies in detail)

Per TOOL-REQ-027 and ADR-004, `diag/`'s public API is the single most architecturally constrained surface in the system, because a party outside this codebase (a future Gallia-based fuzzer, in a separate repo per ADR-005) must be able to drive it without modification. Concretely, this means:

- **Transport-agnostic client interface.** Calling code issues UDS service requests (session control, DID read/write, routine control, security access, transfer) through one client object; whether the underlying transport is ISO-TP-over-CAN or DoIP-over-Ethernet is a construction-time choice, invisible to the calling code (TOOL-REQ-022, TOOL-REQ-023).
- **A request/response interception point.** Every outbound request and inbound response passes through an inspectable hook — this is what lets a fuzzer sit *in front of* the client and mutate requests, or sit *behind* it and log/replay traffic, without touching `diag/`'s internals. This is the concrete mechanism ADR-004 refers to; it does not exist yet in this repository's current scope but the API must not preclude adding it later without a breaking change.
- **No hidden state that a second, concurrent test can't observe.** A test-runner-driven UDS session and a security-fuzzing session must be able to reason about ECU session/security state the same way — this is what makes "a future security layer wraps L2" true rather than aspirational.

This is a design constraint on L2, not a v0.1 deliverable in itself — no interception-hook code ships in v0.1. It is listed here so the constraint is visible to whoever writes `diag/`'s first version, not discovered as a rewrite requirement later.

---

## 5. Deployment Model

| Environment | What runs | Requirement |
|---|---|---|
| Developer laptop | Full package, interactive use, `vcan` or a $35 CANable 2.0 | TOOL-REQ-008, IV-HW-02 |
| Headless Linux bench | Identical package, unattended, real hardware (Kvaser Leaf v3, etc.) | TOOL-REQ-005, IV-HW-03 |
| CI container (GitHub Actions / GitLab CI) | Identical package, `vcan` + virtual UDS ECU, zero physical hardware | TOOL-REQ-026, TOOL-REQ-033/034 |

All three rows install from the same PyPI package / container image (FW-REQ-020, FW-REQ-021). There is no "CI edition."

---

## 6. Non-Functional Requirements — `NFR-xxx`

| ID | Requirement | Priority | Detail | Source |
|---|---|---|---|---|
| NFR-001 | Portability | Must | Linux is the primary target (SocketCAN-native); macOS and Windows are secondary/best-effort, not launch-blocking if degraded | `IV-HW-01` |
| NFR-002 | Timestamp fidelity | Should | Software timestamps are acceptable for CI/diagnostics use in this phase. Hardware timestamping (sub-µs, the credibility feature once own hardware ships) is explicitly a later-phase concern — do not over-engineer timestamp precision now. | internal research |
| NFR-003 | Test determinism | Must | The virtual-ECU + wait-helper combination (TOOL-REQ-026, TOOL-REQ-029) must produce non-flaky CI runs — flaky CI is disqualifying for a CI-native pitch | derived |
| NFR-004 | Extensibility (L2) | Must | See §4 — the L2 API contract | TOOL-REQ-027; ADR-004 |
| NFR-005 | Time-to-first-green-test | Should | [NEW-EST — no source specifies a number; suggested target: a new user reaches a passing test against the virtual ECU in well under an hour from `pip install`.] | derived from the "no hardware to try it" adoption thesis |
| NFR-006 | License purity | Must | No copyleft dependency is compiled into the distributed OSS core without explicit isolation (see FW-REQ-012, FW-REQ-015 license-verification flags) | `IV-LIC-04`; FW-REQ-017 |

---

## 7. Architecture Decision Records

### ADR-001 — Single Engine Across Desktop, Bench, and CI Container
- **Status:** Accepted
- **Context:** Every major incumbent (CANoe, dSPACE, ETAS) splits desktop-interactive and headless/CI use into separately licensed products, and this fragmentation is one of the most-cited pain points in the market research this project is built on.
- **Decision:** One package. Interactive use and CI use are invocation modes of the same code, never separate builds or SKUs.
- **Consequences:** Any future interactive/GUI feature must be additive and optional, never something core execution depends on. This constrains later product decisions (e.g., a GUI cannot become a hard dependency of `runner/`).

### ADR-002 — Python as the Core Language
- **Status:** Accepted
- **Context:** The community being targeted for bottom-up adoption (python-can/cantools/udsoncan/pytest users) is a Python community.
- **Decision:** Python core; defer any Rust rewrite of the bus engine until adoption, not launch speed, is the bottleneck.
- **Consequences:** Accepts a performance ceiling in exchange for adoption speed; revisit only if profiling post-launch shows the bus engine, not distribution, is the constraint.
- **Source:** FW-REQ-001, FW-REQ-003.

### ADR-003 — Apache-2.0 for L0–L3, Commercial Reserved for L4–L5, in a Separate Repository
- **Status:** Accepted
- **Context:** The monetization model depends on L0–L3 being maximally adoptable (open-core wedge) while L4–L5 remain the revenue layer.
- **Decision:** Apache-2.0 license on this entire repo (see [LICENSE](../LICENSE)); L4–L5 code is never merged into this repo, even in prototype form — it lives in a separate, private repository from its first line of code.
- **Consequences:** Slightly more setup overhead now (two repos instead of one) in exchange for never needing to surgically extract proprietary history from OSS git history later.
- **Source:** `IV-LIC-01`, `IV-LIC-02`, FW-REQ-052.

### ADR-004 — The L2 Diagnostics Engine API Must Be Gallia-Wrappable
- **Status:** Accepted
- **Context:** Internal planning establishes that a future security-testing revenue layer is built as Gallia + CaringCaribou/boofuzz wrapped around this exact L2 engine, not a rewrite of it.
- **Decision:** L2's public API (§4) is designed for external interception/wrapping from its first version, even though no wrapper exists yet.
- **Consequences:** A small amount of design discipline now (an interception hook point that has zero users today) avoids a future rewrite of the product's highest-leverage layer.
- **Source:** TOOL-REQ-027, `IV-REG-08`.

### ADR-005 — `vcan`-Based Zero-Hardware Onboarding Is a First-Class Path, Not a Fallback
- **Status:** Accepted
- **Context:** "I need a car or bench to try your tool" is identified as the specific adoption killer in this project's planning.
- **Decision:** The virtual-ECU-on-`vcan` path (TOOL-REQ-008, TOOL-REQ-026) is designed and tested with the same priority as real-hardware paths, not bolted on afterward — it is also the CI test fixture and the quick-start demo, so under-investing in it breaks three things at once, not one.
- **Consequences:** Real-hardware backends (Kvaser, PEAK, Vector XL) can lag `vcan` in maturity without blocking launch; `vcan` cannot lag.
- **Source:** TOOL-REQ-008, TOOL-REQ-026, NFR-005.

### ADR-006 — DCO, Not a Full CLA, for Contributions
- **Status:** Accepted — implemented in [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Context:** See FW-REQ-051 for the full tradeoff discussion.
- **Decision:** Use a Developer Certificate of Origin rather than a Contributor License Agreement, prioritizing contribution friction over future relicensing flexibility.
- **Consequences:** Slightly reduces optionality to relicense community-contributed L3 code commercially later; meaningfully reduces friction for the exact bottom-up contributor motion the whole GTM depends on.
- **Source:** FW-REQ-051.

---

## 8. What This Document Deliberately Does Not Cover

- **L4–L5 internal design** — out of scope for this repository; only the L2 boundary constraint (ADR-004) is specified now.
- **Exact numeric performance targets beyond NFR-005** — no source data exists for latency/throughput targets; do not fabricate them. Set these once real telemetry exists.

## Licensing model

L0–L3 (this repository) is Apache License 2.0 — see [LICENSE](../LICENSE). Security-testing and compliance-evidence automation (L4/L5) are planned as a separate, commercially-licensed layer built *around* this engine, in a separate repository — not a fork of it, and not merged into this one.

<!--
Provenance: adapted from Tapwright's internal planning repository (private).
Business/funding figures (headcount, budget, capital, funding posture) are
intentionally omitted from this public copy — see §1. Everything a
developer needs (standards, regulatory constraints, hardware/OS targets,
licensing, success metrics) is unredacted below.
-->

# Input Variables — Foundational Constraints & Parameters

**Prepared 2026-07-30.** This is the reference for the numbers, constraints, and parameters cited across [`tooling-requirements.md`](tooling-requirements.md), [`framework-requirements.md`](framework-requirements.md), [`architecture.md`](architecture.md), and [`phase-1-requirements.md`](phase-1-requirements.md).

Labeling: **[HARD]** = directly sourced; **[EST]** = estimate/judgment; **[NEW-EST]** = a judgment call worth confirming rather than treating as settled.

---

## 1. Business Inputs — `IV-BUS-xxx`

Headcount, budget, funding posture, and capital figures are tracked in internal project planning and intentionally not published in this repository. The two timeline milestones below are kept because they're the ones other documents in this folder actively cite:

| ID | Parameter | Value | Label |
|---|---|---|---|
| IV-BUS-03 | Phase 0 (validation) duration | Months 0–3 | [HARD] |
| IV-BUS-06 | Phase 1 (this repo's scope) duration | Months 3–8 (= weeks 0–26 of the M1–M6 milestone plan) | [HARD] |

---

## 2. Target User Segments — `IV-SEG-xxx`

| ID | Segment | Who / where to find them |
|---|---|---|
| IV-SEG-01 | Indian Tier-1/Tier-2 supplier engineers | ECU test engineers, V&V leads, diagnostics engineers |
| IV-SEG-02 | Indian EV OEM engineers | Vehicle-software test, BMS/VCU validation, homologation |
| IV-SEG-03 | GCC / captive engineers | AUTOSAR integration + test engineers |
| IV-SEG-04 | ARAI/ICAT-adjacent labs | Homologation + emerging cybersecurity-testing capability |
| IV-SEG-05 | Global grassroots OSS community | python-can/cantools/udsoncan users, SavvyCAN users, r/embedded, r/CarHacking |

IV-SEG-01/02/05 are the primary adoption targets — the OSS wedge is aimed at engineers who can self-serve, not procurement-gated buyers.

---

## 3. Standards & Protocols In Scope — `IV-STD-xxx`

### 3.1 Day-1 (v0.1 must implement) — `IV-STD-D1-xxx`

| ID | Standard | Version (2026-07) | Role |
|---|---|---|---|
| IV-STD-D1-01 | UDS (ISO 14229-1) | 2020 ed. | Diagnostic services client — core services 0x10/0x22/0x2E/0x19/0x27/0x29/0x31/0x34-37 |
| IV-STD-D1-02 | ISO-TP (ISO 15765-2) | current | Transport for UDS-over-CAN |
| IV-STD-D1-03 | DoIP (ISO 13400) | current | Transport for UDS-over-Ethernet; modern flashing/HPC path |
| IV-STD-D1-04 | CAN / CAN-FD (ISO 11898) | current | Day-1 bus, ubiquitous |
| IV-STD-D1-05 | LIN (ISO 17987) | current | Day-1, cheap to add for network-simulation completeness |
| IV-STD-D1-06 | Automotive Ethernet (100/1000BASE-T1) | — | Day-1 backbone; frame-level, SOME/IP-aware |
| IV-STD-D1-07 | DBC | Vector de-facto format | CAN signal database ingestion |
| IV-STD-D1-08 | ARXML (Classic + Adaptive) | — | AUTOSAR communication-matrix ingestion |
| IV-STD-D1-09 | LDF | — | LIN description ingestion |
| IV-STD-D1-10 | A2L / ASAM MCD-2 MC (ASAP2) | 1.7.1 (2018) | ECU variable description for measurement/calibration; pairs with XCP |
| IV-STD-D1-11 | MDF4 / ASAM MDF | 4.3.0 (2025-09-23) | Result/trace file format — read **and** write |
| IV-STD-D1-12 | BLF / ASC | Vector formats | Trace interop with the installed base — non-negotiable |
| IV-STD-D1-13 | ASAM XIL | 3.0.0 (2024-09-30) | MAPort server/client — interop with incumbent test automation and benches |
| IV-STD-D1-14 | FMI | 3.0.2 / 2.0, + FMI-LS-BUS, FMI-LS-XCP | FMU import — consume everyone's vECUs |
| IV-STD-D1-15 | ODX / MCD-2 D (.odx/.pdx) | 2.2.0 | **Read-only** import in v0.1 — consume existing OEM diagnostic databases |

### 3.2 Fast-follow (6–18 months post-v0.1) — `IV-STD-FF-xxx`

| ID | Standard | Note |
|---|---|---|
| IV-STD-FF-01 | SOME/IP + SOME/IP-SD | Service-oriented testing, Classic & Adaptive AUTOSAR |
| IV-STD-FF-02 | SOVD (ASAM Service-Oriented Vehicle Diagnostics) | HTTP/REST/JSON diagnostics — the only cloud-native diagnostics standard; cheap, differentiating |
| IV-STD-FF-03 | ODX **write** | Beyond v0.1's read-only import |
| IV-STD-FF-04 | SSP 2.0.1 | Whole simulation-architecture import (systems of FMUs) |
| IV-STD-FF-05 | CAN XL (ISO 11898-1:2024) | Early-adoption phase; not day-1 |
| IV-STD-FF-06 | 10BASE-T1S (IEEE 802.3cg) | Watch/fast-follow; ASAM CMP already lists it as a capture interface |
| IV-STD-FF-07 | ASAM CMP | 1.1.0 (2026-01-26) — capture-hardware interop, fresh standard, early-mover opportunity |

### 3.3 Later / watch — `IV-STD-LW-xxx`

TSN (IEEE 802.1, gPTP), DDS, zenoh, OTX authoring/runtime, OpenSCENARIO/OpenDRIVE (only if entering ADAS scenario testing — out of this product's thesis entirely).

### 3.4 Explicitly out of scope

Hard-real-time HIL I/O, full calibration-department workflows (INCA territory), protocol conformance suites (TC8/LIN CT), FlexRay depth (legacy), any AUTOSAR BSW stack functionality.

---

## 4. Regulatory & Legal Constraints — `IV-REG-xxx`

| ID | Constraint | Detail | Label |
|---|---|---|---|
| IV-REG-01 | No AUTOSAR exploitation license required | Applies to tools that read/write **published** protocol specs (SOME/IP, UDS, DoIP) without implementing/selling an AUTOSAR BSW stack. Specifications are freely downloadable; the exploitation-license regime targets stack implementations, not interoperability tooling. | [HARD, with interpretation] |
| IV-REG-02 | AUTOSAR Development Partner membership NOT required for this repo's scope | Tier costs €10k/yr + 0.5 FTE; only becomes advisable if ARXML/config features deepen well beyond current scope. | [EST] |
| IV-REG-03 | Product must stay a **verification/test tool**, never a code generator | This is a hard architectural boundary, not a style preference: verification/test tools are typically ISO 26262-8 Clause 11 **TCL1 — no qualification required**; code generators are typically **TCL3** — six-figure, 6–18-month TÜV efforts. Any feature that starts generating production code (vs. testing/observing it) moves the whole product's TCL classification. | [HARD] |
| IV-REG-04 | No ASPICE assessment required for the tool vendor itself | ASPICE demands apply to companies shipping stack software *into vehicles*, not desktop/CI tool vendors. | [EST — documented industry practice] |
| IV-REG-05 | ARAI/ICAT are homologation bodies, not software-tool certifiers | Relevant to positioning (design-partner labs) but not a certification gate for this product. | [HARD] |
| IV-REG-06 | "AUTOSAR" is a protected trademark | Do not market the product as AUTOSAR-branded/conformant without partnership. | [EST — inferred] |
| IV-REG-07 | No ISO 26262 requirement on bench/lab hardware | A lab test tool is not an "item" in the ISO 26262 sense (that scope is safety-related E/E systems installed in production vehicles). | [HARD] |
| IV-REG-08 | Forward-compatibility constraint from a future security layer (out of this repo's scope) | R155 (EU, in force since Jul 2024) / AIS-189 (India, draft, phase-in 2026→2029) are territory for a future security/compliance layer, not this repository. But they are *why* `TOOL-REQ` mandates a clean, scriptable L2 diagnostics API here: a fuzzer must be able to bolt onto it later without a fork. | [HARD] |

---

## 5. Hardware & OS Targets — `IV-HW-xxx`

| ID | Parameter | Value | Label |
|---|---|---|---|
| IV-HW-01 | OS priority | Linux-first (SocketCAN native) primary; macOS/Windows secondary/best-effort | [EST — derived from thesis] |
| IV-HW-02 | Reference hardware — interface A | CANable 2.0, $35, STM32G4-class MCU, gs_usb/candleLight protocol, USB-C | [HARD] |
| IV-HW-03 | Reference hardware — interface B | Kvaser Leaf v3, $410, MagiSync timestamp sync, 100µs timestamp resolution class | [HARD] |
| IV-HW-04 | Zero-hardware CI/demo path | SocketCAN `vcan` (virtual CAN) — required so CI needs no physical hardware and so `pip install` + run works on a bare laptop | [EST — product requirement derived from the "no hardware to try it" adoption problem] |
| IV-HW-05 | Hardware manufacturing scope | **None** in this repository's scope. Software-first sequencing: ship on hardware customers already own. | [EST — explicit recommendation] |
| IV-HW-06 | Multi-vendor backend abstraction target list | SocketCAN, gs_usb, PEAK (PCANBasic), Kvaser (canlib), Vector XL API, TOSUN — via python-can | [HARD] |

---

## 6. Licensing Model — `IV-LIC-xxx`

| ID | Parameter | Value | Label |
|---|---|---|---|
| IV-LIC-01 | Core license (L0–L3, this repository) | Apache-2.0 — permissive, maximizes adoption, doesn't scare vendor integrators the way GPL does | [EST] |
| IV-LIC-02 | Revenue layers (L4–L5) | Commercial license, reserved — **not part of this repository** | [HARD] |
| IV-LIC-03 | Future security-layer dependency license compatibility | Gallia (Fraunhofer AISEC) is Apache-2.0 — compatible with IV-LIC-01, informing the requirement that L2's API be Gallia-compatible | [HARD] |
| IV-LIC-04 | Dependency license policy | All dependencies must be permissive (Apache-2.0/MIT/BSD) — no copyleft (GPL) dependency ships inside the distributed core product | [NEW-EST] |

---

## 7. Success Metrics / Decision Gates — `IV-KPI-xxx`

| ID | Gate | Threshold | Label |
|---|---|---|---|
| IV-KPI-01 | Validation → build | ≥3 credible "I'd use/pay for this" signals from discovery interviews **AND** 1 signed design-partner intent | [HARD] |
| IV-KPI-02 | v0.1 → paid tier (later, not this repo's target) | ≥500 engaged users **AND** a design partner using the OSS wedge in anger (in a real workflow) | [HARD] |
| IV-KPI-03 | Kill / re-aim decision point | **Month 6** (from the start of build). If the OSS wedge has <500 engaged users AND no design partner willing to pay → re-aim, don't abandon the underlying gap | [HARD] |

---

## 8. Traceability Index

| Category | ID prefix | Section |
|---|---|---|
| Business (redacted) | `IV-BUS-` | §1 |
| Target segments | `IV-SEG-` | §2 |
| Standards (day-1) | `IV-STD-D1-` | §3.1 |
| Standards (fast-follow) | `IV-STD-FF-` | §3.2 |
| Standards (later/watch) | `IV-STD-LW-` | §3.3 |
| Regulatory | `IV-REG-` | §4 |
| Hardware/OS | `IV-HW-` | §5 |
| Licensing | `IV-LIC-` | §6 |
| KPIs / gates | `IV-KPI-` | §7 |

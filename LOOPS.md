<!-- SPDX-License-Identifier: Apache-2.0 -->

# LOOPS.md — live loop backlog

The 37 work units of [`DEVELOPMENT-PLAN-L0-L3-AGENTIC.md`](DEVELOPMENT-PLAN-L0-L3-AGENTIC.md) §5,
with current status. The plan is the *specification* and does not change as work
proceeds; this file is the *state* and changes constantly. When they disagree
about what has been built, this file is right.

Each loop becomes a GitHub issue using the SPEC template (plan Appendix A)
before implementation starts. A loop with no named oracle is not ready to start.

**Status:** 🔴 not started · 🟡 in progress · 🔵 in review · ✅ closed · ⏸️ blocked

**Legend:** *Type* W=wrap P=protocol I=integration H=harden X=infrastructure
D=design · *Tier* = highest required verification tier (plan §3) ·
*It.* = estimated agent iterations, a planning signal, not a commitment.

---

## Progress

| Milestone | Loops | Closed | Status |
|---|---|---|---|
| M1 — Substrate (W0–3) | 9 | 4 | 🟡 in progress — substrate merged to `main` and CI-green (#6/#7/#8); INF-05 next |
| M2 — Core diagnostics (W3–8) | 9 | 0 | 🔴 |
| M3 — Trace & reporting (W8–12) | 6 | 0 | 🔴 |
| M4 — The CI story (W12–16) | 6 | 0 | 🔴 |
| M5 — ODX, SOVD & breadth (W16–22) | 9 | 0 | 🔴 |
| M6 — Pilot & harden (W20–26) | 2 | 0 | 🔴 |

---

## INF — Infrastructure

| ID | Goal | Type | Tier | It. | Status | Notes |
|---|---|---|---|---|---|---|
| INF-01 | Repo skeleton: `pyproject`, Apache-2.0, SPDX headers, `CONTRIBUTING`, CoC, DCO | X | T0 | 2 | ✅ | SPDX headers on every file, enforced by `tools/check_spdx.py`. Merged (#6) |
| INF-02 | CI: T0–T4 jobs incl. `vcan` bring-up + coverage ratchet + guardrails | X | T2 | 4 | ✅ | `TODO(M1)` resolved. **Verified green on a real GitHub-hosted runner** (`main`@`ec3f649`, run 31803589165) after two follow-up fixes: the `vcan` kernel module needed an explicit `linux-modules-extra` install (#7), and a leftover non-fixture `vcan_channel()` call in a test (#8) |
| INF-03 | Automated licence gate + sync corrected licence table into `docs/` | X | T1 | 3 | ✅ | `licences.toml` + gate; `docs/framework-requirements.md` corrected and FW-REQ-019 added. Merged (#6) |
| INF-04 | Fixture corpus scaffolding + provenance manifest format | X | T1 | 3 | ✅ | Format, validator, and hash-based tamper detection in place and merged (#6). Corpus itself is empty until BUS-01/INF-05 need fixtures — that's by design, not a gap |
| INF-05 | **Virtual UDS/DoIP ECU** on `vcan`, scenario-configurable, failure injection | P | T3 | 8 | 🟡 | **Highest leverage in the plan — in progress now.** Reuse evaluation done: [`docs/inf-05-simulator-reuse-evaluation.md`](docs/inf-05-simulator-reuse-evaluation.md). `lbenthins/ecu-simulator` is archived and has no failure injection → building, reusing `can-isotp`/`python-can`/`udsoncan` |
| INF-06 | `AGENTS.md` + CODEOWNERS + blast-radius config | D | T0 | 1 | 🔵 | Drafted and merged (#6). **This is a D loop — it closes on human review, not on CI**, so still formally open. `CODEOWNERS` references `@SKIFIN-IT-SERVICES/maintainers`, unverified as an actual GitHub team |
| INF-07 | Loop telemetry: iterations-to-green, human-touch, escapes | X | T1 | 3 | 🔴 | Should. This file auto-updates from CI metadata |
| INF-08 | Docs site + executable examples (doctest in CI) | X | T1 | 4 | 🔴 | Seed from `knowledge-base/05-training-labs/` |

> **INF-05 gates almost everything** (plan §6.1). Any slip there is a
> project-level risk, not a loop-level one.

## HAL — L0 Hardware Abstraction (`src/tapwright/hal/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| HAL-01 | Core `Bus` interface + capability model; config-driven backend selection | D+W | T3 | 6 | Must | 🔴 |
| HAL-02 | SocketCAN backend incl. `vcan` | W | T3 | 4 | Must | 🔴 |
| HAL-03 | `gs_usb` backend (CANable 2.0 class) | W | T3 | 5 | Must | 🔴 |
| HAL-04 | Kvaser `canlib` backend | W | T3 | 5 | Must | 🔴 |
| HAL-05 | PEAK PCANBasic backend | W | T3 | 4 | Should | 🔴 |
| HAL-06 | Vector XL backend | W | T3 | 5 | Should | 🔴 |
| HAL-07 | Capability detection + graceful degradation | H | T4 | 5 | Must | 🔴 |
| HAL-08 | LGPL isolation for `python-can` — dependency only, never vendored | X | T1 | 2 | Must | 🔴 |

> **HAL-03/04/05/06 each need a physical-hardware sign-off no agent can
> perform.** The loop closes at T3-on-`vcan`; a named human runs the same suite
> against real hardware and records the result here. This is the main
> non-parallelisable dependency in the plan.

| Backend | Hardware sign-off | Owner | Date | Result |
|---|---|---|---|---|
| gs_usb (CANable 2.0) | ⏸️ hardware not yet ordered | — | — | — |
| Kvaser (Leaf v3) | ⏸️ hardware not yet ordered | — | — | — |
| PEAK | 🔴 pending | — | — | — |
| Vector XL | 🔴 pending | — | — | — |

## BUS — L1 Bus & Measurement Core (`buses/`, `dbc_arxml/`, `trace/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| BUS-01 | DBC load + decode/encode via `cantools` | W | T4 | 5 | Must | 🔴 |
| BUS-02 | ARXML load + decode; dual-specification path (lightweight input first-class) | W | T4 | 7 | Must | 🔴 |
| BUS-03 | LDF (LIN) database support | W | T3 | 4 | Should | 🔴 |
| BUS-04 | A2L parse (read-only; no calibration write) | W | T3 | 4 | Should | 🔴 |
| BUS-05 | Trace I/O: BLF + ASC read/write | W | T4 | 6 | Must | 🔴 |
| BUS-06 | MDF4 via `asammdf`, optional extra + LGPL isolation | W | T3 | 5 | Should | 🔴 |
| BUS-07 | Restbus / cyclic-send engine, multi-node, DBC-driven cycle times | P | T4 | 8 | Must | 🔴 |
| BUS-08 | Signal-level subscribe/filter API over live traffic | I | T2 | 5 | Should | 🔴 |
| BUS-09 | Ethernet restbus basics | P | T2 | 6 | Could | 🔴 |

## DIAG — L2 Diagnostics Engine (`src/tapwright/diag/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| DIAG-01 | ISO-TP transport via `can-isotp` (MIT — verified) | W | T3 | 5 | Must | 🔴 |
| DIAG-02 | UDS client core via `udsoncan` | W | T4 | 8 | Must | 🔴 |
| DIAG-03 | DoIP transport via `doipclient` + entity discovery | W | T3 | 6 | Must | 🔴 |
| DIAG-04 | Transport-agnostic connection abstraction (SOVD-shaped) | I | T3 | 6 | Must | 🔴 |
| DIAG-05 | Interception/observer hooks — must work across a process boundary | D+I | T2 | 5 | Must | 🔴 |
| DIAG-06 | ODX/PDX read-only import → DID/routine name resolution | W | T3 | 8 | Should | 🔴 |
| DIAG-07 | SOVD client (REST/JSON, ISO 17978) | P | T3 | 8 | Should | 🔴 |
| DIAG-08 | C-10 guardrail: `0x27` mechanics only; CI scan blocks key derivation | H | T1 | 3 | Must | 🔵 landed early with the substrate (`tools/check_forbidden.py`); the deliberate red-team commit that proves CI rejects it is still owed |
| DIAG-09 | Malformed-response hardening: NRCs, timeouts, truncated frames | H | T4 | 7 | Must | 🔴 |

> **DIAG-06 has a weak oracle.** ODX semantic correctness cannot be fully
> machine-verified: the loop closes on *structural* correctness, and semantic
> spot-checks are a T5 human gate.

## RUN — L3 Test Authoring & CI Runner (`runner/`, `report/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| RUN-01 | pytest plugin: `bus`, `uds_client`, `virtual_ecu` fixtures | D+I | T2 | 6 | Must | 🔴 |
| RUN-02 | Declarative YAML test format → pytest collection | P | T3 | 8 | Should | 🔴 |
| RUN-03 | HTML report | W | T2 | 4 | Must | 🔴 |
| RUN-04 | JSON / ATX-style machine-readable report | W | T2 | 4 | Must | 🔴 |
| RUN-05 | Unified CLI — one entry point for all three invocation modes | D+I | T2 | 5 | Must | 🔴 |
| RUN-06 | GitHub Actions example + reusable composite action | X | T2 | 4 | Must | 🔴 |
| RUN-07 | GitLab CI example | X | T2 | 3 | Should | 🔴 |
| RUN-08 | Container image published alongside PyPI package | X | T2 | 4 | Must | 🔴 |
| RUN-09 | Time-to-first-green-test < 1 hour, measured on real users | D | T5 | 4 | Must | 🔴 |

> **RUN-09 is human-led by design.** Its oracle is a stopwatch and a person who
> has never seen the tool. Run it at least twice with different subjects.

---

## Loop telemetry

Populated by INF-07 once it lands. Until then, filled in by hand at each loop
close. Targets are from plan §8.

| Metric | Target | Current |
|---|---|---|
| Iterations-to-green (median, W/P/I) | ≤ 8 | — |
| Human-touch rate (W/P/I/H) | < 30% | — |
| **Escape rate** (defects found after loop close) | **< 0.2** | — |
| Oracle coverage (loops reaching declared tier) | 100% | — |
| Fixture-tamper attempts (guardrail blocks) | track, don't target | 0 |
| Blast-radius violations | → 0 | 0 |
| Time-to-first-green-test | < 1 hour | not yet measured |

Escape rate is the one that matters. Everything else measures efficiency; escape
rate measures whether the method produces correct software. Excellent
iterations-to-green alongside a climbing escape rate means loops are being
gamed and the verification ladder needs to go *deeper*, not faster.

## Open external dependencies

| Item | Blocks | Owner | Status |
|---|---|---|---|
| LGPL legal opinion (C-9) | First **public release**, not development | — | 🔴 not booked |
| PyPI name `tapwright` | Nothing yet; availability rots | — | 🔴 verified available 2026-08-14, not claimed |
| Hardware order (~$530: 2× CANable 2.0, 1× Kvaser Leaf v3) | HAL-03/04 sign-off | — | 🔴 not ordered |
| Design partner (ARAI / ICAT) | M6 | — | 🔴 outreach not started |

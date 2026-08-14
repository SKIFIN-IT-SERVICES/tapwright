<!-- SPDX-License-Identifier: Apache-2.0 -->

# INF-05 — reuse evaluation before building the virtual ECU

**Date:** 2026-08-14 · **Status:** evaluation complete, build approved
**Mandated by:** `DEVELOPMENT-PLAN-L0-L3-AGENTIC.md` §5.1 — *"Before writing a line of simulator code, spend half a day on: (a) does it cover our scenario needs? (b) what licence? (c) does it support the failure injection T4 hardening loops require?"*

C-4 ("reuse, do not rewrite") applies to our own test infrastructure, not just to shipped code. INF-05 is the highest-leverage loop in the plan and gates almost everything downstream, so the temptation to start typing immediately is exactly the one worth resisting. This records what the evaluation found.

## Candidate: [`lbenthins/ecu-simulator`](https://github.com/lbenthins/ecu-simulator)

Named in the research corpus as an existing OSS tool that "simulates vehicle diagnostic services… to test tools that support UDS (ISO 14229) and ISO-TP (ISO 15765-2)" — on its face, a large fraction of INF-05's job already written.

| Question | Finding | Verdict |
|---|---|---|
| **(b) Licence** | MIT | ✅ Compatible with an Apache-2.0 core. No obstacle |
| **(a) Scenario coverage** | Implements OBD-II services `0x01`, `0x03`, `0x09` and UDS `0x10` (DiagnosticSessionControl), `0x11` (ECUReset), `0x19` (ReadDTCInformation). Configured through a flat `ecu_config.json` — static response data (VIN, ECU name, DTCs), not scenarios | ⚠️ Partial. Missing `0x22`/`0x2E` (RDBI/WDBI) and `0x31` (RoutineControl), which DIAG-02 needs. No notion of session-dependent or sequence-dependent behaviour |
| **(c) Failure injection** | None. Happy-path responses only | ❌ **Disqualifying.** DIAG-09 and every T4 hardening loop need an ECU that returns NRCs, times out, and emits truncated and oversized frames *on demand* |
| **Maintenance** | **Archived 2023-06-02**, explicitly unmaintained: *"kept here only for reference"* | ❌ Adopting an archived project means owning it, without the benefit of having designed it |
| **ISO-TP** | Does **not** implement ISO-TP — it responds to diagnostic requests, leaving segmentation to the caller | ⚠️ The hardest part of the transport is not actually in here |

## Decision

**Take it as a reference, do not wrap or fork it.** Build INF-05, on top of libraries we are already committed to.

This is not a reflex to rewrite — the reuse question was asked seriously and the answer went the other way for a specific reason. Failure injection is not a feature INF-05 would like to have; it is most of why INF-05 exists. An ECU that only behaves correctly can verify the happy path, and the happy path is the part least likely to be wrong. The tests that matter most — DIAG-09's malformed-response hardening, HAL-07's capability-mismatch properties, every T4 loop — need an ECU that misbehaves precisely and repeatably. Retrofitting that into an archived codebase built around static JSON responses is not cheaper than building it into a design that assumed it from the start.

The archival is the second reason and would be sufficient on its own: adopting an unmaintained dependency for the component that gates the entire critical path takes on all of the maintenance with none of the design context.

**What we do reuse** — the discipline still applies, just one layer down:

| Component | Reused from | Why not ours |
|---|---|---|
| ISO-TP segmentation/reassembly | `can-isotp` (MIT — verified) | The genuinely hard, spec-dense part. `lbenthins/ecu-simulator` doesn't implement it either |
| CAN transport, `vcan` binding | `python-can` (LGPL-3.0, dependency-only per C-9) | This is L0's job, and L0 wraps `python-can` |
| Client-side UDS, for the differential oracle | `udsoncan` (MIT) | INF-05's own oracle: a `udsoncan` client used directly must talk to our simulated ECU successfully |
| Request/response semantics | ISO 14229 / 15765-2 | Published, precise, deterministic — the strongest oracle available |

What is genuinely ours is the **responder and scenario layer**: a scenario format expressing session state, per-service responses, and injected failures. That layer is small, it is the part no existing tool provides, and it is the part every downstream loop actually consumes.

**Read before implementing:** [`RemotiveBus`](https://remotivelabs.com) — a Docker network plugin doing SocketCAN-to-container bridging and inter-container `vcan`. RUN-08 hits exactly that problem, and the same people ship it to Volvo. Worth reading their approach before designing ours.

## What this implies for the INF-05 SPEC

- **Scenario format is the design surface, and it is the part to get right.** Per `DECISIONS-RECORD.md` §3 the implementation is `vcan`-only in v0.1, but the interface must stay swappable so a Renode-backed implementation can be substituted later without touching a single test.
- **Failure injection is in the first version, not a follow-up.** NRCs, timeouts, truncated frames, oversized frames. It is not a hardening extra; it is the requirement.
- **The simulator needs its own tests.** It is a load-bearing test dependency three times over — onboarding demo, CI fixture, and every loop's integration oracle. A broken simulator produces false green across the entire suite, which is worse than a broken product.
- **Its oracle is `udsoncan` used directly.** A stock `udsoncan` client, with no Tapwright code in the path, must complete a session-control and RDBI exchange against it. That keeps the simulator honest about the spec rather than merely consistent with our own client.
- **Start narrow.** UDS-over-CAN only, per the plan's own risk mitigation. DoIP extends it once the CAN path is proven.

## Sources

- [`lbenthins/ecu-simulator`](https://github.com/lbenthins/ecu-simulator) — archived 2023-06-02, MIT
- [`lbenthins/ecu-simulator` README](https://github.com/lbenthins/ecu-simulator/blob/master/README.md) — service coverage and `ecu_config.json` format
- [udsoncan documentation](https://udsoncan.readthedocs.io/en/latest/) — MIT; the client side of the differential oracle
- [`oussamagobji/Automotive-Diagnostic-Simulator`](https://github.com/oussamagobji/Automotive-Diagnostic-Simulator) — also surveyed; same gap, no failure injection
- [`iDoka/awesome-canbus`](https://github.com/iDoka/awesome-canbus) — surveyed for further candidates; none address failure injection

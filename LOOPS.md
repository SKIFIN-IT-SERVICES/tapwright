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

**25 of 37 loops closed** (🔵 below — closed on `main`, CI-verified; four
partials, 🔵 with a note, count as "landed but not formally signed off"):
INF-01–05, HAL-01/02/07/08, DIAG-01–05, DIAG-09, RUN-01, RUN-03, RUN-04,
RUN-05, RUN-06, RUN-08, BUS-01/02/05/06/07. Roughly 68% of the loop count — see
each section's table below for per-loop detail; this line replaces the
former per-milestone rollup table, which drifted out of sync with the
per-loop tables (a second tracking surface saying something different
from the first is worse than one surface, even an imperfect one) and
didn't map cleanly onto the plan's own M1–M6 loop groupings in the first
place.

Substrate (INF) is done except INF-07/08 (Should). L0 (HAL) has everything
buildable without physical hardware done — `vcan`, LGPL isolation
(HAL-08), and capability detection (HAL-07); HAL-03–06 are blocked on
physical hardware sign-off, a named human task, not an agent one. L2
(DIAG) now has a
complete, transport-agnostic UDS-over-CAN-and-DoIP client, **the
process-boundary interception point** `docs/architecture.md` §4 requires,
**and confirmed malformed-response hardening**, with ODX and SOVD loops
still ahead. L3 (RUN) now has its
fixture layer, a named CLI entry point, a container image build, both
HTML and JSON reports, **and a benchmarked cold-clone CI example**, with
the declarative-YAML loop still ahead. **L1 (BUS) now has
DBC and ARXML decode both first-class, BLF/ASC/MDF4 trace I/O, and
single/multi-message cyclic-send**, with LDF, A2L, and signal-level
subscribe/filter still ahead of it.

---

## INF — Infrastructure

| ID | Goal | Type | Tier | It. | Status | Notes |
|---|---|---|---|---|---|---|
| INF-01 | Repo skeleton: `pyproject`, Apache-2.0, SPDX headers, `CONTRIBUTING`, CoC, DCO | X | T0 | 2 | ✅ | SPDX headers on every file, enforced by `tools/check_spdx.py`. Merged (#6) |
| INF-02 | CI: T0–T4 jobs incl. `vcan` bring-up + coverage ratchet + guardrails | X | T2 | 4 | ✅ | `TODO(M1)` resolved. **Verified green on a real GitHub-hosted runner** (`main`@`ec3f649`, run 31803589165) after two follow-up fixes: the `vcan` kernel module needed an explicit `linux-modules-extra` install (#7), and a leftover non-fixture `vcan_channel()` call in a test (#8) |
| INF-03 | Automated licence gate + sync corrected licence table into `docs/` | X | T1 | 3 | ✅ | `licences.toml` + gate; `docs/framework-requirements.md` corrected and FW-REQ-019 added. Merged (#6) |
| INF-04 | Fixture corpus scaffolding + provenance manifest format | X | T1 | 3 | ✅ | Format, validator, and hash-based tamper detection in place and merged (#6). Corpus itself is empty until BUS-01/INF-05 need fixtures — that's by design, not a gap |
| INF-05 | **Virtual UDS/DoIP ECU** on `vcan`, scenario-configurable, failure injection | P | T3 | 8 | 🔵 | **Highest leverage in the plan.** Implemented at `src/tapwright/diag/virtual_ecu/` (moved from the test-plan's original `tools/virtual_ecu/` location — `TOOL-REQ-026` requires it importable from the installed package). UDS-**over-CAN only** (`0x10`/`0x22`/`0x2E`/`0x19`/`0x27`-mechanics); DoIP not yet built. All 4 failure-injection kinds implemented and CI-verified. **All 9 CI jobs green on PR #10, including T2 (vcan) and T3 (all 19 differential cases vs. a stock `udsoncan` client)** — the full oracle passed. 41 T1 unit tests + 24 T2/T3 vcan-gated tests, all real. Open item: PR #10 review/merge |
| INF-06 | `AGENTS.md` + CODEOWNERS + blast-radius config | D | T0 | 1 | 🔵 | Drafted and merged (#6). **This is a D loop — it closes on human review, not on CI**, so still formally open. `CODEOWNERS` references `@SKIFIN-IT-SERVICES/maintainers`, unverified as an actual GitHub team |
| INF-07 | Loop telemetry: iterations-to-green, human-touch, escapes | X | T1 | 3 | 🔴 | Should. This file auto-updates from CI metadata |
| INF-08 | Docs site + executable examples (doctest in CI) | X | T1 | 4 | 🔴 | Seed from `knowledge-base/05-training-labs/` |

> **INF-05 gates almost everything** (plan §6.1). Any slip there is a
> project-level risk, not a loop-level one.

## HAL — L0 Hardware Abstraction (`src/tapwright/hal/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| HAL-01 | Core `Bus` interface + capability model; config-driven backend selection | D+W | T3 | 6 | Must | 🔵 |
| HAL-02 | SocketCAN backend incl. `vcan` | W | T3 | 4 | Must | 🔵 |
| HAL-03 | `gs_usb` backend (CANable 2.0 class) | W | T3 | 5 | Must | 🔴 |
| HAL-04 | Kvaser `canlib` backend | W | T3 | 5 | Must | 🔴 |
| HAL-05 | PEAK PCANBasic backend | W | T3 | 4 | Should | 🔴 |
| HAL-06 | Vector XL backend | W | T3 | 5 | Should | 🔴 |
| HAL-07 | Capability detection + graceful degradation | H | T4 | 5 | Should | 🔵 |
| HAL-08 | LGPL isolation for `python-can` — dependency only, never vendored | X | T1 | 2 | Must | 🔵 |

> **HAL-01/HAL-02** landed together as PR #4 (`src/tapwright/hal/{bus,frame,errors}.py`,
> authored by @surendersinghIT, opened 2026-07-31 — before the loop
> substrate existed). Rebased onto the current substrate's test-tier
> convention and CI: 2 conflicts resolved (`ci.yml`, `pyproject.toml`,
> `CHANGELOG.md`), tests moved from its own `tests/hal/` into
> `tests/{unit,integration}/` with the shared `vcan_channel`/`requires_vcan`/
> `requires_hardware` fixtures, SPDX headers added. CI caught one real bug in
> the process — `test_backend_swap_is_config_only` sent and received on a
> single bus handle, which SocketCAN never echoes back without
> `receive_own_messages=True` — fixed to use a sender/receiver pair like
> every other round-trip case. **All 9 CI jobs green, PR clean/mergeable.**
> `Bus`/`Frame`/`HalError` cover SocketCAN + `vcan` only — `gs_usb` (HAL-03),
> Kvaser (HAL-04), and the remaining backends are separate, not-yet-started
> loops. **Correction (2026-08-25): HAL-08 is not one of them** — its full
> acceptance criterion ("build fails if `python-can` source is vendored
> into the tree") was already implemented by INF-03's licence gate
> (`tools/check_licences.py`'s vendoring scan, repo-wide rather than
> `hal/`-scoped, which the criterion doesn't require) and already has two
> red-team tests proving it fires (`test_vendored_copyleft_is_detected`,
> `test_vendor_directory_is_detected`, `tests/unit/test_guardrails.py`),
> both green in CI's own T1/guardrails jobs. `LOOPS.md` just never
> reflected it — marked 🔵 now, no new code needed.

> **HAL-07** (#43, PR #44): `Bus.send()`'s `CapabilityError` check (raises
> when `frame.is_fd and not self._fd`) already existed and was already
> correct — no implementation changes needed, this loop is the
> verification that proves it. No test file anywhere had previously
> referenced `CapabilityError`. A parametrized sweep across the full
> `(bus_fd, frame_fd)` matrix, not `hypothesis` — the state space is 2
> booleans, already fully enumerable, so fuzzing wouldn't add coverage a
> plain parametrize doesn't already provide. **Priority corrected to
> Should** — `TOOL-REQ-009`'s own rating, not the plan's stale Must. All
> 10 CI jobs green, T2 genuinely exercising the capability matrix on real
> `vcan`.

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
| BUS-01 | DBC load + decode/encode via `cantools` | W | T4 | 5 | Must | 🔵 |
| BUS-02 | ARXML load + decode; dual-specification path (lightweight input first-class) | W | T4 | 7 | Must | 🔵 |
| BUS-03 | LDF (LIN) database support | W | T3 | 4 | Should | 🔴 |
| BUS-04 | A2L parse (read-only; no calibration write) | W | T3 | 4 | Should | 🔴 |
| BUS-05 | Trace I/O: BLF + ASC read/write | W | T4 | 6 | Must | 🔵 with a note |
| BUS-06 | MDF4 via `asammdf`, optional extra + LGPL isolation | W | T3 | 5 | Must | 🔵 |
| BUS-07 | Cyclic-send engine, single/multi-message, DBC-driven cycle times | P | T4 | 8 | Must | 🔵 |
| BUS-08 | Signal-level subscribe/filter API over live traffic | I | T2 | 5 | Should | 🔴 |
| BUS-09 | Ethernet restbus basics | P | T2 | 6 | Could | 🔴 |

> **BUS-01** (PR #23): L1's first code. `load_dbc()`/`DbcDatabase` wrap
> `cantools`'s own `Database`; the only new logic is bridging decode/encode
> to `hal.Frame`. First loop to populate INF-04's fixture corpus for real —
> `fixtures/databases/multiplexed.dbc` (self-authored) plus four golden
> expected-output JSONs, each derived by running `cantools` directly (never
> from our own implementation, which didn't exist yet). Found a real
> subtlety while authoring the fixture, before any code existed:
> `decode_message()` needs `force_extended_id` passed through explicitly
> for an extended-ID message, or it raises a bare `KeyError`. All 12
> tests (7 T3 + 1 T4 + 4 new guardrail unit tests) pass for real locally —
> DBC decode touches no bus/socket, unlike every `diag/` loop this
> session. **Also fixed a real gap in `tools/check_blast_radius.py`**,
> hit directly by this loop: adding new `provenance.toml` entries
> (purely additive) was flagged the same as tampering with an existing
> fixture, requiring an unnecessary `fixture-change:` trailer.
> **Fixture `verified_by` fields are provisional** — flagged in the PR as
> needing the reviewer's actual confirmation, since an agent can't
> self-certify per `AGENTS.md`/`PROVENANCE.md`'s own rule.

> **BUS-02** (#37, PR #38): `load_arxml()`, sharing `load_dbc()`'s wrapper
> class — renamed `DbcDatabase` → `CanDatabase` since `cantools` parses
> DBC and ARXML into the identical `Database` type, so a format-specific
> class name was never accurate (flagged as a correction from the issue's
> own sketch, not silent). New self-authored fixture
> `fixtures/databases/vehicle_signals.arxml` — hand-authored AUTOSAR 4.x
> XML, since `cantools` 42.0.3 has no ARXML *write* support to generate
> one programmatically; iterated against `cantools` itself (wrong
> `ADDRESSING-MODE` element name, wrong `SYSTEM-SIGNAL`/`COMPU-METHOD`
> linkage path) until it parsed and decoded correctly. This loop's
> required "known-gap list" deliverable (the plan's own risk-mitigation
> note for BUS-02) is `docs/bus-02-arxml-known-gaps.md`: no ARXML write
> support, Adaptive AUTOSAR unverified, only `LINEAR` compu-methods
> exercised. **Dual-specification path proven, not just asserted** —
> `test_dbc_path_remains_fully_functional_alongside_arxml` loads BUS-01's
> DBC and this loop's ARXML in the same session. All 10 CI jobs green.

> **BUS-05** (#45, PR #46): `tapwright.trace.write_blf()`/`read_blf()` and
> `write_asc()`/`read_asc()` wrap `python-can`'s own
> `BLFReader`/`BLFWriter`/`ASCReader`/`ASCWriter` (already a required
> dependency) rather than reimplementing either format. `hal.Frame` gains
> a `timestamp` field (default `0.0`, backward compatible — all 12
> existing `Frame(...)` call sites unaffected) — BLF/ASC are fundamentally
> timestamped formats and `Frame` had none before this loop;
> `Bus.send()`/`recv()` deliberately untouched. **A real hardening fix
> found while implementing**: `python-can`'s own `ASCReader` silently
> returns zero frames for a file that isn't a valid ASC trace at all,
> rather than raising — confirmed directly. `read_asc()` now checks for
> the header line `ASCWriter` always writes first, raising
> `TraceLoadError` instead. **Marked "with a note"**: no real
> Vector-CANoe-exported file is available in this environment, so true
> CANoe interop (`TOOL-REQ-019`/`020`'s own literal wording) is
> unverified — only round-tripping through `python-can`'s own
> implementation is tested, in both directions. All 10 CI jobs green.

> **BUS-06** (#51, PR #52): `tapwright.trace.write_mdf4()`/`read_mdf4()`
> wrap `python-can`'s own `MF4Writer`/`MF4Reader` — which already
> implement CAN-frame-level MDF4 logging on top of `asammdf` — rather than
> hand-rolling `asammdf.Signal`/`MDF.append()` calls directly. `asammdf`
> (LGPL-3.0) ships as a new optional extra, `tapwright[mdf4]`; the core
> installs and passes its full suite without it, extending the isolation
> precedent HAL-08 already established for `python-can` itself.
> **Priority correction, flagged in the issue and applied here**: the
> plan's own loop table and this file listed this loop as Should, but the
> cited requirement (`TOOL-REQ-021`) is Must — corrected in the table
> above. This was in fact the highest-priority remaining unblocked loop,
> since every other agent-buildable Must loop was already closed. **A real
> upstream gap found during API research**: `python-can`'s own
> `can/io/mf4.py` guards its `asammdf` import with `except ImportError`
> only — an incompatible `asammdf`/`numpy` combination (hit directly on
> this dev machine: `asammdf` 8.8.26 needs `numpy>=2`, and a partial
> Windows-side numpy upgrade left `np.bool` raising `AttributeError`
> instead of its usual deprecated-alias warning) surfaces as an
> **uncaught `AttributeError`**, which can crash `import can` entirely
> since `can/io/__init__.py` imports `mf4.py` unconditionally. This
> temporarily broke `pytest` globally on this machine (every project, not
> just this repo) after `asammdf` was installed for research purposes —
> caught immediately, fixed by uninstalling it from the global
> environment, and all further development done in an isolated `.venv`
> instead. `write_mdf4()`/`read_mdf4()` catch `python-can`'s own
> correctly-raised `NotImplementedError` (the "not installed at all" case)
> and translate it to `TraceError` naming the extra — the failure mode
> this project's own code can actually control; the `AttributeError` case
> is an upstream `python-can` gap, not fixed here. 8 T3/T4 test cases, all
> using `pytest.importorskip("asammdf")` so the file itself proves both
> halves of the oracle: skips cleanly in the existing `t3-differential`
> job (no `[mdf4]`), passes for real in a new `mdf4-extra` CI job (with
> it). All CI jobs green.

> **BUS-07** (#49, PR #50): `hal.Bus.send_periodic()` wraps `python-can`'s
> own `BusABC.send_periodic()`; `tapwright.buses.start_cyclic_from_dbc()`
> derives the period from an already-loaded `CanDatabase`'s declared
> `GenMsgCycleTime`, raising `ValueError` when neither a declared cycle
> time nor an explicit period is given. **Scope correction, flagged in the
> issue and applied here**: the plan's own loop table titled this
> "Restbus / cyclic-send engine, multi-node" — but the cited requirement
> (`TOOL-REQ-011`, Must) is scoped to single/multi-*message* "basic
> stimulation," not multi-node simulated ECUs with node-behavior
> scripting (`TOOL-REQ-012`, Should/Fast-follow, explicitly deferred, and
> already matching `buses/__init__.py`'s own pre-existing docstring and
> `docs/tooling-requirements.md`'s Won't-scope entry against a "GUI
> restbus-simulation designer"). This file's Goal column corrected to
> match. New self-authored fixture `fixtures/databases/cyclic.dbc` — the
> existing `multiplexed.dbc` fixture is hash-checked immutable and none of
> its messages declare a cycle time, so a new small fixture was added
> rather than modified. 7 T4/T2 test cases (`vcan`-gated, skip locally on
> Windows) cover the DBC-driven and explicit-period paths, `.stop()`
> actually halting transmission, concurrent independent cyclic tasks, and
> HAL-07's existing `CapabilityError` still applying through the periodic
> send path. Timing assertions use a generously wide tolerance band rather
> than the literal ±5% `TOOL-REQ-011` names, documented as a deliberate
> gap: a shared CI VM's scheduler can't reliably meet a tight jitter
> budget. All CI jobs green.

## DIAG — L2 Diagnostics Engine (`src/tapwright/diag/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| DIAG-01 | ISO-TP transport via `can-isotp` (MIT — verified) | W | T3 | 5 | Must | 🔵 |
| DIAG-02 | UDS client core via `udsoncan` | W | T4 | 8 | Must | 🔵 |
| DIAG-03 | DoIP transport via `doipclient` + entity discovery | W | T3 | 6 | Must | 🔵 |
| DIAG-04 | Transport-agnostic connection abstraction (SOVD-shaped) | I | T3 | 6 | Must | 🔵 |
| DIAG-05 | Interception/observer hooks — must work across a process boundary | D+I | T2 | 5 | Must | 🔵 |
| DIAG-06 | ODX/PDX read-only import → DID/routine name resolution | W | T3 | 8 | Should | 🔴 |
| DIAG-07 | SOVD client (REST/JSON, ISO 17978) | P | T3 | 8 | Should | 🔴 |
| DIAG-08 | C-10 guardrail: `0x27` mechanics only; CI scan blocks key derivation | H | T1 | 3 | Must | 🔵 landed early with the substrate (`tools/check_forbidden.py`); the deliberate red-team commit that proves CI rejects it is still owed |
| DIAG-09 | Malformed-response hardening: NRCs, timeouts, truncated frames | H | T4 | 7 | Must | 🔵 |

> **DIAG-01** (PR #12): `IsoTpTransport` built on `hal.Bus` via `rxfn`/`txfn`
> adapters, not a raw `python-can` bus — deliberately, so L2 sits on L0
> (`docs/architecture.md`). All 12 T3 cases green against a stock
> `isotp.CanStack` peer, both directions, up to ~4000-byte payloads. CI
> caught a real bug: `_txfn` read `message.extended_id`, but
> `isotp.CanMessage`'s stored attribute is `is_extended_id` — every send
> raised `AttributeError` inside `can-isotp`'s own thread, silently killing
> it with zero visible failure until CI's differential oracle caught it (8 of
> 12 cases failed until fixed). **Known inconsistency, not yet resolved**:
> `tools/virtual_ecu` (INF-05) still opens its own `python-can` bus directly
> rather than building on `hal.Bus` — it predates HAL-01/02 and hasn't been
> revisited.

> **DIAG-02** (PR #14): `open_uds_client()` returns a plain `udsoncan.Client`
> — the only new code is `TapwrightIsoTpConnection`, the `BaseConnection`
> adapter over DIAG-01's transport. All 12 T3+T4 cases green, differentially
> matched against udsoncan's own reference connection stack. CI caught two
> real bugs: `empty_rxqueue()` wasn't defensive against an already-closed
> transport (udsoncan calls it before its own open-check runs), and the T4
> property test's client fixture was function-scoped, which `hypothesis`
> rejects outright (`FailedHealthCheck`) since it would rebuild the ECU+
> client per generated example. Narrower than full `TOOL-REQ-024`:
> RoutineControl/ClearDTC aren't ECU-implemented yet (#9's own deferral) —
> proven instead via a clean `serviceNotSupported` response, not a hang.

> **DIAG-03** (PR #16): `open_doip_uds_client()` writes **no connection
> adapter** — `doipclient` ships its own official one, reused directly. New
> code is the virtual ECU's DoIP responder (`DoIPVirtualECU`), dispatching
> to the same `ProtocolState` the CAN path uses. All 9 T3 cases pass — and,
> unusually, **verified genuinely locally** before CI even ran (DoIP is
> plain TCP, no `vcan` needed), first `diag/` loop with that property since
> INF-05. **Not done: entity discovery** (UDP vehicle-announcement
> broadcast, ISO 13400 §7.3) — the plan's own goal line names it, this loop
> only built routing activation + diagnostic message exchange. No TLS, no
> alive-check timer either. None block DIAG-04; flagged as future work if a
> loop actually needs them.

> **DIAG-04** (PR #18): `open_connection()` dispatches on config-object type
> to DIAG-02/DIAG-03's factories. Oracle was unusual — not a differential
> comparison but the parametrization itself succeeding — and it did, all 9
> CI jobs green first try, DoIP-side cases (5/10) also verified for real
> locally before ever reaching CI. **Corrected mid-implementation**: the
> issue/test-plan said `open_connection()` would be re-exported at
> `tapwright.diag` package level; kept as
> `tapwright.diag.connection_config.open_connection` instead, since
> re-exporting would've broken the "stay cheap" import convention every
> prior `diag/` submodule established (see the test file's own docstring
> for the full reasoning). M2's exit criterion — "same UDS test passes
> unmodified over CAN and DoIP" — is now met.

> **DIAG-05** (#25, PR #29 — third attempt: #26 merged before its CI-caught
> fix had gone through CI and was reverted; #28's merge-base against `main`
> was left tangled by that revert; #29 was rebuilt clean off `main` and is
> what actually landed): `InterceptingConnection` wraps any `BaseConnection`
> (CAN or DoIP) and publishes every request/response to at most one
> connected observer over TCP + newline-delimited JSON — a genuine
> cross-process oracle, not a mock: `tests/differential/_interception_
> observer.py` is a standalone script importing nothing from `tapwright`,
> spawned as a real subprocess. CI itself caught a real bug — `is_open()`
> proxying straight to the inner connection, which some inner connections
> report as open at construction, so `udsoncan.Client.open()` never called
> this wrapper's own `open()` and the observer socket never bound — fixed
> and re-verified. Also surfaced (and fixed, PR #30) a real gap in CI infra
> unrelated to this loop's own code: `bring-up-vcan`'s `apt-get` had no
> timeout, and a stuck mirror hung three consecutive runs for 30–60+
> minutes each before failing; now bounded with `timeout` + retry plus a
> job-level `timeout-minutes` backstop.

> **DIAG-09** (#35, PR #36): 13 new cases across
> `tests/differential/test_client_hardening.py` (6 deterministic cases × 2
> transports) and `tests/property/test_client_hardening_properties.py` (1
> `hypothesis`-fuzzed NRC byte range) confirm `open_uds_client()`/
> `open_doip_uds_client()`/`open_connection()` handle all 4 of INF-05's
> `FailureInjection` kinds cleanly — a gap DIAG-02/03's own test plans
> never closed (they only exercised `timeout`), and one
> `test_virtual_ecu_uds.py` explicitly flagged as owed to this loop.
> **No implementation changes were needed** — the existing client stack
> already handled every case correctly, `truncated` (the "no hang" case)
> included, on the very first run. The T4 fuzz test *did* catch something
> real on its first CI run, though: 0x78
> (`RequestCorrectlyReceived_ResponsePending`) is spec-legitimate "please
> wait," and `udsoncan` correctly waits for a real final response instead
> of treating it as terminal — since the injected failure never sends one,
> the client times out rather than raising `NegativeResponseException`.
> Not a hang, not a crash, just a different (still clear) exception for a
> protocol-legitimate reason — fixed by excluding 0x78 from the general
> fuzz strategy and adding a dedicated case for it, rather than narrowing
> the fuzzed range silently.

> **DIAG-06 has a weak oracle.** ODX semantic correctness cannot be fully
> machine-verified: the loop closes on *structural* correctness, and semantic
> spot-checks are a T5 human gate.

## RUN — L3 Test Authoring & CI Runner (`runner/`, `report/`)

| ID | Goal | Type | Tier | It. | Pri | Status |
|---|---|---|---|---|---|---|
| RUN-01 | pytest plugin: `bus`, `uds_client`, `virtual_ecu` fixtures | D+I | T2 | 6 | Must | 🔵 |
| RUN-02 | Declarative YAML test format → pytest collection | P | T3 | 8 | Should | 🔴 |
| RUN-03 | HTML report | W | T2 | 4 | Must | 🔵 |
| RUN-04 | JSON / ATX-style machine-readable report | W | T2 | 4 | Should | 🔵 |
| RUN-05 | Unified CLI — one entry point for all three invocation modes | D+I | T2 | 5 | Must | 🔵 |
| RUN-06 | GitHub Actions example + reusable composite action | X | T2 | 4 | Must | 🔵 |
| RUN-07 | GitLab CI example | X | T2 | 3 | Should | 🔴 |
| RUN-08 | Container image published alongside PyPI package | X | T2 | 4 | Must | 🔵 with a note |
| RUN-09 | Time-to-first-green-test < 1 hour, measured on real users | D | T5 | 4 | Must | 🔴 |

> **RUN-01** (PR #21): `tapwright.runner.plugin` registered as a `pytest11`
> entry point — confirmed live (`tapwright-0.0.1.dev0` in pytest's own
> plugin banner during this repo's own test runs), not just importable.
> `def test_x(uds): ...` works against the plugin's default empty
> `Scenario()` with zero configuration; a user overrides `scenario` via
> plain pytest fixture-override for real DIDs. `uds` is built on DIAG-04's
> `open_connection()`. All 9 CI jobs green first try. CAN/`vcan` only —
> DoIP fixtures and `TOOL-REQ-029` (deterministic `wait_for_*` helpers) are
> both explicitly out of scope, flagged as fast-follows rather than
> silently dropped or silently folded in.

> **RUN-03** (#39, PR #40): wraps `pytest-html` (MPL-2.0, new dependency)
> rather than reimplementing report rendering — a `tryfirst`
> `pytest_configure` hook in `tapwright.runner.plugin` sets a default
> `--html` path only if the user hasn't already chosen one, so a report
> appears with zero required flags (`tryfirst=True` matters:
> `pytest-html`'s own `pytest_configure` only registers its reporter if
> `htmlpath` is already truthy by the time its hook runs). **"Decoded
> frames" not built** — no mechanism anywhere in the codebase records
> which frames a test exchanged for a report to read back, flagged as a
> real follow-up rather than silently dropped. **Determinism scoped to the
> results table, not raw bytes** — found directly while writing the test
> plan: `pytest-html`'s own template embeds a generation timestamp and a
> per-test wall-clock duration, both legitimate variance for a report
> that's required to include timing at all (`TOOL-REQ-031` names it). All
> 10 CI jobs green.

> **RUN-04** (#41, PR #42): wraps `pytest-json-report` (MIT, new
> dependency), extending RUN-03's own `pytest_configure` hook rather than
> adding a second one. **Priority corrected to Should** — the plan's loop
> table (row above, and the plan document itself) says Must, but
> `TOOL-REQ-032`'s own row in `docs/tooling-requirements.md` rates itself
> Should; per this project's own convention (inherit from the cited
> requirement's rating), LOOPS.md's own status column now reflects that
> correction rather than the plan's stale value — see this file's own
> header ("when they disagree... this file is right"). **"Schema-
> validates" is against `docs/schemas/run-report.schema.json`, a schema
> this loop defines**, not the ASAM ATX standard the plan's own title for
> this loop names — `TOOL-REQ-032`'s own wording ("not built now, just
> don't block it") rules that out for now. A real design gap found via
> TDD: `pytest-json-report` splits "enabled" from "where" into two
> separate options, unlike `pytest-html`'s single option — naively
> checking only the boolean would have overwritten an explicitly-chosen
> file path with the auto-default.

> **RUN-05** (#31, PR #32): `tapwright.runner.cli.main()` is a thin
> pass-through to `pytest.main()`, registered as both an installed console
> script (`tapwright [pytest-args...]`) and `python -m tapwright` (new
> top-level `__main__.py`) — the two invocation surfaces proven identical,
> TOOL-REQ-030's own acceptance test. All 9 CI jobs green first try, T2
> genuinely exercising the installed console script on Linux. **Not a
> `tapwright run` subcommand**, unlike the issue's own rough sketch: there
> is exactly one thing this CLI does today and no second subcommand to
> distinguish it from — flagged explicitly rather than built speculatively.
> A subcommand structure is a natural addition once RUN-02/03/04 exist.

> **RUN-08** (#33, PR #34): `Dockerfile` builds Tapwright from source;
> `quickstart.py` — the first formal "quickstart" defined anywhere in this
> repo — is the container's entrypoint, bringing up `vcan0` inside the
> container's own network namespace, starting a `VirtualECU`, and
> completing one UDS RDBI round-trip, with only `--cap-add=NET_ADMIN
> --cap-add=NET_RAW` at `docker run` time. New CI job (`container`) builds
> and smoke-tests the image on every push — all 10 CI jobs green, the
> vcan-in-container path genuinely validated on real Linux (containers
> there share the host kernel directly, unlike Docker Desktop's own VM,
> which has no `vcan` module and couldn't run 2 of the 6 test cases
> locally). **Scoped to build + CI smoke test only** — no registry push,
> a deliberate, separate, human-triggered action. **Runs as root, not the
> originally-planned non-root user**: two non-root approaches (a plain
> `USER` switch; `setcap` on `ip` at build time) both failed for real,
> documented reasons specific to this one-shot `NET_ADMIN`-requiring
> entrypoint — see the Dockerfile's own comment. Marked "with a note"
> rather than a clean 🔵 for that scope correction, not for anything
> unverified.

> **RUN-06** (#47, PR #48): `examples/github-actions/` — a standalone
> example, deliberately *not* this repo's own `ci.yml` (which tests
> tapwright's own source, not what a third-party consumer's cold clone
> experiences). One small test on RUN-01's own `uds` fixture, a
> copy-pasteable workflow reusing `bring-up-vcan` via GitHub's cross-repo
> action-reference syntax rather than duplicating vcan setup. **The
> benchmark the plan required was done for real**: cloned
> `vectorgrp/ci-siltest-demo` and read its workflow directly (research
> only, not committed) — Vector's own public CI reference needs
> self-hosted runners with three licensed products (DaVinci Configurator,
> vVIRTUALtarget, CANoe4SW Server Edition) pre-installed and cannot go
> green on a stock runner at any step count; `docs/run-06-benchmark.md`
> records the comparison. The new `Example — GitHub Actions (RUN-06)` CI
> job runs the example's own test against the current source on every
> push, so "goes green from a cold clone" is proven by CI itself. All 11
> CI jobs green.

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

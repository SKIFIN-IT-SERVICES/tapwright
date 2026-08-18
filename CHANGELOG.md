# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/) once a `0.1.0` is tagged.

## [Unreleased]

### Added

- **DBC ingestion + symbolic decode via `cantools`** (BUS-01, `TOOL-REQ-014`;
  #22): `tapwright.dbc_arxml.load_dbc()`/`DbcDatabase` wrap `cantools`'s own
  `Database`, bridging decode/encode to `tapwright.hal.Frame` directly —
  L1's first code, and the first loop to populate INF-04's fixture corpus
  for real (`fixtures/databases/multiplexed.dbc`, self-authored, plus four
  golden expected-output JSON files). `decode_message()` needs
  `force_extended_id` passed through explicitly for extended-ID
  messages — found while authoring the fixture, before the implementation
  existed, and recorded in the fixture's own notes. Also fixes a real gap
  in `tools/check_blast_radius.py`: adding new `provenance.toml` entries
  was incorrectly flagged the same as tampering with an existing fixture.
- **pytest-native plugin: `ecu`/`bus`/`uds` fixtures** (RUN-01,
  `TOOL-REQ-028`; #20): `tapwright.runner.plugin`, registered as a
  `pytest11` entry point — auto-discovered on `pip install tapwright`, no
  `pytest_plugins = [...]` needed. `def test_x(uds): ...` works with zero
  configuration (an empty default `Scenario`); a user overrides the
  `scenario` fixture in their own test file to configure DIDs. `uds` is
  built on DIAG-04's `open_connection()`, inheriting its transport-agnostic
  properties. CAN/`vcan` only in this pass — DoIP fixtures are a
  fast-follow. `TOOL-REQ-029` (deterministic `wait_for_*` helpers) is a
  separate requirement, not built here.
- **Transport-agnostic connection abstraction** (DIAG-04, #17):
  `tapwright.diag.connection_config.open_connection()` — a single
  construction-time choice (`CanConnectionConfig` vs. `DoipConnectionConfig`,
  dispatched by type) between DIAG-02's and DIAG-03's client factories,
  both returning the same `udsoncan.Client` type. Verified with one literal
  test body run unmodified over both transports — the "invisible to the
  calling code" property `docs/architecture.md` §4 requires, demonstrated
  rather than argued. Shaped so a future `SovdConnectionConfig` (DIAG-07)
  slots into the same dispatch.
- **DoIP transport** (DIAG-03, `TOOL-REQ-023`; #15): `open_doip_uds_client()`
  — the DoIP-transport twin of DIAG-02's `open_uds_client()`, returning the
  same `udsoncan.Client` type. Writes no connection adapter of its own:
  `doipclient` ships an official `udsoncan.connections.BaseConnection`
  implementation, reused directly. The new work is the virtual ECU's DoIP
  responder (`tapwright.diag.virtual_ecu.DoIPVirtualECU`), which dispatches
  to the *same* `ProtocolState` the CAN-side responder uses — one set of
  UDS service logic, two transports. `doipclient` becomes a runtime
  dependency. First `diag/` loop verified with genuine local red/green
  TDD since INF-05 (DoIP is plain TCP, no `vcan` needed).
- **UDS client core via `udsoncan`** (DIAG-02, `TOOL-REQ-022` client half /
  `TOOL-REQ-024`; #13): `tapwright.diag.connection.TapwrightIsoTpConnection`
  — a `udsoncan.connections.BaseConnection` adapter over DIAG-01's
  `IsoTpTransport` — and `tapwright.diag.uds_client.open_uds_client()`, the
  transport-agnostic construction point `docs/architecture.md` §4 requires:
  it returns a plain `udsoncan.Client`, so every service the library already
  implements (RDBI, WDBI, DTC read, RoutineControl, SecurityAccess, session
  control, ...) works through our transport with no service-level code of
  our own, per `AGENTS.md`'s reuse rule. Verified byte-identical to
  udsoncan's own reference connection stack across happy-path, multi-frame,
  and error cases, plus a `hypothesis`-driven property test across
  arbitrary DID value lengths.
- **ISO-TP transport over `hal.Bus`** (DIAG-01, `TOOL-REQ-022` transport
  half; #11): `tapwright.diag.isotp_transport.IsoTpTransport` wraps
  `can-isotp`'s `isotp.TransportLayer`, bridged to `tapwright.hal.Bus` via
  `rxfn`/`txfn` adapters rather than opening its own `python-can` bus — L2
  built on L0, per `docs/architecture.md`'s layering. Multi-frame
  segmentation/reassembly verified byte-identical to a stock
  `isotp.CanStack` peer, both directions, up to ~4000-byte payloads;
  out-of-sequence Consecutive Frames surface as `TransportProtocolError`
  rather than a silently wrong reassembly. `tapwright.diag.errors` adds the
  `DiagError` hierarchy, mirroring `hal.errors`' convention.
- **HAL: `Bus` abstraction + SocketCAN/`vcan` backend** (HAL-01/HAL-02,
  `TOOL-REQ-001` partial, `TOOL-REQ-002`, `TOOL-REQ-008`, `TOOL-REQ-009`,
  `TOOL-REQ-010`; #3): `open_bus()` + `Bus` over SocketCAN (real interfaces
  and `vcan`), `Frame`, and a typed `HalError` hierarchy so invalid config
  and lifecycle misuse raise clear errors rather than bare exceptions from
  inside `python-can`. CAN-FD capability is checked explicitly — an FD send
  on a classic-CAN-only bus raises rather than failing silently.
- **Virtual UDS ECU responder** (INF-05, `TOOL-REQ-026`):
  `tapwright.diag.virtual_ecu` — a scenario-configurable UDS-over-ISO-TP
  responder on `vcan`, ships as part of the installed package so a
  `pip install`-only user can run a read-DID round trip with zero hardware.
  Session control (`0x10`), RDBI/WDBI (`0x22`/`0x2E`), ReadDTCInformation
  (`0x19`), and SecurityAccess mechanics (`0x27` — request-seed/send-key
  only, never derivation, per C-10). Failure injection (NRC override,
  timeout, truncated frame, oversized response) built in from the start,
  which is the reason it exists rather than wrapping the archived
  `lbenthins/ecu-simulator` (see
  `docs/inf-05-simulator-reuse-evaluation.md`). `python-can`, `can-isotp`,
  and `udsoncan` become the project's first real runtime dependencies.
- **Agent contract and loop backlog** (INF-06): `AGENTS.md` states the
  invariants that hold in every step of the development loop — the reuse rule,
  the oracle rule, the forbidden list, and the escalation protocol. `CODEOWNERS`
  protects `fixtures/` and the guardrails themselves. `LOOPS.md` tracks all 37
  work units and their status.
- **Verification ladder in CI** (INF-02): `ci.yml` now splits into T0 static /
  T1 unit / T2 integration / T3 differential / T4 property jobs, brings up
  `vcan` on the runner (resolving the standing `TODO(M1)`), and adds a
  coverage-ratchet job and a `guardrails` job. `tests/` gains the matching
  tier directories.
- **Guardrails** (`tools/`): SPDX header check, dependency-licence gate,
  fixture integrity and provenance check, forbidden-capability scan (C-10,
  DIAG-08), blast-radius and `fixture-change:` trailer check, and the
  coverage ratchet (85% line / 75% branch on L0–L2). All wired into both
  pre-commit and CI, and all covered by tests.
- **Fixture corpus scaffolding** (INF-04): `fixtures/` with a provenance
  manifest format and `PROVENANCE.md` documenting sourcing rules — no
  OEM-proprietary data, expected outputs human-verified at creation and never
  regenerated to match code.
- **Dependency licence manifest** (INF-03): `licences.toml`, machine-enforced,
  recording a verification date for every dependency.
- SPDX headers on all existing source files, completing INF-01.

### Changed

- `PROCESS.md`: step 2 now requires naming the **oracle** — the independently
  authored authority that decides correctness — plus the verification tier and
  blast radius. Step 3 adds the **fixture-immutability** rule. Step 4 requires
  that the reviewer did not supervise the work under review.
- `docs/framework-requirements.md`: corrected the dependency licence table.
  **`python-can` is LGPL-3.0, not BSD-2-Clause; `can-isotp` is MIT, not
  LGPL-3.0** — both were estimates and both were wrong. Added FW-REQ-019 (the
  LGPL isolation boundary) and set FW-REQ-032's coverage target.

### Fixed

- Nothing yet — no functional code has shipped.

---

- Repository scaffolding: `LICENSE` (Apache-2.0), `NOTICE`, `README.md`,
  `ARCHITECTURE.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`.
- Packaging skeleton (`pyproject.toml`, `src/` layout) and CI workflow.
- Module skeleton for `buses/`, `dbc_arxml/`, `diag/`, `runner/`,
  `report/`, `trace/` — no functional code yet.

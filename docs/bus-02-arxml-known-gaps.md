# BUS-02 — ARXML known-gap list

<!-- SPDX-License-Identifier: Apache-2.0 -->

Per the plan's own risk-mitigation note for BUS-02 ("`cantools` ARXML depth
gaps block BUS-02 — mitigation: documented known-gap list, upstream
contributions rather than a fork, narrow v0.1 ARXML claims honestly"). This
is that list — written from what authoring `fixtures/databases/
vehicle_signals.arxml` and reading `cantools`' own ARXML loader
(`cantools.database.can.formats.arxml`) surfaced directly, not a
speculative survey of the AUTOSAR spec.

`tapwright.dbc_arxml.load_arxml()` is a thin wrapper around
`cantools.database.load_file()` — per `AGENTS.md`'s reuse rule, gaps here
are `cantools`' own depth limits, not something this loop reimplements
around. Where a gap blocks a real user, the right fix is an upstream
`cantools` contribution, not a fork.

## What works (verified against this loop's own fixture and test suite)

- Classic AUTOSAR 4.x `CAN-CLUSTER` / `CAN-FRAME-TRIGGERING` / `CAN-FRAME`
  → `I-SIGNAL-I-PDU` → `I-SIGNAL` → `SYSTEM-SIGNAL` reference chains
- Standard (11-bit) and extended (29-bit) arbitration IDs
  (`CAN-ADDRESSING-MODE`)
- `LINEAR` `COMPU-METHOD`s (`COMPU-RATIONAL-COEFFS`), including negative
  offsets
- Multiple messages, multiple signals per message, correct byte-position
  packing (`START-POSITION` / `PACKING-BYTE-ORDER`)

Multiplexed-signal decode is **not** re-tested per-format here: BUS-01's
own `multiplexed.dbc` suite already proves multiplex decode works once
`cantools` has parsed *any* format into its common `Database`
representation, which this loop's ARXML path shares completely
(`test_dbc_path_remains_fully_functional_alongside_arxml` proves both
paths produce that same shared representation in the same session). A
per-format multiplex fixture would be re-testing `cantools`' parser, not
this loop's own (thin) wrapper.

## Known gaps

- **No ARXML *write* support.** `cantools.database.dump_file()` does not
  support `database_format="arxml"` in the version this project depends
  on (42.0.3) — confirmed directly while attempting to generate this
  loop's own fixture programmatically (`cantools.database.errors.Error:
  Unsupported output database format 'arxml'`), which is why
  `vehicle_signals.arxml` was hand-authored as raw XML instead. `TOOL-REQ-
  015` only requires read/ingestion, so this doesn't block v0.1's own
  claims, but it does mean `tapwright.dbc_arxml` has no ARXML-encode path
  at all — `CanDatabase.encode()` works (proven by
  `test_encode_round_trips_through_decode`) because encoding a *frame*
  from an already-loaded database is unrelated to dumping a *database*
  back out as ARXML source.
- **Adaptive AUTOSAR (service-oriented, SOME/IP-based) communication
  matrices are out of scope for this loop and likely underserved by
  `cantools` itself.** `cantools`' ARXML loader targets Classic AUTOSAR's
  CAN communication matrix (the `CAN-CLUSTER`/`I-SIGNAL` object model this
  loop's fixture exercises); nothing in this loop's own testing touched
  Adaptive AUTOSAR's service/event-based descriptions. `TOOL-REQ-015`
  names "Classic + Adaptive" — Adaptive is not verified working and should
  not be claimed as supported until a real Adaptive ARXML sample has been
  tried against it.
- **ARXML schema-variant coverage is unverified beyond AUTOSAR 4.x
  "System Description"-shaped documents.** Real OEM tool exports (DaVinci,
  PREEvision, System Desk) sometimes emit ECU Extract-only ARXML (a
  narrower slice of the same schema, missing top-level `SYSTEM`/cluster
  elements this loop's fixture includes) or AUTOSAR 3.x-family schemas.
  Neither was tried here. If a real user's ARXML fails to load, checking
  which of these two categories it falls into is the first diagnostic
  step before assuming a `tapwright` bug.
- **Non-`LINEAR` `COMPU-METHOD` categories** (`TEXTTABLE`,
  `SCALE_LINEAR_AND_TEXTTABLE`, `IDENTICAL`) are supported by `cantools`'
  own loader (per its source) but untested by this loop's fixture, which
  only exercises `LINEAR`. Believed to work (same underlying
  `Database`/`Signal` representation DBC's own text-table/choices support
  already uses, per BUS-01), but not proven the way `LINEAR` now is.

## What this means for the v0.1 claim

"ARXML ingestion (Classic)" — verified, narrowly, for the object-model
shape this loop's fixture and CI actually exercise. "+ Adaptive" (as
`TOOL-REQ-015` states) is **not** yet verified and should not be
represented as working in user-facing docs until a real Adaptive sample is
tried. This is the "narrow v0.1 ARXML claims honestly" half of the plan's
own risk mitigation, applied.

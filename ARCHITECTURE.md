# Architecture

## Guiding principle

> **One engine. Laptop, headless Linux bench, and CI container are three
> ways of invoking the same package — never three separate products.**

This is the single most important design constraint in the project. It
exists because the tools Tapwright is positioned against don't follow it:
Vector CANoe ships as a Desktop Edition and a separately-licensed Server
Edition; getting one automated HIL loop out of dSPACE's toolchain can mean
four or more separately-licensed products. Tapwright's bet is that a
CI-native tool should be CI-native by construction, not by a second SKU
bolted on later.

## Layered module map

```
┌──────────────────────────────────────────────────────────────────┐
│  L5  Compliance & orchestration        — NOT IN THIS REPO          │
│  L4  Security testing (fuzzing, etc.)  — NOT IN THIS REPO          │
╞══════════════════ everything below this line is L0-L3 ════════════╡
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

**This repository is L0–L3.** L4 (security/fuzzing) and L5
(compliance/orchestration evidence generation) are a separate, not-yet-open
layer, kept in a different repository by design — see [Licensing](#licensing-model)
below. They're shown on the diagram only because they constrain one thing
about L2 today: its public API is deliberately kept clean and scriptable so
that a future fuzzing harness (in the spirit of projects like
[Gallia](https://github.com/Fraunhofer-AISEC/gallia)) can drive it without
forking it.

### Module responsibilities

| Module | Layer | Responsibility |
|---|---|---|
| `hal/` | L0 | One hardware abstraction, many backends — nothing above it branches on interface vendor |
| `buses/` | L1 | Frame-level send/receive, basic cyclic stimulation, decode orchestration |
| `dbc_arxml/` | L1 | DBC/ARXML/LDF/A2L parsing |
| `diag/` | L2 | UDS/DoIP client, ODX import, the virtual-ECU responder used for zero-hardware testing |
| `runner/` | L3 | The `pytest` plugin: fixtures, deterministic wait helpers, CI entrypoints |
| `report/` | L3 | HTML/JSON report generation |
| `trace/` | L1/L3 | BLF/ASC/MDF4 read+write, query/filter over recorded traffic |

## Data flow

```
  Input files                     Runtime engine                    Output
  ───────────                     ──────────────                    ──────
  DBC / ARXML / LDF ──┐
  A2L ─────────────────┼──▶  dbc_arxml/ (decode)  ──┐
  ODX / PDX ───────────┘                            │
                                                      ▼
  Physical bus ──▶ hal/ (backend) ──▶ buses/ (frames) ──▶ diag/ (UDS/DoIP) ──▶ runner/ (pytest)
  or vcan ──────────▶                                                              │
  (zero hardware)                                                                  ├──▶ report/ (HTML/JSON)
                                                                                    │
  BLF / ASC / MDF4 ◀── trace/ (write) ◀──────────────────────────────────────────┘
```

A physical CAN interface and `vcan` (Linux's virtual CAN device) are equally
first-class entry points. Nothing above `buses/` can tell the difference —
that's what makes "try it with zero hardware" an architectural property,
not a marketing claim.

## Standards this project speaks

| Standard | What it's for |
|---|---|
| ISO 14229 (UDS) | Diagnostic services — session control, DID read/write, DTCs, routines, transfer |
| ISO 13400 (DoIP) | UDS transport over Ethernet |
| ISO 15765-2 (ISO-TP) | UDS transport over CAN |
| ISO 11898 (CAN / CAN-FD) | The bus itself |
| ISO 17987 (LIN) | Low-cost sensor/actuator bus |
| DBC | De-facto CAN signal-database format |
| ARXML (AUTOSAR, Classic + Adaptive) | AUTOSAR communication-matrix format |
| ASAM MCD-2 MC (A2L) | ECU variable description for measurement/calibration |
| ASAM MDF (MDF4) | Measurement/trace file format |
| ODX / MCD-2 D | OEM diagnostic database format (read-only support) |
| BLF / ASC | Vector's trace formats — read/write for installed-base interop |

Deliberately **not** targeted yet: SOME/IP, SOVD, ODX write, CAN XL,
10BASE-T1S, TSN, DDS. Some of these are realistic fast-follow candidates;
none of them block the L0–L3 scope this repository covers.

## Deployment model

| Environment | What runs |
|---|---|
| Developer laptop | Full package, interactive use, `vcan` or a real interface |
| Headless Linux bench | Identical package, unattended, real hardware |
| CI container (GitHub Actions / GitLab CI) | Identical package, `vcan` + virtual UDS ECU, zero physical hardware |

All three install from the same package. There is no "CI edition."

## Licensing model

L0–L3 (this repository) is Apache License 2.0 — see [LICENSE](LICENSE).
Security-testing and compliance-evidence features (L4/L5) are planned as a
separate, commercially-licensed layer built *around* this engine, in a
separate repository — not a fork of it, and not merged into this one. If
you're evaluating whether to build on Tapwright: everything in this
repository is, and is intended to remain, fully open source.

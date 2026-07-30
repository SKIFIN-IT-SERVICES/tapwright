# Tapwright

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/SKIFIN-IT-SERVICES/tapwright/actions/workflows/ci.yml/badge.svg)](https://github.com/SKIFIN-IT-SERVICES/tapwright/actions/workflows/ci.yml)
[![Status: pre-v0.1](https://img.shields.io/badge/status-pre--v0.1-orange.svg)](ROADMAP.md)

**A CI-native, open-core UDS/DoIP diagnostic test runner and DBC/ARXML-aware
trace analyzer for automotive software testing.**

Linux-first, dongle-free, pytest-native. It runs on the CAN/CAN-FD interface
you already own — or on none at all, against a simulated ECU, so you can try
the whole thing without a bench, a car, or a license dongle.

> **Status:** early development, pre-`v0.1`. The interfaces below describe
> where this project is headed, not what's shipped yet. See
> [ROADMAP.md](ROADMAP.md) for what exists today versus what's next.

## Why

Automotive bus/diagnostic testing tools (Vector CANoe, ETAS INCA, dSPACE)
are Windows-desktop, dongle-licensed, five-figure-per-seat products built in
the 1990s. The industry moved to Linux, containers, and CI/CD; the tools
that test automotive software mostly didn't. Tapwright is an attempt at the
tool that assumes CI from day one instead of retrofitting it — open-core,
git-diffable, and priced so an individual engineer or a small team can
adopt it without a procurement process.

## What it does (target v0.1 scope)

- **Talks CAN, CAN-FD, and LIN** over whatever interface you have —
  SocketCAN, a $35 `gs_usb`-class adapter (e.g. CANable 2.0), Kvaser, PEAK,
  Vector XL — through one abstraction, plus a zero-hardware virtual bus
  (`vcan`) for CI and quick starts.
- **Decodes DBC and ARXML** (Classic and Adaptive AUTOSAR) to named,
  symbolic signals.
- **Speaks UDS (ISO 14229)** over ISO-TP and **DoIP (ISO 13400)** —
  session control, DID read/write, DTCs, routines, transfer/flash sequence.
- **Reads and writes BLF, ASC, and MDF4** — trace files interoperate with
  the Vector-format installed base, not just with itself.
- **Is a `pytest` plugin**, not a proprietary scripting language. Tests are
  plain Python; configuration is YAML/TOML. Everything is text, so `git
  diff` on a test suite actually means something.
- **Runs the same way** on a laptop, a headless Linux bench, and inside a
  CI container — one package, not a "server edition" SKU.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full layer breakdown and
[ROADMAP.md](ROADMAP.md) for the milestone plan.

## What it explicitly does not do

Restbus-simulation GUI authoring, calibration/XCP write access, SOME/IP,
SOVD, LIN schedule-table authoring, hard-real-time HIL I/O, or anything
resembling an AUTOSAR BSW stack. Some of these are later roadmap items;
some are permanently out of scope — see [ARCHITECTURE.md](ARCHITECTURE.md).

## Installation

```bash
pip install tapwright   # not yet published — this is the intended command
```

Not on PyPI yet. Watch [ROADMAP.md](ROADMAP.md) or the repo's Releases page.

## Contributing

Contributions are very welcome, especially before `v0.1` while the shape of
the project is still being decided. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the dev setup, testing (no hardware required — everything runs against
a virtual CAN bus), and the DCO sign-off process. Please also read the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Please don't file public issues for security reports — see
[SECURITY.md](SECURITY.md) for how to report privately.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

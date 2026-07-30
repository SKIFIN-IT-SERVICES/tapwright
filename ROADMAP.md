# Roadmap

Tapwright is pre-`v0.1`. This describes the planned path to a first usable
release and beyond. Milestone numbers are sequential, not calendar
commitments — they'll slip, and that's fine; what matters is the order.

## Where things stand today

- [x] Repository scaffolding: license, governance docs, packaging, CI skeleton
- [ ] Everything else

## Path to v0.1

| Milestone | Goal | Ships |
|---|---|---|
| **M1 — Spike** | Prove the core plumbing works | UDS read-DID over a real interface + `vcan`, proving the `python-can` + `udsoncan` + ISO-TP glue |
| **M2 — Core diagnostics** | The engine a real ECU could be pointed at | Full multi-backend hardware abstraction, DBC/ARXML decode, UDS over ISO-TP *and* DoIP, the full core UDS service set, `pytest` fixtures |
| **M3 — Trace + report** | Make results legible and interoperable | BLF/ASC/MDF4 read+write, HTML and JSON reports |
| **M4 — CI story** | Make "CI-native" literally true | Virtual UDS ECU on `vcan` (so anyone can try it with zero hardware), GitHub Actions and GitLab CI examples, docs site |
| **M5 — Polish + launch** | Ready for outside users | ODX/PDX read-only import, `pip install`-able package, `CONTRIBUTING.md`/governance files (done — you're reading them), public launch |
| **M6 — First real-world pilot** | Find out what we got wrong | Deployed into a real workflow; whatever breaks shapes what comes after `v0.1` |

## After v0.1 (fast-follow, not yet scheduled)

- SOME/IP + SOME/IP-SD testing
- SOVD client (the HTTP/REST-native ASAM diagnostics standard)
- ODX **write**, not just read
- CAN XL, 10BASE-T1S
- An open plugin/adapter SDK for third-party hardware and report backends

## Explicitly not planned in this repository

Restbus-simulation GUI authoring, full calibration/XCP-write workflows,
hard-real-time HIL I/O, AUTOSAR BSW stack functionality of any kind. See
[ARCHITECTURE.md](ARCHITECTURE.md) for why — in short, this project stays a
*verification/test tool*, not a code generator or a stack implementation,
deliberately.

Security-testing and compliance-evidence automation (fuzzing, R155/ISO 21434
evidence generation, and similar) are a planned layer built *on top of* this
engine, but as a separate, not-yet-open project — not part of this
repository's roadmap.

## How to influence this roadmap

Open an issue. Before `v0.1`, the roadmap is genuinely still up for debate —
this is the best time to show up.

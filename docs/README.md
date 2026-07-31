# Engineering Specifications

This folder is the detailed spec set for implementing Tapwright's L0–L3 engine — adapted from internal project planning so the development team (human or AI-assisted) has everything needed to start building, not just the short public summary in the repo-root `README.md`/`ARCHITECTURE.md`/`ROADMAP.md`.

**Read in this order:**

1. [`input-variables.md`](input-variables.md) — the constants everything else cites: in-scope standards (`IV-STD-*`), regulatory constraints (`IV-REG-*`), hardware/OS targets (`IV-HW-*`), licensing model (`IV-LIC-*`), success metrics (`IV-KPI-*`). Business/funding figures are intentionally not published here.
2. [`tooling-requirements.md`](tooling-requirements.md) — **what** the product must do: the full functional requirement catalog (`TOOL-REQ-xxx`), organized by layer (L0 hardware abstraction → L3 test runner), each with MoSCoW priority, phase, and acceptance criteria.
3. [`framework-requirements.md`](framework-requirements.md) — **how** it gets built: language/runtime, dependency policy, packaging, CI/CD, licensing mechanics, OSS governance (`FW-REQ-xxx`).
4. [`architecture.md`](architecture.md) — the full system design synthesizing 1–3: module map, data flow, deployment model, non-functional requirements (`NFR-xxx`), and Architecture Decision Records (`ADR-xxx`) for the load-bearing calls. This is the detailed version of the repo-root `ARCHITECTURE.md`.
5. [`phase-1-requirements.md`](phase-1-requirements.md) — the milestone-by-milestone build plan (M1–M6), each milestone listing exactly which `TOOL-REQ-xxx`/`FW-REQ-xxx` IDs it satisfies plus acceptance criteria. This is the detailed version of the repo-root `ROADMAP.md`.

## ID schemes, at a glance

| Prefix | Meaning | Lives in |
|---|---|---|
| `IV-xxx` | Input Variable — a constant/constraint | `input-variables.md` |
| `TOOL-REQ-xxx` | Tooling Requirement — a functional capability | `tooling-requirements.md` |
| `FW-REQ-xxx` | Framework Requirement — a tech-stack/process decision | `framework-requirements.md` |
| `NFR-xxx` | Non-Functional Requirement | `architecture.md` |
| `ADR-xxx` | Architecture Decision Record | `architecture.md` |
| `P1-REQ-*` | Phase-1-specific requirement not covered by the above | `phase-1-requirements.md` |

A requirement is cited by ID everywhere it's relevant rather than restated — if you're implementing `diag/`, for example, start from `TOOL-REQ-022`–`027` in `tooling-requirements.md`, then read `architecture.md` §4 (the L2 API contract) before writing the first line, not after.

## A note on provenance

These documents were adapted from a private internal planning repository. Where the originals cited internal market-research files (competitor teardowns, standards deep-dives, etc.), those citations have been replaced with plain-language context here, since the source files aren't part of this repository. Treat any remaining bracketed citation (e.g. `IV-HW-02`) as a pointer to another file in *this* folder, not to something external.

## See also

- [`../PROCESS.md`](../PROCESS.md) — the development workflow (issue → test plan → TDD → checkin) used to actually build against these specs.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — dev environment setup.

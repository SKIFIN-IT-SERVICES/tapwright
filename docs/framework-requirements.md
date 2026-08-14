<!--
Provenance: adapted from Tapwright's internal planning repository (private).
Source-file citations refer to internal research not included here — treat
as provenance/context, not links.
-->

# Framework Requirements — Tech Stack, Engineering Process & OSS Governance

**Prepared 2026-07-30.** Where [`tooling-requirements.md`](tooling-requirements.md) catalogs **what** the product must do, this document catalogs **how it gets built and shipped**: language/runtime, dependency policy, packaging, CI/CD, licensing mechanics, and — because this ships as open source from day one — the governance and contribution machinery that determines whether the bottom-up adoption motion actually works. A missing `CONTRIBUTING.md` or an unclear license boundary is not a hygiene issue for this product; it is a go-to-market defect, because the entire strategy is "engineers adopt it themselves, below procurement's radar."

Labeling matches the rest of the set: **[HARD]**/**[EST]** carried from prior research, **[NEW-EST]** for judgment calls introduced here that maintainers should explicitly confirm rather than treat as settled.

---

## 1. Language & Runtime — `FW-REQ-00x`

| ID | Requirement | Priority | Rationale |
|---|---|---|---|
| FW-REQ-001 | Python as the core implementation language | Must | Matches the community being targeted for adoption — `python-can`, `cantools`, `udsoncan`, `doipclient`, `asammdf`, and `pytest` are all Python; pytest-native authoring is the entire differentiation claim against CAPL |
| FW-REQ-002 | Minimum supported Python version: 3.10+ | Should | Aligns with the industry signal that even Vector CANoe 19 added Python 3.10+ support in 2025 — this is now the credible floor, not an aggressive one |
| FW-REQ-003 | Do not start a Rust core for the bus engine now | Won't (for now) | Explicitly deferred: a Rust core may be worth revisiting for the perf-sensitive bus engine once the product has adopters, but Python gets adopters fastest and that's the current objective |

---

## 2. Dependency / Build-vs-Reuse Policy — `FW-REQ-01x`

**Governing principle:** the product *is* the supported, integrated, documented, CI-native experience around these libraries — not a rewrite of them.

**Licenses below are verified, not estimated** (verified 2026-08-01; machine-enforced by [`licences.toml`](../licences.toml) + `tools/check_licences.py`). The two marked ⚠️ were previously recorded from estimate and **both estimates were wrong** — see the correction note after the table.

| ID | Dependency | Role | License | Policy |
|---|---|---|---|---|
| FW-REQ-010 | `python-can` | L0 hardware abstraction (TOOL-REQ-001–007) | ⚠️ **LGPL-3.0** (verified 2026-08-01) | Reuse as-is; this *is* the L0 layer. **Dependency only** — never vendored, forked, or frozen into a binary (FW-REQ-019) |
| FW-REQ-011 | `cantools` | DBC/ARXML/A2L decode (TOOL-REQ-014, 015, 017) | MIT (verified) | Reuse; contribute upstream fixes for ARXML-depth gaps found during integration rather than forking |
| FW-REQ-012 | `can-isotp` (`python-can-isotp`) | ISO-TP transport (TOOL-REQ-022) | ⚠️ **MIT** (verified 2026-08-01) | Reuse directly. The isolation caveat previously attached to this entry **does not apply** — it can be a plain core dependency |
| FW-REQ-013 | `udsoncan` | UDS client (TOOL-REQ-022, 023, 024) | MIT (verified) | Reuse; wrap, don't rewrite |
| FW-REQ-014 | `doipclient` | DoIP transport (TOOL-REQ-023) | MIT (verified) | Reuse; wrap into the `udsoncan` connection |
| FW-REQ-015 | `asammdf` | MDF4 read/write (TOOL-REQ-021) | **LGPL-3.0** (verified 2026-08-01) | Ships as an **optional extra** (`tapwright[mdf4]`); the core installs and passes its full suite without it. Dependency only, per FW-REQ-019 |
| FW-REQ-016 | `pytest` | Test runner (TOOL-REQ-028–030) | MIT (verified) | Native — this *is* the L3 differentiation vs. CAPL |
| FW-REQ-017 | License verification gate (process requirement) | Must | No dependency is added without an entry in [`licences.toml`](../licences.toml) recording its license and the date it was verified against the package's own metadata. CI fails otherwise. Permissive-only for the core; weak copyleft only under FW-REQ-019; strong copyleft never | `IV-LIC-04` |
| FW-REQ-018 | Future security-layer compatibility constraint | Must (architectural, not a dependency choice) | The L2 diagnostics engine (TOOL-REQ-027) must remain wrappable by **Gallia** (Fraunhofer AISEC, Apache-2.0) without a fork — this constrains L2's API design, not its dependency list | `IV-LIC-03` |
| FW-REQ-019 | **LGPL isolation boundary** | Must | `python-can` and `asammdf` (both LGPL-3.0) are dependencies *only*: installed from PyPI, imported at runtime, unmodified. Never copied into the tree, never forked, never statically linked into a distributed artifact. This is why **FW-REQ-022 (single static binary) is BLOCKED** pending legal opinion. Enforced by the vendoring scan in `tools/check_licences.py` (HAL-08) | `IV-LIC-04`; `DECISIONS-RECORD.md` §5 |

### ⚠️ Correction — the two licenses this table originally got wrong

Both entries above marked ⚠️ were recorded as `[EST]` estimates and both were wrong, in opposite directions:

| Dependency | Originally recorded | Actually (verified 2026-08-01) | Consequence |
|---|---|---|---|
| `python-can` | BSD-2-Clause | **LGPL-3.0** | Worse than assumed. The permissive core has a weak-copyleft dependency at its foundation, so FW-REQ-019's isolation boundary is load-bearing rather than precautionary — and FW-REQ-022 is blocked |
| `can-isotp` | LGPL-3.0 | **MIT** | Better than assumed. No isolation needed; the optional/pluggable-transport workaround FW-REQ-012 originally called for is unnecessary work that can be dropped |

The lesson is the one FW-REQ-017 now enforces mechanically: **a license nobody checked is not data.** An estimate that happened to be right (`asammdf`) is indistinguishable, at planning time, from two that were wrong — which is why the gate checks a recorded verification date rather than trusting the field.

The remaining external dependency is a **legal opinion on LGPL isolation**, which blocks first public release but not development.

---

## 3. Packaging & Distribution — `FW-REQ-02x`

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FW-REQ-020 | `pip install`-able package published to PyPI | Must | P1-v0.1 |
| FW-REQ-021 | Container image published alongside the PyPI package, day one | Must | P1-v0.1 |
| FW-REQ-022 | Single static Linux binary | Could | Later — explicitly deferred |

---

## 4. Testing & QA Framework — `FW-REQ-03x`

| ID | Requirement | Priority | Rationale |
|---|---|---|---|
| FW-REQ-030 | The product's own development test suite is written in `pytest` | Must | Dogfooding the exact differentiator being sold; a pytest-native product with a non-pytest internal test suite would undercut its own pitch |
| FW-REQ-031 | The full internal test suite runs against `vcan` with zero physical hardware | Must | Doubles as the contributor-onboarding requirement — a new contributor must be able to clone, install, and run the full test suite without owning a CAN interface |
| FW-REQ-032 | Maintain meaningful automated-test coverage on L0–L2 | Should | **Set 2026-08-14: 85% line / 75% branch on L0–L2, as a ratchet** (may rise, never fall) — enforced by `tools/coverage_ratchet.py`. No coverage gate on L3, where failures are loud. The number is a floor against drift, not a target: *coverage is not a goal, assertions are* — a test that executes code without asserting on its behaviour is rejected in review regardless of its effect on the number (`AGENTS.md` §5) |

---

## 5. CI/CD Framework — `FW-REQ-04x`

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FW-REQ-040 | GitHub Actions as the primary, best-documented CI target | Must | P1-v0.1 |
| FW-REQ-041 | GitLab CI as a secondary, documented target | Should | P1-v0.1 |
| FW-REQ-042 | Every PR's CI run exercises the L0–L2 abstraction against `vcan` | Must | P1-v0.1 |

---

## 6. Licensing Framework — `FW-REQ-05x`

| ID | Requirement | Priority | Detail |
|---|---|---|---|
| FW-REQ-050 | Apache-2.0 license file at repo root; SPDX license headers on every source file | Must | Standard Apache-2.0 OSS hygiene; makes the license machine-checkable |
| FW-REQ-051 | Contribution certification: **Developer Certificate of Origin (DCO)**, not a full CLA | [NEW-EST — flagged for explicit maintainer confirmation] | A DCO (sign-off-in-commit, as used by the Linux kernel and many CNCF projects) is lower-friction for the individual-engineer bottom-up contributor this product's GTM depends on. A full CLA — the kind that lets a company unilaterally relicense contributions — adds a legal-review step that cuts directly against "an engineer adopts this below procurement's radar." This is a real decision with a real tradeoff (a CLA gives more flexibility to later relicense L3 pieces commercially); it is stated here as a recommendation, not a fact. |
| FW-REQ-052 | Open-core/proprietary code separation from day one | Must | Security/compliance code, even before it exists, is architected to live in a **separate repository/package**, never mixed into the OSS L0–L3 repo. This avoids the common "open-core mess" where proprietary code has to be surgically extracted from an OSS history later. | `IV-LIC-02` |

---

## 7. OSS Governance & Contribution Requirements — `FW-REQ-06x`

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FW-REQ-060 | Repository structure follows the L0–L3 module layout (`hal/`, `buses/`, `dbc_arxml/`, `diag/`, `runner/`, `report/`, `trace/`) | Must | P1-v0.1 — **done**, see `src/tapwright/` |
| FW-REQ-061 | `CONTRIBUTING.md` published at launch, not retrofitted later | Must | P1-v0.1 — **done** |
| FW-REQ-062 | Code of Conduct published at launch (Contributor Covenant) | Must | P1-v0.1 — **done** |
| FW-REQ-063 | Issue and PR templates | Should | P1-v0.1 — **done** |
| FW-REQ-064 | Semantic Versioning; `0.x` during Phase 1 with breaking changes documented in a CHANGELOG | Must | P1-v0.1 — **done** |
| FW-REQ-065 | Tagged releases auto-publish to PyPI and the container registry | Should | P1-v0.1 — not yet automated |
| FW-REQ-066 | Documentation site live by Milestone M4 ("CI story") | Must | P1-v0.1, by week 16 |

---

## 8. Coding Standards — `FW-REQ-07x`

| ID | Requirement | Priority | Detail |
|---|---|---|---|
| FW-REQ-070 | An automated formatter/linter runs in CI and blocks merge on violation | Must | `ruff` — **done**, see `pyproject.toml` and `.github/workflows/ci.yml` |
| FW-REQ-071 | Type hints + a type checker (`mypy`) on all public APIs, at minimum L2's diagnostics-engine surface | Should | Directly supports TOOL-REQ-027 ("clean, scriptable L2 API") — type hints make that API contract enforceable, not just documented in prose |
| FW-REQ-072 | Pre-commit hooks mirror the CI lint/format gate locally | Could | **Done**, see `.pre-commit-config.yaml` |

---

## 9. Extensibility / Plugin SDK — `FW-REQ-08x`

| ID | Requirement | Priority | Phase | Note |
|---|---|---|---|---|
| FW-REQ-080 | Open plugin/adapter API for third-party HAL backends and report formats | Should | Fast-follow | Internal research lists "open plugin/adapter SDK from day one" as a leapfrog differentiator against vendor-neutral orchestration tools — **but** the v0.1 checklist ([`phase-1-requirements.md`](phase-1-requirements.md)) does not include a plugin SDK. This document resolves the tension in favor of the narrower v0.1 scope: ship the concrete L0–L3 feature set first, formalize the plugin boundary once real third-party integration demand appears. Flagged explicitly rather than silently dropped. |

---

## Traceability Index

| Category | ID prefix | Section | Depends on |
|---|---|---|---|
| Language & runtime | `FW-REQ-00x` | §1 | — |
| Dependency policy | `FW-REQ-01x` | §2 | `IV-LIC-*`; `TOOL-REQ-001–030` |
| Packaging | `FW-REQ-02x` | §3 | — |
| Testing/QA | `FW-REQ-03x` | §4 | `IV-HW-04`; TOOL-REQ-026 |
| CI/CD | `FW-REQ-04x` | §5 | TOOL-REQ-033, 034 |
| Licensing | `FW-REQ-05x` | §6 | `IV-LIC-*` |
| OSS governance | `FW-REQ-06x` | §7 | — |
| Coding standards | `FW-REQ-07x` | §8 | TOOL-REQ-027 |
| Extensibility | `FW-REQ-08x` | §9 | — |

# RUN-06 benchmark — `examples/github-actions/` vs. `vectorgrp/ci-siltest-demo`

<!-- SPDX-License-Identifier: Apache-2.0 -->

Per the plan's own instruction for this loop: "Benchmark against
`vectorgrp/ci-siltest-demo`" — Vector's own public reference
implementation of automated SIL testing in GitHub Actions. Cloned
directly (`git clone https://github.com/vectorgrp/ci-siltest-demo`) and
read `.github/workflows/main.yaml` to produce this comparison; nothing
below is estimated.

## What Vector's own demo requires

| | Vector's `ci-siltest-demo` |
|---|---|
| Runner | **Self-hosted only** — `runs-on: vtt`, `canoe-small`, `canoe-large` (custom labels for machines with Vector's own tooling pre-installed) |
| Licensed tooling required | DaVinci Configurator, vVIRTUALtarget, CANoe4SW Server Edition |
| Jobs | 4 (`build-sut` → `build-simulation` → `run-tests-simulation` → `display-test-report`), each depending on artifacts uploaded/downloaded from the previous |
| Steps (approx., across all 4 jobs) | 18 |
| Can a cold clone go green on a stock GitHub-hosted runner? | **No** — regardless of step count, the pipeline cannot execute at all without owning Vector licenses and configuring self-hosted runners first |

## What `tapwright`'s example requires

| | `examples/github-actions/` |
|---|---|
| Runner | **Stock `ubuntu-latest`** (GitHub-hosted, free) |
| Licensed tooling required | None |
| Jobs | 1 |
| Steps | 5 (checkout, setup-python, bring-up-vcan, pip install, pytest) |
| Can a cold clone go green on a stock GitHub-hosted runner? | **Yes** — verified directly by this repository's own CI (`Example — GitHub Actions (RUN-06)` job in `ci.yml`), which runs this exact example's test against the current source on every push |

## The honest comparison

This isn't a fair fight on *test depth* — Vector's demo exercises a real
compiled ECU binary (`LightControl.dpa`) through a licensed simulation
environment; `tapwright`'s example exercises a Python-simulated virtual
ECU. It *is* a fair fight on the specific claim RUN-06's own acceptance
criterion makes: **setup friction to a first green run**. On that axis,
Vector's own public reference cannot reach a first green run on a stock
runner at any step count, and `tapwright`'s example does, in 5 steps, on
free infrastructure. That gap — not raw test depth — is this project's
actual positioning against the incumbent tooling (see `README.md`'s own
"Why" section).

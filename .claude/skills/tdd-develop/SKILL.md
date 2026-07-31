---
name: tdd-develop
description: Run the red-green-refactor TDD loop to implement a Tapwright feature or fix against an existing test plan. Use when actively writing code for an issue that already has a test plan (from the test-plan skill) — this is step 3 of PROCESS.md's development loop.
---

# TDD Develop

Step 3 of [`PROCESS.md`](../../../PROCESS.md)'s development loop: standard Kent Beck-style test-driven development, applied one test case at a time from the plan produced by the `test-plan` skill.

## Prerequisite

A test plan must already exist (issue comment or skipped test stubs in `tests/`). If it doesn't, stop and run the `test-plan` skill first — implementing without a plan defeats the point of the loop and this skill should not improvise one on the fly.

## The loop (repeat per test case)

1. **Red.** Take the next unimplemented case from the plan. If it's a skip-stubbed test, remove the `@pytest.mark.skip`; if it's a plan bullet, write the test now. Run it:
   ```bash
   pytest path/to/test_file.py::test_name -v
   ```
   Confirm it fails **for the reason you expect** — read the failure output. A test that errors out on an `ImportError` or `AttributeError` before reaching your assertion isn't red for the right reason; fix the setup first, then re-confirm red on the actual assertion.

2. **Green.** Write the minimum implementation that makes this one test pass. Resist implementing more than this test demands — the next test in the plan will pull the next increment out of you; pre-building it now usually means building the wrong shape before you have a second data point.
   ```bash
   pytest path/to/test_file.py::test_name -v   # confirm green
   pytest                                       # confirm nothing else broke
   ```

3. **Refactor.** With the test green as a safety net, clean up: naming, duplication, structure. Re-run the test (and the full suite) after every refactor step, not just at the end — a refactor that breaks something is much cheaper to spot immediately than three steps later.

4. **Repeat** for the next case in the plan until it's exhausted.

## No hardware required

The full suite runs against `vcan`, per [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#running-tests):
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
pytest
```
If a specific case genuinely needs real hardware (a specific vendor backend), mark it to skip cleanly when the hardware isn't present rather than failing CI — see [`docs/architecture.md`](../../../docs/architecture.md) NFR-003 (test determinism) for why a flaky/hardware-dependent test in the default suite is treated as a bug in itself.

## Special case — touching `diag/`'s public API

Before red on any test that exercises `diag/`'s public surface, re-read [`docs/architecture.md`](../../../docs/architecture.md) §4 (the L2 API contract) and ADR-004. The requirement — transport-agnostic client interface, an inspectable request/response interception point, no hidden per-session state — is architectural, not test-visible today, so a green test suite alone won't catch a violation of it. Check the shape of what you're building against that section explicitly, not just against the test plan.

## When you're done with all cases

Run the complete quality gate before handing off to `checkin`:
```bash
ruff check .
ruff format --check .
pytest --cov=tapwright --cov-report=term-missing
```
All three must be clean. Then move to the `checkin` skill — this skill's job ends at "the code works and is clean," not at "it's committed."

## What this skill does NOT do

Decide what to test (that's `test-plan`, already done before this skill starts) or commit/push the result (that's `checkin`). If mid-loop you discover the test plan itself was wrong or incomplete, pause and say so — update the plan (or flag it back to `test-plan`) rather than silently testing something different from what was agreed.

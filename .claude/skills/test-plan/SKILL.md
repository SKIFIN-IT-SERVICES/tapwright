---
name: test-plan
description: Draft a test-first test plan for a Tapwright issue before implementation begins, grounded in the relevant TOOL-REQ/FW-REQ acceptance criteria. Use when starting work on an already-filed issue, before writing any implementation code — this is step 2 of PROCESS.md's development loop and a prerequisite for tdd-develop.
---

# Test Plan

Step 2 of [`PROCESS.md`](../../../PROCESS.md)'s development loop. The point is to decide what "done" means, as concrete test cases, *before* implementation exists — this is what makes step 3 (`tdd-develop`) genuinely test-first instead of tests-added-after.

## Steps

1. **Read the issue and its cited requirement.** If the issue references `TOOL-REQ-xxx` or `FW-REQ-xxx`, open [`docs/tooling-requirements.md`](../../../docs/tooling-requirements.md) or [`docs/framework-requirements.md`](../../../docs/framework-requirements.md) and read that row's **Acceptance Criteria** column closely — this is the source of truth for what the test plan must cover, not the issue title.

2. **Enumerate test cases across three categories:**
   - **Happy path** — the case the acceptance criteria literally describe (e.g. TOOL-REQ-022: "reads a DID from a real or virtual ECU over CAN").
   - **Edge cases** — boundary conditions the acceptance criteria imply but don't spell out (oversized payloads, empty responses, minimum/maximum values, the zero-hardware `vcan` path *and* a real-backend path where relevant per [`IV-HW-*`](../../../docs/input-variables.md)).
   - **Error cases** — what should happen when the input is invalid or the ECU/bus misbehaves (malformed frame, negative UDS response, timeout, wrong session state). Untested error paths are where most real bugs live — don't skip this category to save time.

3. **If a requirement's acceptance criteria don't cover a case you think matters:** that's a signal, not a blocker. Flag it explicitly — either the requirement needs a one-line addendum (propose the edit) or the test case is out of scope and should be dropped. Don't silently test something the spec never asked for; don't silently drop something the spec implies either.

4. **Format the plan** as whichever fits the change's size:
   - **Small change** (a handful of cases): post the plan as a comment on the issue — a short bullet list of test case descriptions is enough.
   - **Larger change**: write it directly as `tests/` file(s) with cases stubbed via `@pytest.mark.skip(reason="test plan — implementation pending")`, so the plan and the eventual tests are the same artifact (no transcription step, no drift between "what I planned" and "what I tested").

5. **Special case — L2 (`diag/`) changes:** if any test case exercises `diag/`'s public API surface, explicitly include a test case (or a comment noting the constraint) that reflects [`docs/architecture.md`](../../../docs/architecture.md) §4's requirement: the API must stay usable by an external caller intercepting requests/responses, even though no such caller exists yet. This doesn't need its own test today, but the plan should note it wasn't forgotten.

6. **Hand off.** Report the finished plan location (issue comment or file paths) so `tdd-develop` can pick up the first case as "red."

## What this skill does NOT do

Write implementation code, or run the tests (there's nothing to run yet beyond confirming the skip-stubs collect without error). If you find yourself writing the function body to figure out what to test, stop — that's `tdd-develop`'s job, and doing it here defeats the point of planning tests before code.

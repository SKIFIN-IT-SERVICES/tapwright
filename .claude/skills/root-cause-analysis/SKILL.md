---
name: root-cause-analysis
description: Perform a structured root cause analysis (reproduce, isolate, five-whys, write-up, regression test) when a Tapwright bug surfaces in CI, code review, or after release — then file the resulting fix as a new issue. Use for bugs found AFTER code has already merged, not for problems caught during normal test-plan/tdd-develop work before merge (those just get fixed in place).
---

# Root Cause Analysis

Step 5 of [`PROCESS.md`](../../../PROCESS.md)'s development loop — the branch that fires when a bug surfaces after code has already shipped (merged to `main`, flagged in review of an already-merged PR, or reported from real usage). This is deliberately more process than a same-PR fix warrants; use judgment on severity (a typo doesn't need this) but default to running it for anything that reached `main` incorrectly.

## When to use this vs. just fixing it

- **Just fix it, no RCA:** a bug caught by `tdd-develop`'s own test loop, or in review before merge. The normal loop already handles this — that's what steps 2–4 are for.
- **Run this skill:** the bug shipped. Something in CI on `main`, an intermittent/flaky failure, or a report from actual use of the tool.

## Steps

1. **Reproduce it deterministically.** Get a minimal, repeatable reproduction — exact input, exact command, exact environment (backend used, `vcan` vs. real hardware). If it *won't* reproduce deterministically — it's intermittent — **that non-determinism is itself the first finding**: file it as its own issue immediately (cite [`docs/architecture.md`](../../../docs/architecture.md) NFR-003, test determinism) even before you understand the underlying bug. A flaky CI-native test tool failing its own determinism bar is not a footnote.

2. **Isolate.**
   - If it's a regression (worked before, broke now): `git bisect` between the last-known-good and first-known-bad commits.
     ```bash
     git bisect start
     git bisect bad HEAD
     git bisect good <last-known-good-sha>
     # git bisect run pytest path/to/failing_test.py   # if it's automatable
     ```
   - If it's not a regression (always broken, just newly discovered): narrow to the smallest input/call sequence that still triggers it.

3. **Ask "why" until you hit a process or design gap — the Five Whys.** Don't stop at the first technical cause; keep asking why *that* was possible. Write out the chain, e.g.:
   - Why did the DID length check accept a >4-byte payload? → The bounds check only validated the lower bound.
   - Why did that ship? → No test covered an oversized-payload case.
   - Why not? → The test plan for TOOL-REQ-024 didn't include a boundary-size category.
   - Why not? → The `test-plan` skill's edge-case prompt didn't explicitly call out payload-size boundaries as a standing category.
   - **Root cause:** a gap in the test-planning checklist, not (just) a missing bounds check. The fix therefore includes both the code fix *and* strengthening what future test plans check for — otherwise this recurs with the next boundary-sensitive feature.
   
   Stop asking "why" once you reach something actionable at the process/design level, not necessarily exactly five times.

4. **Write up the RCA.** Short, structured, as an issue or issue comment:
   - **What happened** (user-visible symptom)
   - **Root cause** (the end of the five-whys chain, not just the immediate technical cause)
   - **The fix** (what changes, at both the code level and, if the chain pointed there, the process level)
   - **The regression test** that would have caught this — write its description now; it becomes the fix issue's test plan (skip `test-plan` as a separate step, since you already did that thinking here)

5. **File the fix as a new issue** (use the `file-issue` skill or `gh issue create` directly), citing this RCA and the relevant `TOOL-REQ`/`FW-REQ` ID if one exists. Label it normally. Run it through the standard loop: the RCA's regression test *is* the test plan, so proceed straight to `tdd-develop` — red (the regression test, currently failing), green (the actual fix), refactor.

## What this skill does NOT do

Skip straight to a fix without the write-up, even when the fix is obvious. The write-up is what prevents the same root cause from producing a different symptom next time — an un-written-up "obvious" fix is exactly how the same class of bug recurs three more times before anyone notices the pattern.

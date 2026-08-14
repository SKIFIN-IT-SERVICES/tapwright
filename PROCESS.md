# Development Process

Tapwright is built issue-first and test-first. This document is the loop every change — feature or bugfix — goes through, and the conventions that make the loop actually work as a team scales past one contributor. If you're using Claude Code, each step below has a matching skill in [`.claude/skills/`](.claude/skills/) that walks through it interactively; this document is the process those skills implement, so it's also the reference for anyone working without them.

Most of the code here is written by AI agents running unattended, which changes what this process has to defend against — an agent converges on *whatever the tests measure*, so the tests have to measure the right thing and be beyond the agent's reach. Two additions carry that weight: the **oracle** requirement in step 2, and the **fixture-immutability** rule in step 3. [`AGENTS.md`](AGENTS.md) states the invariants that hold in every step; [`LOOPS.md`](LOOPS.md) tracks the backlog those changes come from.

## The loop

```
   ┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
   │  1. FILE    │────▶│  2. TEST    │────▶│  3. TDD      │────▶│  4. CHECKIN │
   │    ISSUE    │     │    PLAN     │     │  DEVELOP     │     │             │
   └─────────────┘     └─────────────┘     └──────────────┘     └──────┬──────┘
         ▲                                   Red → Green →              │
         │                                    Refactor loop             │
         │                                                              ▼
         │              ┌─────────────┐                          merged, closes
         └──────────────│ 5. ROOT     │◀─── bug found in CI,      the issue
                         │    CAUSE    │     review, or prod
                         │    ANALYSIS │
                         └─────────────┘
                         produces a new issue
                         (the regression test
                          IS the fix's test plan)
```

Every change starts as an issue and ends as a merged PR that closes it. Bugs found after merge don't get a quick silent patch — they get a root cause analysis, which produces a new issue with a regression test as its acceptance criterion, and the loop runs again. This is deliberate: it's slower for a one-line fix and much faster for the tenth recurrence of a bug that was never actually understood the first time.

---

## 1. File an issue

Nothing gets built without an issue first — including your own idea, including a "quick fix." This isn't bureaucracy for its own sake: it's the first checkpoint that catches scope creep (does this actually belong in `v0.1`? see [`docs/tooling-requirements.md`](docs/tooling-requirements.md)'s Won't list) before any code exists to be attached to it.

- Use the [bug report](.github/ISSUE_TEMPLATE/bug_report.md) or [feature request](.github/ISSUE_TEMPLATE/feature_request.md) template.
- If the issue implements a specific requirement, reference its ID (`TOOL-REQ-022`, `FW-REQ-051`, etc.) from [`docs/`](docs/) — this is what keeps the codebase traceable back to the spec instead of drifting from it silently.
- Label it: layer (`L0`–`L3`), priority (`must`/`should`/`could`, mirroring MoSCoW from the requirements catalog), and type (`bug`/`enhancement`). See [Labels](#labels) below for the full set.
- Claude Code: the `file-issue` skill does this end-to-end, including finding the right `TOOL-REQ`/`FW-REQ` ID to cite.

## 2. Write a test plan

Before any implementation code, write down what "done" means as tests — not prose, actual test cases (happy path, edge cases, error cases). This is the artifact that makes step 3 possible to do test-first instead of test-eventually.

- Post it as a comment on the issue, or as a `tests/` file with `@pytest.mark.skip(reason="test plan — implementation pending")` stubs, whichever fits the change's size.
- Ground every test case in the requirement's stated acceptance criteria (from `docs/tooling-requirements.md`) — if the acceptance criteria don't cover a case you're about to test, that's a signal the requirement itself needs a one-line update, not that you should test something ungrounded.
- Claude Code: the `test-plan` skill drafts this from the issue and the relevant requirement ID.

### Name the oracle

**Every test plan must name its oracle explicitly: the executable authority that decides whether the output is correct.** Not "the tests I'm about to write" — those restate the implementation's intent, and if the same agent writes both, they agree with each other by construction while both being wrong. An oracle is a source of truth that existed *before* the implementation and was authored independently of it:

| Oracle | What it looks like here | Used by |
|---|---|---|
| The wrapped library, called directly | Assert our output is byte-identical to calling `cantools`/`udsoncan`/`python-can` ourselves | Most `hal/`, `buses/`, `diag/` work |
| A recorded golden trace | A BLF/ASC fixture whose decoded content is known and human-verified | `trace/`, `dbc_arxml/` |
| A published specification | ISO 14229 (UDS), 13400 (DoIP), 15765-2 (ISO-TP) — deterministic request/response semantics | `diag/` protocol work |
| The virtual ECU | A simulated ECU on `vcan` that responds correctly and misbehaves on demand | Anything integration-level |
| A property that must hold | `decode(encode(x)) == x`; no input crashes the parser | Hardening work |

Write the oracle down as a specific file, fixture, or reference call — "differential vs. `cantools`" is a direction, `fixtures/databases/multiplexed.dbc` decoded by `cantools` directly is an oracle. **If you cannot name one, you don't have a test plan yet** — you have a research task, and it needs a human to either narrow the goal until an oracle exists ("import ODX" doesn't have one; "resolve DID `0xF190` to `VIN` in this PDX" does) or to mark the work human-led. Some work genuinely is: API ergonomics and naming have taste as the requirement, and that's the process working, not failing.

Also state the **verification tier** the change must reach (T0 static → T1 unit → T2 integration on `vcan` → T3 differential → T4 property/fuzz → T5 human) and the **blast radius**: the file set the change may touch. `fixtures/**` and `tests/differential/expected/**` are outside every blast radius, always.

## 3. TDD development (red → green → refactor)

Standard Kent Beck-style TDD, applied to the test plan from step 2:

1. **Red** — un-skip (or write) one failing test from the plan. Run it. Confirm it fails for the reason you expect, not for an unrelated reason (a test that fails on an `ImportError` before it even reaches your assertion isn't testing anything yet).
2. **Green** — write the minimum code that makes it pass. Resist building more than the current test demands; the next test in the plan will demand the next increment.
3. **Refactor** — with the test green as a safety net, clean up (naming, duplication, structure) without changing behavior. Re-run the test after every refactor step.
4. Repeat for the next test case in the plan until the plan is exhausted.

This applies at every layer (L0–L3), but **L2 (`diag/`) carries extra weight**: because its public API is the one this project has committed to keeping externally wrappable ([`docs/architecture.md`](docs/architecture.md) §4, ADR-004), a red-green-refactor cycle that touches `diag/`'s public surface should include a step 0 — re-read that section — before red.

- No physical hardware is needed for any of this — the full test suite runs against `vcan` (see [`CONTRIBUTING.md`](CONTRIBUTING.md#running-tests)).
- Claude Code: the `tdd-develop` skill runs this loop, pulling test cases from the plan one at a time.

### Fixtures are immutable

**Never edit a file under `fixtures/` or `tests/differential/expected/` to make a failing test pass.** This is the one rule in this document with no proportionality clause attached.

A differential test failing means one of two things: the implementation is wrong, or the fixture is wrong. The first is overwhelmingly more likely, and it is the *entire point* of the test — a failing differential test is the process working. Changing the expected output to match what the code produced doesn't fix anything; it deletes the bug report and guarantees nothing will ever catch that bug again. The suite goes green, the defect ships, and it decodes plausible-looking wrong numbers forever. In a tool people use to decide whether an ECU behaves correctly, that is the worst outcome available.

Fixtures *are* sometimes wrong. When you believe one is:

1. **Stop.** Don't change it, and don't work around it.
2. Escalate to a maintainer with the evidence — what the fixture says, what the implementation produces, and why you believe the fixture is the wrong one.
3. If confirmed, the fixture change lands as **its own commit**, with a `fixture-change:` trailer recording what was wrong and how the new expected value was independently verified, and CODEOWNERS approval from someone who didn't write the code under test. Never bundled into the commit that needed it to pass.

CI's `guardrails` job enforces this mechanically, and `CODEOWNERS` requires the human approval. Both are backstops. The rule holds whether or not they catch you.

The same applies to the coverage ratchet and the guardrail scripts themselves: if a check is in your way, that's a conversation to have, not a file to edit.

## 4. Checkin

- **Branch naming:** `<type>/<short-description>`, e.g. `feat/uds-security-access-hooks`, `fix/isotp-flow-control-timeout`. Type matches the Conventional Commits type below.
- **Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):** `<type>(<scope>): <description>`, e.g. `feat(diag): add UDS 0x27 security access hook points`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. Scope is usually the module (`hal`, `buses`, `diag`, `runner`, `report`, `trace`) or `repo` for cross-cutting changes. This is enforced by a commit-msg hook (`conventional-pre-commit`, see [`.pre-commit-config.yaml`](.pre-commit-config.yaml)) — a malformed commit message fails locally before it ever reaches CI.
- **Every commit is signed off** (DCO — `git commit -s`), per [`CONTRIBUTING.md`](CONTRIBUTING.md#developer-certificate-of-origin-dco).
- Before opening the PR: `ruff check . && ruff format --check . && pytest` all pass locally. CI re-runs the same checks, but catching it locally is faster for you and cheaper for shared CI minutes.
- Open the PR against `main` using the [PR template](.github/PULL_REQUEST_TEMPLATE.md) — it links back to the issue, lists what was tested, and checks the DCO/CHANGELOG/lint boxes.
- One reviewer approval + green CI required to merge. Squash-merge by default, so `main`'s history reads as one Conventional Commit per shipped change.
- **The reviewer must not have supervised the work being reviewed**, and reviews the change against the *issue and test plan*, not against the diff. Someone who watched an implementation converge over forty iterations is the worst available judge of whether the result matches what was originally asked for — by then the intent has been re-anchored to whatever the last failure was. Standing review questions: does this satisfy the goal as written, or only the tests? **What existing library does this, that we've now reimplemented?** Did it stay inside its blast radius?
- Claude Code: the `checkin` skill runs the pre-flight checklist and drafts the commit message and PR description.

## 5. Root cause analysis (when a bug surfaces after merge)

If something breaks in CI on `main`, in review, or in the field, don't just patch the symptom. Root cause analysis is proportionate to severity — a typo doesn't need this, a flaky `vcan` test or an incorrect UDS response does:

1. **Reproduce** it deterministically. If it only reproduces intermittently, that's itself the first finding (see NFR-003, test determinism, in [`docs/architecture.md`](docs/architecture.md) §6) — file it as its own issue even before the underlying bug is understood.
2. **Isolate**: bisect to the change that introduced it if it's a regression; otherwise narrow to the smallest failing case.
3. **Ask "why" until you hit a process or design gap, not just a code gap** (the "Five Whys" pattern) — e.g. "the DID length check was wrong" → why did that ship? → "no test covered a >4-byte DID" → why not? → "the test plan didn't include an oversized-payload case" → that's the actual finding: the test-plan step needs a standing checklist item for boundary sizes, not just this one bug fixed.
4. **Write it up** as a short RCA: what happened, root cause, the fix, and — critically — the regression test that would have caught it, which becomes the acceptance criterion for the fix's issue (closing the loop back to step 1).
5. File the fix as a normal issue citing the RCA, and run it through the full loop (steps 1–4) like anything else. Don't skip test-plan-first just because you already know the fix — the regression test from the RCA *is* the test plan.
- Claude Code: the `root-cause-analysis` skill walks through this structure and files the resulting issue.

---

## Labels

| Category | Labels |
|---|---|
| Layer | `L0`, `L1`, `L2`, `L3` |
| Priority (MoSCoW) | `priority: must`, `priority: should`, `priority: could` |
| Type | `bug`, `enhancement`, `documentation` |
| Process | `needs-test-plan`, `needs-rca`, `good first issue` |

## Definition of Done

A change is done when: it closes an issue, its test plan is fully green (not skipped, not `xfail`ed away) **at the verification tier the plan declared**, `ruff`/`mypy`/`pytest` and the `guardrails` job all pass in CI, no fixture was modified to get there, `CHANGELOG.md` is updated, and — if it touches `diag/`'s public API — [`docs/architecture.md`](docs/architecture.md) §4 has been re-read and still holds.

## Why this is worth the overhead

This is more process than a one-line bugfix "needs." That's the point: the cost is paid once, per contributor, as a habit; the payoff compounds every time a regression *doesn't* happen because a boundary case was in the test plan, or every time a bug *doesn't* recur because its root cause — not its symptom — got fixed. For a project whose entire pitch is being the CI-native, trustworthy alternative to Windows-desktop tools with binary configs nobody can review, the development process itself has to hold to that same bar.

<!-- SPDX-License-Identifier: Apache-2.0 -->

# AGENTS.md — the agent contract

This file states the invariants that hold **regardless of which step of
[`PROCESS.md`](PROCESS.md) you are in**. `.claude/skills/` tells you *how to do a
step*; this file tells you what is true in every step. It is deliberately short
so it can be followed reliably. If it conflicts with anything else in the repo,
this file and `PROCESS.md` win — in that order, `PROCESS.md` being the
operational authority on workflow.

Applies to every automated agent and, equally, to humans.

## 1. Invariants at every commit

Every commit that lands on a branch must satisfy all of these:

- `ruff check . && ruff format --check . && mypy src` pass.
- `pytest` passes. Not "passes except the one I marked `xfail`."
- Every source file carries an SPDX header: `# SPDX-License-Identifier: Apache-2.0`
  (checked by `tools/check_spdx.py` in CI).
- The commit is signed off (DCO — `git commit -s`), per
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- The commit message is a [Conventional Commit](https://www.conventionalcommits.org/):
  `<type>(<scope>): <description>`.
- No new third-party dependency without a matching entry in
  [`licences.toml`](licences.toml). CI fails otherwise.
- **No L4 or L5 code in this repository.** Security testing (fuzzing, attack
  tooling) and compliance/orchestration live in a separate private repo, per
  ADR-003 and ADR-007. The boundary is the *repository*, not a feature flag.

## 2. The reuse rule

> If `python-can`, `cantools`, `udsoncan`, `doipclient`, `can-isotp`, or
> `asammdf` already does this, **wrap it. Do not reimplement it.** A PR that
> reimplements wrapped-library functionality will be rejected regardless of
> whether its tests pass.

This is the project's central technical strategy, not a style preference: the
product is the supported, integrated, CI-native experience around those
libraries. Reimplementing them destroys the differential-testing oracle (T3)
that keeps this codebase verifiable, and takes on maintenance the project has
deliberately declined.

The rule applies to test infrastructure too, not just shipped code. Before
building a tool, spend the half hour to check whether one exists.

If you believe a wrap is genuinely impossible — the library lacks a hook, the
API cannot express what we need — **stop and escalate**. Do not route around it
by rewriting.

## 3. The oracle rule

> **Do not modify files under `fixtures/` or `tests/differential/expected/` to
> make a test pass. If a fixture appears wrong, stop and escalate.**

A fixture is an *oracle*: an independently-authored authority on what correct
output looks like. Editing one to match your implementation converts a caught
bug into a permanent silent defect, and it does so invisibly — the suite goes
green, and nothing ever catches it again.

This is the single most likely way agentic development fails on this project.
CODEOWNERS and a CI guardrail enforce it mechanically; this rule exists so you
do not have to be stopped by them.

A legitimate fixture change is possible — fixtures do contain mistakes. The path
for it is: escalate, get a human to confirm the fixture is wrong, then make the
change in **its own commit** with a `fixture-change:` trailer explaining what was
wrong and how the new expected value was independently verified. Never bundled
into the commit that needed it to pass.

## 4. Forbidden

- **No security-bypass capability** (C-10). UDS service `0x27` request/response
  *mechanics* only. No seed-to-key derivation algorithms, no key databases, no
  brute-force or key-search helpers, no "example" implementations of either.
  Tapwright helps you test an ECU you are authorised to test; it is not an
  unlocking tool. Enforced by a CI scan (`tools/check_forbidden.py`), but the
  scan is a backstop for the rule, not the rule itself.
- **No vendoring of LGPL source** (C-9). `python-can` and `asammdf` are
  LGPL-3.0. They are *dependencies* — installed from PyPI, imported at runtime.
  Never copy their source into this tree, never fork them into `vendor/`, never
  freeze them into a binary artifact.
- **No network calls in tests.** Every test runs offline, against `vcan` and the
  virtual ECU. A test that reaches the internet is non-deterministic and will be
  rejected. `pytest` runs with sockets to external hosts treated as a bug.
- **No OEM-proprietary data in fixtures.** No customer DBC, ARXML, or PDX files,
  ever, in this public repository — regardless of how realistic a test fixture it
  would make. Every fixture needs recorded provenance (see
  `fixtures/PROVENANCE.md`).

## 5. Coverage

> **Coverage is not a goal. Assertions are. A test that executes code without
> asserting on its behaviour will be rejected in review regardless of its effect
> on coverage.**

The ratchet (85% line / 75% branch on L0–L2) exists to stop coverage *falling*.
It is not a target to be reached by writing tests that call functions and assert
nothing.

## 6. Blast radius

Every loop (issue) declares the file set it may modify. Stay inside it. If the
work genuinely cannot be completed without touching a file outside the declared
radius, that is a signal the loop was scoped wrong — **escalate rather than
widening it yourself**. CI checks this against the `Blast radius` block in the
linked issue.

`fixtures/**` and `tests/differential/expected/**` are outside every blast
radius, always, without exception.

## 7. Escalation protocol

**Stop and hand back to a human when:**

- The oracle appears wrong (a fixture, an expected output, a spec reading).
- Exit criteria cannot be met without touching forbidden or out-of-radius paths.
- You have hit the iteration cap (default 15) without going green.
- A new third-party dependency seems necessary.
- The work would require L4/L5 capability, or anything on the forbidden list.
- Two loops appear to contradict each other, or a requirement (`TOOL-REQ-*` /
  `FW-REQ-*`) appears wrong.

**When you escalate, include:** what you were trying to do, the exact failure
(command and output, not a paraphrase), what you have already tried and why each
attempt failed, and what you believe the underlying problem is. An escalation
that says "this doesn't work" wastes the handoff.

Escalating is a successful outcome, not a failure. A loop that stops at
iteration 4 with a clear question is far cheaper than one that spends 15
iterations converging on something wrong.

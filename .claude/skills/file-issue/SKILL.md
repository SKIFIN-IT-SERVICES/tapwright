---
name: file-issue
description: File a well-structured GitHub issue for a Tapwright bug or feature, using the project's templates, layer/priority/type labels, and TOOL-REQ/FW-REQ traceability. Use when the user wants to report a bug, propose a feature, or track upcoming work — this is always step 1 of PROCESS.md's development loop, before any code or test plan exists.
---

# File Issue

Step 1 of [`PROCESS.md`](../../../PROCESS.md)'s development loop. Nothing gets built without an issue first — this catches scope creep against [`docs/tooling-requirements.md`](../../../docs/tooling-requirements.md)'s Won't list before any code exists.

## Steps

1. **Determine bug vs. feature.** A bug is observed-behavior-doesn't-match-spec-or-expectation; a feature is new-capability-doesn't-exist-yet. This decides which template applies.

2. **Ground it in the spec, if it's covered by one.** Search [`docs/tooling-requirements.md`](../../../docs/tooling-requirements.md), [`docs/framework-requirements.md`](../../../docs/framework-requirements.md), and [`docs/phase-1-requirements.md`](../../../docs/phase-1-requirements.md) for a matching `TOOL-REQ-xxx` / `FW-REQ-xxx`:
   - If found, cite it in the issue body (`Implements TOOL-REQ-022`). This is what keeps the codebase traceable back to the requirement catalog instead of drifting.
   - If the work doesn't map to an existing requirement ID, say so explicitly rather than forcing a citation — not everything needs one (e.g. a genuine bug in already-shipped code has no forward-looking REQ to cite).
   - If it maps to something in the Won't-scope table, flag that clearly and ask the user to confirm before filing — this is exactly the scope-creep check the process exists to catch.

3. **Write the issue** using the appropriate template:
   - Bug: [`.github/ISSUE_TEMPLATE/bug_report.md`](../../../.github/ISSUE_TEMPLATE/bug_report.md) — what happened, what was expected, reproduction steps, environment (Tapwright version, Python version, OS, hardware backend if relevant).
   - Feature: [`.github/ISSUE_TEMPLATE/feature_request.md`](../../../.github/ISSUE_TEMPLATE/feature_request.md) — the real workflow problem being solved, not just the feature; check it against the Won't-scope table first, per the template's own instructions.

4. **Apply labels:**
   - **Layer**: `L0`, `L1`, `L2`, or `L3` — matches the module map in [`docs/architecture.md`](../../../docs/architecture.md) §2. If it doesn't cleanly fit one layer (e.g. touches `trace/`, which straddles L1/L3), pick the layer of the primary change.
   - **Priority**: `priority: must` / `priority: should` / `priority: could` — inherit directly from the cited requirement's MoSCoW rating if one exists; otherwise use judgment and say so.
   - **Type**: `bug` or `enhancement` (templates auto-apply these; verify they landed).
   - If this issue is itself the output of a root-cause analysis (see the `root-cause-analysis` skill), also apply `needs-rca` is *not* right here — that label marks issues still awaiting an RCA, not ones that already have one; link the RCA write-up in the issue body instead.

5. **File it** via `gh issue create` with the title, body, and labels assembled above. Confirm the labels actually exist in the repo first (`gh label list`) — if the label set has drifted from [`PROCESS.md`](../../../PROCESS.md)'s `## Labels` table, flag that rather than silently creating a differently-spelled label.

6. **Report back** the issue number/URL and a one-line summary of what was filed, so the user (or a follow-up `test-plan` skill invocation) can pick it up.

## What this skill does NOT do

Write a test plan (that's the `test-plan` skill, step 2) or start implementation (that's `tdd-develop`, step 3). Filing the issue is the whole job here — resist the urge to also sketch a solution in the issue body beyond what the template asks for.

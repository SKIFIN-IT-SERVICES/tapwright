---
name: checkin
description: Run the pre-flight checklist and prepare a compliant commit and pull request for Tapwright — lint, tests, DCO sign-off, Conventional Commits message, CHANGELOG update, PR template. Use when code changes are complete and ready to be committed and pushed — this is step 4 of PROCESS.md's development loop, after tdd-develop and before the PR is opened.
---

# Checkin

Step 4 of [`PROCESS.md`](../../../PROCESS.md)'s development loop. This is the pre-flight checklist between "the code works" (end of `tdd-develop`) and "it's merged."

## Pre-flight checklist (all must pass before committing)

```bash
ruff check .
ruff format --check .
pytest --cov=tapwright --cov-report=term-missing
```
If any of these fail, go back to `tdd-develop` — do not commit around a failing check by, e.g., excluding the failing file or lowering coverage expectations without discussion.

## Branch naming

`<type>/<short-description>`, matching the Conventional Commits type below — e.g. `feat/uds-security-access-hooks`, `fix/isotp-flow-control-timeout`, `docs/architecture-l2-contract-clarify`.

## Commit message — Conventional Commits

Format: `<type>(<scope>): <description>`

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`
- **Scope:** the module touched (`hal`, `buses`, `dbc_arxml`, `diag`, `runner`, `report`, `trace`) or `repo` for cross-cutting changes
- **Description:** imperative mood, no trailing period — e.g. `feat(diag): add UDS 0x27 security access hook points`

This is enforced by a commit-msg hook ([`conventional-pre-commit`](https://github.com/compilerla/conventional-pre-commit), configured in [`.pre-commit-config.yaml`](../../../.pre-commit-config.yaml)) — a malformed message is rejected locally before it reaches CI. If `pre-commit install --hook-type commit-msg` hasn't been run yet in this environment, run it now (see [`CONTRIBUTING.md`](../../../CONTRIBUTING.md)).

Reference the issue being closed in the commit body or PR description (`Closes #N`), not the subject line.

## Sign off (DCO)

Every commit: `git commit -s -m "..."`. This is not optional — see [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#developer-certificate-of-origin-dco) for why. If a commit was made without `-s`, amend it (`git commit --amend -s`) before pushing rather than leaving it unsigned.

## Update CHANGELOG.md

Add an entry under `## [Unreleased]`, in the relevant category (Added / Changed / Fixed), one line, referencing the issue/PR. Skip only for changes with zero user-visible effect (e.g. internal refactor with no behavior change) — and say so explicitly rather than silently omitting the entry.

## Open the PR

Use [`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md) (auto-populated by GitHub when you open via the web UI or `gh pr create` without `--body`). Fill in:
- What changed and why, linking the issue (`Closes #N`)
- Type of change
- The checklist (DCO, tests added, CHANGELOG updated, lint clean, `docs/architecture.md` re-read if `diag/`'s public API was touched)
- How it was tested (`vcan`, real hardware, or both — name the backend if real hardware)

```bash
gh pr create --title "<same as the primary commit subject>" --body "$(cat <<'EOF'
## What this changes and why
Closes #N

...

## How this was tested
...
EOF
)"
```

## After opening

One reviewer approval + green CI required to merge. Squash-merge by default (so `main` reads as one Conventional Commit per shipped change) unless the branch's individual commits are independently meaningful and the reviewer prefers to preserve them.

## What this skill does NOT do

Write the code (that's `tdd-develop`) or decide what to build (that's `file-issue`/`test-plan`). If the pre-flight checklist surfaces a failure, this skill's job is to send you back a step, not to work around the failure to get a commit out the door.

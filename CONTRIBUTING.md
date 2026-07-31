# Contributing to Tapwright

Thanks for considering it. This project is pre-`v0.1` and the shape of the
codebase is still being decided — this is the best time to have real
influence over it, not the worst time to show up.

Please also read the [Code of Conduct](CODE_OF_CONDUCT.md).

## The development process

This project follows a specific issue-first, test-first loop — file an
issue, write a test plan, implement test-driven (red/green/refactor),
check in — documented in full in [PROCESS.md](PROCESS.md), including what
to do when a bug surfaces after merge (root cause analysis, not a quiet
patch). Read that before your first PR; this file covers environment setup
and the mechanics, PROCESS.md covers the workflow itself.

If you're using Claude Code, [`.claude/skills/`](.claude/skills/) has a
skill for each step of that loop (`file-issue`, `test-plan`, `tdd-develop`,
`root-cause-analysis`, `checkin`).

For the full engineering spec behind any given requirement — what exactly
`TOOL-REQ-022` or `FW-REQ-051` means — see [`docs/`](docs/).

## Before you write code

For anything beyond a small fix, open an issue first (or comment on an
existing one) describing what you want to do. This project deliberately
keeps a narrow `v0.1` scope — see [ROADMAP.md](ROADMAP.md) and
[ARCHITECTURE.md](ARCHITECTURE.md) for what's in and out of scope — so a
quick conversation before a large PR saves everyone time.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying you wrote it or otherwise have
the right to submit it under this project's license:

```bash
git commit -s -m "your commit message"
```

This adds a `Signed-off-by: Your Name <you@example.com>` trailer to the
commit. We use a DCO rather than a Contributor License Agreement
specifically to keep the barrier to a first contribution low — set `user.name`
and `user.email` in git config so the trailer is meaningful, and you're set.

## Development setup

Requires **Python 3.10+**.

```bash
git clone https://github.com/SKIFIN-IT-SERVICES/tapwright.git
cd tapwright
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

`pre-commit install` sets up both the pre-commit (lint/format) and
commit-msg (Conventional Commits, see below) hooks in one step — see
[`.pre-commit-config.yaml`](.pre-commit-config.yaml)'s
`default_install_hook_types`.

## Running tests

**No hardware required.** The full test suite runs against Linux's virtual
CAN device (`vcan`), which is also how CI runs it:

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
pytest
```

If you're on macOS/Windows or don't have `vcan` available, tests that need
it are expected to skip cleanly rather than fail — please file an issue if
one doesn't.

## Code style

Formatting and linting run via `ruff` and are enforced in CI; `pre-commit
install` (above) runs the same checks locally before each commit so you
find out immediately instead of after pushing. Public APIs — especially
anything in `diag/` — should carry type hints; that module's API is
deliberately kept clean enough for external tools to build on later, so
treat its public surface with extra care.

## Commit messages — Conventional Commits

Format: `<type>(<scope>): <description>` — e.g.
`feat(diag): add UDS 0x27 security access hook points`.

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`
- **Scope:** the module touched (`hal`, `buses`, `dbc_arxml`, `diag`,
  `runner`, `report`, `trace`) or `repo` for cross-cutting changes

This is enforced by a commit-msg hook — a malformed message is rejected
locally, before it reaches CI. See [PROCESS.md](PROCESS.md#4-checkin) for
the full checkin checklist (branch naming, CHANGELOG, PR template).

## Pull requests

- Keep PRs scoped to one change. A PR that both fixes a bug and reformats
  unrelated files is harder to review and harder to revert if something's
  wrong.
- Add or update tests for behavior you change — ideally written test-first,
  per [PROCESS.md](PROCESS.md#3-tdd-development-red--green--refactor).
- Update `CHANGELOG.md` under `[Unreleased]`.
- CI must pass (lint + tests) before merge.
- Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md) — it's
  auto-populated when you open the PR.

## Where to start

Issues labeled `good first issue` are a reasonable entry point once they
exist. Until then: read [ARCHITECTURE.md](ARCHITECTURE.md), pick something
from the current milestone in [ROADMAP.md](ROADMAP.md), and open an issue
to claim it before starting.

# Contributing to Tapwright

Thanks for considering it. This project is pre-`v0.1` and the shape of the
codebase is still being decided — this is the best time to have real
influence over it, not the worst time to show up.

Please also read the [Code of Conduct](CODE_OF_CONDUCT.md).

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

## Pull requests

- Keep PRs scoped to one change. A PR that both fixes a bug and reformats
  unrelated files is harder to review and harder to revert if something's
  wrong.
- Add or update tests for behavior you change.
- Update `CHANGELOG.md` under `[Unreleased]`.
- CI must pass (lint + tests) before merge.

## Where to start

Issues labeled `good first issue` are a reasonable entry point once they
exist. Until then: read [ARCHITECTURE.md](ARCHITECTURE.md), pick something
from the current milestone in [ROADMAP.md](ROADMAP.md), and open an issue
to claim it before starting.

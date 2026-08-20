# SPDX-License-Identifier: Apache-2.0

"""T2 test plan for RUN-08 — container image build + quickstart smoke test
(`FW-REQ-021`, ADR-001).

Implements #33. The oracle is the plan's own acceptance line, verbatim:
"`docker run` executes the quickstart with no host setup." Every case below
shells out to a real `docker` CLI against a real Docker daemon and a real
built image — never a mock of either.

## Scope notes (posted in full to #33; kept here as a pointer)

- **Build + CI smoke test only.** This loop does not push the image to any
  registry (`ghcr.io` or otherwise) — that is a deliberate, separate,
  human-triggered action, not something this loop or its CI job does.
- **"No host setup" reading**: `vcan`'s kernel module has to be loadable on
  whatever machine ultimately runs `docker run` -- a host-*kernel*
  capability no container image can carry itself (containers share the
  host kernel). Read here as "no *interactive* host setup beyond
  `--cap-add` flags at run time" -- the same level CI's own
  `bring-up-vcan` action already provides at the runner level, and the
  same constraint RemotiveBus's own approach has.
- **Not independently tested**: the case where the host kernel genuinely
  cannot load `vcan` at all (module absent, not just not-yet-loaded).
  Every environment these tests actually run in (this dev machine, CI)
  guarantees `vcan` is loadable, so there is no way to exercise "it isn't"
  without faking the host kernel itself. Documented as a known gap, not
  silently dropped.
- **Scope correction found during tdd-develop, posted to #33**: the
  container runs as root, not the non-root user originally planned. Two
  non-root approaches were tried and both failed for reasons specific to
  this one-shot, `NET_ADMIN`-requiring entrypoint (capability inheritance
  doesn't cross a plain `USER` switch; `setcap` at build time hit a Docker
  overlay-filesystem limitation) -- see the Dockerfile's own comment. The
  corresponding test now asserts the actual (root) behavior rather than
  silently dropping the hygiene concern, so a future change away from root
  has to update this test deliberately.
- **L2 API-cleanliness note** (test-plan skill step 5): N/A -- this loop
  doesn't touch `diag/`'s public API surface; the quickstart script is a
  *caller* of it, same as any other test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SKIP = pytest.mark.skip(reason="test plan — implementation pending (issue #33)")

pytestmark = pytest.mark.requires_docker

IMAGE_TAG = "tapwright:test"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_FLAGS = ["--rm", "--cap-add=NET_ADMIN", "--cap-add=NET_RAW"]


def docker(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    # Docker's build/run output is UTF-8 regardless of platform; the default
    # `text=True` encoding follows the OS locale, which on Windows is a
    # legacy codepage (cp1252) that can't decode it -- observed as a
    # background-thread UnicodeDecodeError from subprocess's own output
    # reader, surfacing as a pytest warning rather than a clean failure.
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def built_image() -> str:
    """Builds the image once per test module rather than per case -- a
    `docker build` is slow, and every case in this file exercises the same
    image, not a variant of it.
    """
    result = docker("build", "-t", IMAGE_TAG, str(REPO_ROOT), timeout=600)
    assert result.returncode == 0, result.stderr
    return IMAGE_TAG


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_image_builds_successfully(built_image):
    result = docker("image", "inspect", built_image)
    assert result.returncode == 0


def test_quickstart_runs_successfully_with_required_capabilities(built_image):
    """The literal RUN-08 acceptance criterion: `docker run` executes the
    quickstart -- vcan bring-up, a VirtualECU, one UDS RDBI round-trip --
    end to end, with only `--cap-add` flags at run time.
    """
    result = docker("run", *RUN_FLAGS, built_image, timeout=60)

    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_quickstart_can_run_twice_independently(built_image):
    """Each `docker run` gets a fresh network namespace -- the entrypoint
    must not assume a `vcan0` interface already exists from a prior run.
    """
    first = docker("run", *RUN_FLAGS, built_image, timeout=60)
    second = docker("run", *RUN_FLAGS, built_image, timeout=60)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr


def test_build_context_excludes_git_and_dev_only_files(built_image):
    """`.dockerignore` hygiene: the published image shouldn't carry this
    repo's own `.git` history or CI-only files into a shipped artifact.
    """
    result = docker("run", "--rm", "--entrypoint", "sh", built_image, "-c", "test -e /app/.git")

    assert result.returncode != 0  # .git must NOT be present


def test_container_runs_as_root_deliberately_not_by_default_omission(built_image):
    """Scope correction, made during tdd-develop and posted to #33: this was
    originally a non-root check. Two non-root approaches were tried and
    both failed for filesystem/capability-inheritance reasons specific to
    this one-shot, `NET_ADMIN`-requiring entrypoint (see the Dockerfile's
    own comment for what was tried). Rather than silently dropping the
    hygiene concern, this case asserts the *actual* current behavior --
    root -- so a future change away from root (e.g. if this image grows a
    long-running mode where the su/gosu wrapper's cost is worth it) fails
    this test and has to update it deliberately, instead of the image
    quietly drifting to non-root with no test noticing either way.
    """
    result = docker("run", "--rm", "--entrypoint", "id", built_image, "-u")

    assert result.returncode == 0
    assert result.stdout.strip() == "0"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_quickstart_without_required_capabilities_fails_with_actionable_error(built_image):
    """Onboarding-quality requirement: a first-time user who forgets
    `--cap-add` should see a clear message pointing at the missing
    capability, not a bare Python traceback -- this is exactly the "no host
    setup" promise's most likely first failure mode.
    """
    result = docker("run", "--rm", built_image, timeout=60)

    assert result.returncode != 0
    assert "cap-add" in result.stderr.lower() or "net_admin" in result.stderr.lower()

# SPDX-License-Identifier: Apache-2.0

"""T1/T3: RUN-07's example verification (GitLab CI, `TOOL-REQ-034`).

Unlike RUN-06 (verified for real via a GitHub Actions CI job that
actually runs the example), there's no GitLab account/project to run a
real pipeline against -- see `examples/gitlab-ci/README.md`. What's
verified here instead:

- the test file's core logic matches RUN-06's own proven example
  (no drift between the two platforms' examples)
- `.gitlab-ci.yml` is valid YAML
- `.gitlab-ci.yml` validates against GitLab's own official JSON Schema
  for the format (`app/assets/javascripts/editor/schema/ci.json` in
  `gitlab-org/gitlab-foss` -- the same schema GitLab's own web IDE editor
  uses), fetched live and skipped (not failed) if the network is
  unavailable, matching this project's established pattern for checks
  that depend on an external service (`loop_telemetry.py`'s own
  `needs_rca_issue_count()`, INF-07).

GitLab's public CI Lint API (`/api/v4/ci/lint`) was the original plan for
this verification -- confirmed directly that its global, no-account
endpoint was removed in GitLab 16.0 (`/projects/:id/ci/lint` now requires
an authenticated project), so schema validation against GitLab's own
official schema is the closest real, no-account equivalent available.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GITLAB_CI_YML = REPO_ROOT / "examples" / "gitlab-ci" / ".gitlab-ci.yml"
GITHUB_ACTIONS_TEST = REPO_ROOT / "examples" / "github-actions" / "test_vin_read.py"
GITLAB_CI_TEST = REPO_ROOT / "examples" / "gitlab-ci" / "test_vin_read.py"

GITLAB_SCHEMA_URL = (
    "https://gitlab.com/gitlab-org/gitlab-foss/-/raw/master/"
    "app/assets/javascripts/editor/schema/ci.json"
)


def fetch_gitlab_ci_schema() -> dict | None:
    """`None` (never raises) if the network is unavailable -- a schema
    fetched over the network must not make this check flaky.
    """
    try:
        with urllib.request.urlopen(GITLAB_SCHEMA_URL, timeout=10) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def test_example_test_logic_matches_the_proven_github_actions_example():
    """No drift between the two platforms' examples: same scenario, same
    DID, same assertion -- only the CI orchestration YAML differs.
    """
    github_actions_source = GITHUB_ACTIONS_TEST.read_text(encoding="utf-8")
    gitlab_source = GITLAB_CI_TEST.read_text(encoding="utf-8")

    shared_lines = [
        'Scenario(dids={0xF190: DIDConfig(value=b"VIN1234567890123")})',
        "response = uds.read_data_by_identifier(0xF190)",
        'assert response.service_data.values[0xF190] == b"VIN1234567890123"',
    ]
    for line in shared_lines:
        assert line in github_actions_source
        assert line in gitlab_source


def test_gitlab_ci_yaml_is_valid_yaml():
    doc = yaml.safe_load(GITLAB_CI_YML.read_text(encoding="utf-8"))
    assert "test" in doc


def test_gitlab_ci_yaml_matches_official_schema():
    schema = fetch_gitlab_ci_schema()
    if schema is None:
        pytest.skip("could not reach GitLab's schema host -- network unavailable")

    doc = yaml.safe_load(GITLAB_CI_YML.read_text(encoding="utf-8"))

    import jsonschema

    jsonschema.validate(instance=doc, schema=schema)


def test_requirements_txt_matches_the_github_actions_example():
    """Both examples install the same not-yet-on-PyPI git URL -- no drift
    between the two platforms' install instructions.
    """
    github_actions_requirements = (
        REPO_ROOT / "examples" / "github-actions" / "requirements.txt"
    ).read_text(encoding="utf-8")
    gitlab_requirements = (REPO_ROOT / "examples" / "gitlab-ci" / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert "git+https://github.com/SKIFIN-IT-SERVICES/tapwright.git@main" in (
        github_actions_requirements
    )
    assert github_actions_requirements == gitlab_requirements

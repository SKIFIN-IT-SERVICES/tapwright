# SPDX-License-Identifier: Apache-2.0

"""T1: the guardrails actually guard (INF-02, INF-03, INF-04, DIAG-08).

These checks are the mechanical defence against the failure mode the plan calls
oracle capture — a test made to pass by editing what it was testing against.
A guardrail nobody tested is a guardrail nobody knows works, and the moment it
matters is exactly the moment nobody is watching. So each one is tested the way
you would test a lock: not "does it open", but "does it stay shut against the
thing it exists to stop".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_blast_radius  # noqa: E402
import check_fixtures  # noqa: E402
import check_forbidden  # noqa: E402
import check_licences  # noqa: E402
import check_spdx  # noqa: E402

# --------------------------------------------------------------------------
# C-10 — no security-bypass capability (DIAG-08)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "def seed_to_key(seed): return seed ^ 0xFF",
        "def seed2key(seed): ...",
        "def calculate_key(seed): ...",
        "def derive_key(seed): ...",
        "KEY_TABLE = {0x01: b'\\xde\\xad'}",
        "SEED_KEY_TABLE = []",
        "# helper to brute force the key",
        "def bypass_security(client): ...",
    ],
)
def test_forbidden_scan_rejects_key_derivation(source):
    """The scan blocks the code C-10 exists to keep out of the repository."""
    hits = check_forbidden.scan_text(source)
    assert hits, f"forbidden scan missed: {source!r}"


@pytest.mark.parametrize(
    "source",
    [
        # 0x27 request/response mechanics are the whole point of the layer and
        # must not trip the scan. A guardrail that blocks legitimate work gets
        # disabled, and then it guards nothing.
        "def request_seed(self, level): ...",
        "def send_key(self, level, key): ...",
        "def security_access(self, level, key_callback): ...",
        "response = client.unlock_security_access(level)",
        "SECURITY_ACCESS = 0x27",
    ],
)
def test_forbidden_scan_allows_uds_mechanics(source):
    """Transporting a key the caller supplies is exactly what we do ship."""
    assert not check_forbidden.scan_text(source), f"false positive on: {source!r}"


def test_forbidden_scan_rejects_l4_imports():
    """ADR-003/007: the open/commercial split is a repository boundary."""
    assert check_forbidden.scan_text("from tapwright.security import Fuzzer")


def test_repository_is_clean_of_forbidden_capability():
    """The live check, over the real tree."""
    assert check_forbidden.main() == 0


# --------------------------------------------------------------------------
# INF-04 — fixture immutability and provenance
# --------------------------------------------------------------------------


def write_manifest(fixtures_dir: Path, body: str) -> None:
    (fixtures_dir / "provenance.toml").write_text(body, encoding="utf-8")


@pytest.fixture
def fixture_tree(tmp_path):
    """A miniature fixtures/ directory with one recorded fixture."""
    fixtures_dir = tmp_path / "fixtures"
    (fixtures_dir / "databases").mkdir(parents=True)
    fixture = fixtures_dir / "databases" / "example.dbc"
    fixture.write_text("BO_ 100 Example: 8 ECU\n", encoding="utf-8")

    write_manifest(
        fixtures_dir,
        f"""
[[fixture]]
path = "databases/example.dbc"
sha256 = "{check_fixtures.sha256_of(fixture)}"
origin = "self-authored"
licence = "Apache-2.0"
source = "Written for this test"
added = "2026-08-14"
verified_by = "a-human"
description = "Minimal DBC"
""",
    )
    return fixtures_dir, fixture


def load_manifest(fixtures_dir: Path):
    return check_fixtures.load(fixtures_dir / "provenance.toml")


def test_intact_fixture_passes(fixture_tree):
    fixtures_dir, _ = fixture_tree
    assert check_fixtures.verify(fixtures_dir, load_manifest(fixtures_dir)) == []


def test_edited_fixture_is_detected(fixture_tree):
    """The core defence: content changed under a recorded hash fails, loudly.

    This is the scenario the whole guardrail exists for — a failing differential
    test 'fixed' by editing the expected value. It must fail whether or not
    anyone reads the diff.
    """
    fixtures_dir, fixture = fixture_tree
    fixture.write_text("BO_ 100 Example: 8 TAMPERED\n", encoding="utf-8")

    errors = check_fixtures.verify(fixtures_dir, load_manifest(fixtures_dir))

    assert len(errors) == 1
    assert "CONTENT CHANGED" in errors[0]
    # The message has to teach, not just fail: someone hitting this needs to
    # know escalation is the path, not a hash update.
    assert "escalate" in errors[0].lower()


def test_deleted_fixture_is_detected(fixture_tree):
    fixtures_dir, fixture = fixture_tree
    fixture.unlink()
    errors = check_fixtures.verify(fixtures_dir, load_manifest(fixtures_dir))
    assert any("does not exist on disk" in error for error in errors)


def test_unrecorded_fixture_is_detected(fixture_tree):
    """A fixture with no provenance is a legal risk and an epistemic one."""
    fixtures_dir, _ = fixture_tree
    (fixtures_dir / "databases" / "mystery.dbc").write_text("BO_ 1 X: 8 E\n", encoding="utf-8")

    errors = check_fixtures.verify(fixtures_dir, load_manifest(fixtures_dir))
    assert any("has no entry in provenance.toml" in error for error in errors)


def test_incomplete_provenance_is_detected(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    fixture = fixtures_dir / "sample.dbc"
    fixture.write_text("x\n", encoding="utf-8")
    write_manifest(
        fixtures_dir,
        f'[[fixture]]\npath = "sample.dbc"\nsha256 = "{check_fixtures.sha256_of(fixture)}"\n',
    )

    errors = check_fixtures.verify(fixtures_dir, load_manifest(fixtures_dir))
    assert any("missing" in error and "verified_by" in error for error in errors)


def test_unknown_origin_is_rejected(tmp_path):
    """Provenance we can't classify means provenance we can't defend."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    fixture = fixtures_dir / "sample.dbc"
    fixture.write_text("x\n", encoding="utf-8")
    write_manifest(
        fixtures_dir,
        f"""
[[fixture]]
path = "sample.dbc"
sha256 = "{check_fixtures.sha256_of(fixture)}"
origin = "found-on-a-customer-share"
licence = "Unknown"
source = "somewhere"
added = "2026-08-14"
verified_by = "a-human"
""",
    )

    errors = check_fixtures.verify(fixtures_dir, load_manifest(fixtures_dir))
    assert any("is not one of" in error for error in errors)


def test_live_fixture_corpus_is_intact():
    assert check_fixtures.main([]) == 0


# --------------------------------------------------------------------------
# blast-radius / fixture-change trailer (plan §4.5)
# --------------------------------------------------------------------------


def test_modified_existing_fixture_is_flagged():
    """The core case the trailer requirement exists for: an *existing*
    fixture data file changed, no fixture-change: trailer anywhere."""
    changes = [("M", "fixtures/databases/multiplexed.dbc")]
    assert check_blast_radius.modified_protected_fixtures(changes) == [
        "fixtures/databases/multiplexed.dbc"
    ]


def test_added_fixture_is_not_flagged():
    """A brand-new fixture (status A, not M/D/R) needs no trailer — this
    module's own docstring says so explicitly."""
    changes = [("A", "fixtures/databases/new_one.dbc")]
    assert check_blast_radius.modified_protected_fixtures(changes) == []


def test_provenance_manifest_edit_alone_is_not_flagged():
    """provenance.toml is modified on *every* fixture-adding loop (that's
    how a new [[fixture]] entry gets recorded) — flagging that as 'an
    existing fixture changed' would require a fixture-change: trailer for a
    purely additive edit, contradicting the module's own stated intent.
    Caught while adding BUS-01's fixtures (issue #22): this exact case
    would otherwise have failed CI for no real reason.
    """
    changes = [("M", "fixtures/provenance.toml")]
    assert check_blast_radius.modified_protected_fixtures(changes) == []


def test_provenance_manifest_does_not_mask_a_real_fixture_edit():
    """Both changing in the same commit: the manifest edit is excluded, but
    the actual fixture data-file edit is still caught."""
    changes = [
        ("M", "fixtures/provenance.toml"),
        ("M", "fixtures/expected/dbc_multiplexed_engine_data.json"),
    ]
    assert check_blast_radius.modified_protected_fixtures(changes) == [
        "fixtures/expected/dbc_multiplexed_engine_data.json"
    ]


# --------------------------------------------------------------------------
# INF-03 — licence policy (C-7, C-9)
# --------------------------------------------------------------------------


POLICY = {
    "allowed": ["Apache-2.0", "MIT"],
    "isolation_required": ["LGPL-3.0"],
    "forbidden": ["GPL-3.0"],
}


def test_gpl_dependency_is_rejected():
    """INF-03's exit criterion: adding a GPL dependency fails the build."""
    errors: list[str] = []
    check_licences.check_licence_policy(
        {
            "policy": POLICY,
            "dependency": [{"name": "boofuzz", "licence": "GPL-3.0", "verified": "2026-08-14"}],
        },
        errors,
    )
    assert any("forbidden" in error for error in errors)
    # The error should point at the architecture that makes GPL tooling usable
    # at all here, rather than just saying no.
    assert any("process boundary" in error for error in errors)


def test_lgpl_dependency_requires_isolation():
    """C-9: LGPL is fine as a dependency, never as vendored source."""
    errors: list[str] = []
    check_licences.check_licence_policy(
        {
            "policy": POLICY,
            "dependency": [{"name": "python-can", "licence": "LGPL-3.0", "verified": "2026-08-01"}],
        },
        errors,
    )
    assert any("isolation" in error for error in errors)

    errors = []
    check_licences.check_licence_policy(
        {
            "policy": POLICY,
            "dependency": [
                {
                    "name": "python-can",
                    "licence": "LGPL-3.0",
                    "verified": "2026-08-01",
                    "isolation": "dependency-only",
                }
            ],
        },
        errors,
    )
    assert errors == []


def test_unverified_licence_is_rejected():
    """An unverified licence is an estimate, and estimates have already been wrong twice."""
    errors: list[str] = []
    check_licences.check_licence_policy(
        {"policy": POLICY, "dependency": [{"name": "somelib", "licence": "MIT"}]},
        errors,
    )
    assert any("verified" in error for error in errors)


def test_undeclared_dependency_is_rejected():
    errors: list[str] = []
    check_licences.check_manifest_coverage(
        {"newlib"}, {"dependency": [{"name": "cantools"}]}, errors
    )
    assert any("no entry in licences.toml" in error for error in errors)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("python-can>=4.0", "python-can"),
        ("cantools", "cantools"),
        ("tomli; python_version<'3.11'", "tomli"),
        ("asammdf[decode]>=7", "asammdf"),
        ("pytest >= 8", "pytest"),
    ],
)
def test_requirement_names_are_parsed(spec, expected):
    assert check_licences.parse_requirement_name(spec) == expected


def test_vendored_copyleft_is_detected(tmp_path):
    """C-9 / HAL-08: LGPL source copied into the tree fails the build."""
    src = tmp_path / "src" / "tapwright" / "hal"
    src.mkdir(parents=True)
    (src / "bundled_can.py").write_text(
        "# GNU LESSER GENERAL PUBLIC LICENSE\n# Version 3\n", encoding="utf-8"
    )

    errors: list[str] = []
    check_licences.check_no_vendored_copyleft(tmp_path, errors)
    assert any("vendored source" in error for error in errors)


def test_vendor_directory_is_detected(tmp_path):
    src = tmp_path / "src" / "tapwright" / "_vendor"
    src.mkdir(parents=True)
    (src / "can.py").write_text("pass\n", encoding="utf-8")

    errors: list[str] = []
    check_licences.check_no_vendored_copyleft(tmp_path, errors)
    assert any("vendored third-party source" in error for error in errors)


def test_live_licence_policy_passes():
    assert check_licences.main() == 0


def test_manifest_records_the_corrected_licences():
    """The two facts docs/framework-requirements.md originally got wrong.

    python-can was recorded BSD-2-Clause and can-isotp LGPL-3.0; both were
    estimates and both were wrong. Pinning them in a test means a future edit
    that quietly reverts to the estimate fails rather than passing silently.
    """
    manifest = check_licences.load(REPO_ROOT / "licences.toml")
    by_name = {entry["name"]: entry for entry in manifest["dependency"]}

    assert by_name["python-can"]["licence"] == "LGPL-3.0"
    assert by_name["python-can"]["isolation"] == "dependency-only"
    assert by_name["can-isotp"]["licence"] == "MIT"


# --------------------------------------------------------------------------
# FW-REQ-050 — SPDX headers
# --------------------------------------------------------------------------


def test_missing_spdx_header_is_detected(tmp_path):
    path = tmp_path / "module.py"
    path.write_text('"""No header."""\n', encoding="utf-8")
    assert not check_spdx.has_header(path)


def test_spdx_header_after_shebang_is_accepted(tmp_path):
    path = tmp_path / "script.py"
    path.write_text(
        "#!/usr/bin/env python3\n# SPDX-License-Identifier: Apache-2.0\n", encoding="utf-8"
    )
    assert check_spdx.has_header(path)


def test_spdx_header_buried_deep_is_rejected(tmp_path):
    """A licence identifier on line 40 is a comment, not a header."""
    path = tmp_path / "module.py"
    path.write_text("\n" * 40 + "# SPDX-License-Identifier: Apache-2.0\n", encoding="utf-8")
    assert not check_spdx.has_header(path)


def test_every_tracked_source_file_has_an_spdx_header():
    assert check_spdx.main([]) == 0

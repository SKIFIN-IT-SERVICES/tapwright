# SPDX-License-Identifier: Apache-2.0

"""Fixture integrity and provenance gate (INF-04, plan §4.3 / §4.5).

Two jobs:

**Integrity.** Every fixture's SHA-256 is recorded in ``fixtures/provenance.toml``
and checked here. A changed hash fails the build. This is the mechanical half of
the fixture-immutability rule — the half that works even when nobody reads the
diff carefully, which is the case the rule actually needs to survive. The plan
names oracle capture (an agent quietly editing an expected output to make a
failing test pass) as the single most likely way development fails on this
project; a hash check is a cheap, complete defence against the accidental
version of it.

**Provenance.** Every fixture records where it came from and who verified it.
This catches the legal risk — OEM-proprietary data landing in a public
repository — and the epistemic one, an expected output nobody can explain.

    python tools/check_fixtures.py             # verify
    python tools/check_fixtures.py --update    # recompute hashes, stub new entries
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _toml import load  # noqa: E402

REQUIRED_FIELDS = ("path", "sha256", "origin", "licence", "source", "added", "verified_by")

VALID_ORIGINS = {"self-authored", "self-generated", "public-sample"}

# Manifest and docs are not themselves fixtures.
NOT_FIXTURES = {"provenance.toml", "PROVENANCE.md", ".gitkeep"}

# Fixtures are meant to be small and pointed (PROVENANCE.md §3). A large one is
# not necessarily wrong, but it should be a deliberate decision someone made.
MAX_FIXTURE_BYTES = 5 * 1024 * 1024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fixture_files(fixtures_dir: Path) -> list[Path]:
    return sorted(
        path for path in fixtures_dir.rglob("*") if path.is_file() and path.name not in NOT_FIXTURES
    )


def verify(fixtures_dir: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = manifest.get("fixture", [])
    by_path = {entry.get("path"): entry for entry in entries}

    on_disk = {path.relative_to(fixtures_dir).as_posix() for path in fixture_files(fixtures_dir)}

    for rel in sorted(on_disk - set(by_path)):
        errors.append(
            f"fixtures/{rel} has no entry in provenance.toml.\n"
            f"    Every fixture records where it came from, under what licence, and who "
            f"verified it\n"
            f"    (fixtures/PROVENANCE.md §2). Run `--update` to stub the entry, then fill "
            f"it in by hand."
        )

    for rel in sorted(set(by_path) - on_disk):
        errors.append(
            f"provenance.toml lists 'fixtures/{rel}', which does not exist on disk.\n"
            f"    A deleted fixture means the tests that relied on it are now asserting "
            f"against nothing."
        )

    for rel in sorted(on_disk & set(by_path)):
        entry = by_path[rel]
        path = fixtures_dir / rel

        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            errors.append(f"fixtures/{rel}: provenance entry is missing {', '.join(missing)}.")

        origin = entry.get("origin")
        if origin and origin not in VALID_ORIGINS:
            errors.append(
                f"fixtures/{rel}: origin '{origin}' is not one of "
                f"{', '.join(sorted(VALID_ORIGINS))}.\n"
                f"    If it came from somewhere else, it does not belong in a public "
                f"repository."
            )

        recorded = entry.get("sha256")
        actual = sha256_of(path)
        if recorded and recorded != actual:
            errors.append(
                f"fixtures/{rel}: CONTENT CHANGED.\n"
                f"      recorded {recorded}\n"
                f"      actual   {actual}\n"
                f"    Fixtures are oracles and do not change to accommodate an "
                f"implementation.\n"
                f"    If this fixture is genuinely wrong, stop and escalate — see "
                f"AGENTS.md §3.\n"
                f"    A confirmed correction lands as its own commit with a "
                f"`fixture-change:` trailer\n"
                f"    and CODEOWNERS approval; `--update` is for *adding* fixtures, not "
                f"for silencing this."
            )

        size = path.stat().st_size
        if size > MAX_FIXTURE_BYTES:
            errors.append(
                f"fixtures/{rel}: {size // 1024} KB exceeds the {MAX_FIXTURE_BYTES // 1024} KB "
                f"guideline.\n"
                f"    A small fixture that isolates one edge case beats a large realistic "
                f"one — it is\n"
                f"    faster, easier to reason about when it fails, and its provenance is "
                f"clearer."
            )

    return errors


def update(fixtures_dir: Path, manifest_path: Path, manifest: dict[str, Any]) -> None:
    """Recompute hashes and stub entries for new fixtures.

    Deliberately does *not* fill in origin, licence, source, or verified_by:
    those are human claims about where a file came from, and a tool that guessed
    at them would turn the provenance requirement into a formality.
    """
    entries = {entry.get("path"): entry for entry in manifest.get("fixture", [])}
    lines: list[str] = []
    added: list[str] = []

    for path in fixture_files(fixtures_dir):
        rel = path.relative_to(fixtures_dir).as_posix()
        entry = entries.get(rel)
        digest = sha256_of(path)

        if entry is None:
            added.append(rel)
            entry = {
                "path": rel,
                "sha256": digest,
                "origin": "",
                "licence": "",
                "source": "",
                "added": "",
                "verified_by": "",
                "description": "",
            }
        else:
            entry = dict(entry)
            entry["sha256"] = digest

        lines.append("[[fixture]]")
        for field in ("path", "sha256", "origin", "licence", "source", "added", "verified_by"):
            lines.append(f'{field} = "{entry.get(field, "")}"')
        lines.append(f'description = "{entry.get("description", "")}"')
        lines.append("")

    header = manifest_path.read_text(encoding="utf-8").split("# [[fixture]]")[0].rstrip()
    body = "\n".join(lines).rstrip()
    manifest_path.write_text(f"{header}\n\n{body}\n", encoding="utf-8")

    if added:
        print(f"Stubbed {len(added)} new fixture entr(y/ies):")
        for rel in added:
            print(f"  {rel}")
        print(
            "\nFill in origin, licence, source, added, and verified_by by hand.\n"
            "`verified_by` names a person who looked at the file and believes it is what\n"
            "it says it is — it cannot be inferred, which is the point."
        )
    else:
        print("Hashes refreshed; no new fixtures.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="recompute hashes and stub entries for newly added fixtures",
    )
    # argv is a parameter so the test suite can call main([]) directly, rather
    # than shelling out or having pytest's own arguments parsed as ours.
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    fixtures_dir = repo_root / "fixtures"
    manifest_path = fixtures_dir / "provenance.toml"

    if not fixtures_dir.is_dir():
        print("No fixtures/ directory — nothing to check.")
        return 0

    manifest = load(manifest_path)

    if args.update:
        update(fixtures_dir, manifest_path, manifest)
        return 0

    errors = verify(fixtures_dir, manifest)
    if errors:
        print("Fixture gate failed:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}\n", file=sys.stderr)
        return 1

    count = len(manifest.get("fixture", []))
    print(f"Fixture gate passed: {count} fixture(s), hashes and provenance intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

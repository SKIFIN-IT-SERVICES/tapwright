# SPDX-License-Identifier: Apache-2.0

"""Licence gate: no dependency enters the tree unreviewed (INF-03, FW-REQ-017).

Three checks, each guarding a different way licence discipline fails in
practice:

1. **Every declared dependency has a manifest entry.** The realistic failure is
   not someone deliberately adding a GPL package; it is someone adding a
   convenient one without checking, because checking is boring. This makes not
   checking impossible rather than merely discouraged.

2. **No forbidden licence anywhere.** GPL/AGPL in an Apache-2.0 core is
   unrecoverable once it ships — it is not a bug you can patch out of the
   versions people already installed.

3. **No vendored copyleft source** (C-9, FW-REQ-019, HAL-08). ``python-can`` and
   ``asammdf`` are LGPL-3.0, which is fine as long as they stay *dependencies*.
   Copying their source into this tree converts the whole distribution into
   something the Apache-2.0 licence on the tin no longer describes.

    python tools/check_licences.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _toml import load  # noqa: E402

# Text that appears in the source of the copyleft packages we depend on. If it
# shows up in our tree, someone has copied source in rather than depending on it.
VENDORED_MARKERS = [
    r"GNU LESSER GENERAL PUBLIC LICENSE",
    r"GNU GENERAL PUBLIC LICENSE",
    r"This program is free software: you can redistribute it and/or modify",
]

# Where vendored source would plausibly land.
VENDOR_SUSPECTS = ["vendor", "_vendor", "third_party", "3rdparty", "external"]


def parse_requirement_name(spec: str) -> str:
    """Extract the package name from a PEP 508 requirement string."""
    return re.split(r"[<>=!~\[;\s]", spec.strip(), maxsplit=1)[0].strip().lower()


def declared_dependencies(pyproject: dict[str, Any]) -> set[str]:
    project = pyproject.get("project", {})
    specs: list[str] = list(project.get("dependencies", []))
    for extra_specs in project.get("optional-dependencies", {}).values():
        specs.extend(extra_specs)
    return {parse_requirement_name(spec) for spec in specs if parse_requirement_name(spec)}


def check_manifest_coverage(
    declared: set[str], manifest: dict[str, Any], errors: list[str]
) -> None:
    known = {entry["name"].lower() for entry in manifest.get("dependency", [])}
    for name in sorted(declared - known):
        errors.append(
            f"Dependency '{name}' is declared in pyproject.toml but has no entry in "
            f"licences.toml.\n"
            f"    Add one recording its licence, the date you verified it (from the "
            f"package's own\n"
            f"    metadata, not from memory), and what layer needs it."
        )


def check_licence_policy(manifest: dict[str, Any], errors: list[str]) -> None:
    policy = manifest.get("policy", {})
    allowed = set(policy.get("allowed", []))
    isolation_required = set(policy.get("isolation_required", []))
    forbidden = set(policy.get("forbidden", []))

    for entry in manifest.get("dependency", []):
        name = entry.get("name", "<unnamed>")
        licence = entry.get("licence")

        if not licence:
            errors.append(f"Dependency '{name}' in licences.toml has no licence recorded.")
            continue
        if not entry.get("verified"):
            errors.append(
                f"Dependency '{name}' has no `verified` date. A licence nobody checked "
                f"is an estimate,\n    and this project has already been burned twice by "
                f"estimates (see licences.toml header)."
            )

        if licence in forbidden:
            errors.append(
                f"Dependency '{name}' is {licence}, which is forbidden in this repository.\n"
                f"    Strong copyleft cannot enter the Apache-2.0 core in any form. If the "
                f"functionality\n"
                f"    is genuinely needed, it must be invoked across a process boundary "
                f"from the separate\n"
                f"    L4 repository — escalate rather than working around this."
            )
        elif licence in isolation_required:
            if entry.get("isolation") != "dependency-only":
                errors.append(
                    f"Dependency '{name}' is {licence} (weak copyleft) but is not marked "
                    f'`isolation = "dependency-only"`.\n'
                    f"    C-9 permits it only as an unmodified dependency installed from "
                    f"PyPI — never\n"
                    f"    vendored, forked, or frozen into a binary."
                )
        elif licence not in allowed:
            errors.append(
                f"Dependency '{name}' is {licence}, which is not in the allowed list.\n"
                f"    Add it to `policy.allowed` deliberately (a maintainer decision, per "
                f"CODEOWNERS)\n"
                f"    or choose a differently-licensed library."
            )


def check_no_vendored_copyleft(repo_root: Path, errors: list[str]) -> None:
    """C-9 / HAL-08: copyleft source must never be copied into this tree."""
    src = repo_root / "src"
    if not src.is_dir():
        return

    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()

        if any(part.lower() in VENDOR_SUSPECTS for part in path.parts):
            errors.append(
                f"{rel}: looks like vendored third-party source.\n"
                f"    Dependencies are installed from PyPI, not copied into the tree (C-9)."
            )
            continue

        if path.suffix not in {".py", ".pyi", ".txt", ".c", ".h"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for marker in VENDORED_MARKERS:
            if re.search(marker, text, flags=re.IGNORECASE):
                errors.append(
                    f"{rel}: contains copyleft licence text — this looks like vendored "
                    f"source.\n"
                    f"    python-can and asammdf are LGPL-3.0 and must stay dependencies, "
                    f"never copies (C-9)."
                )
                break


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []

    manifest = load(repo_root / "licences.toml")
    pyproject = load(repo_root / "pyproject.toml")

    check_manifest_coverage(declared_dependencies(pyproject), manifest, errors)
    check_licence_policy(manifest, errors)
    check_no_vendored_copyleft(repo_root, errors)

    if errors:
        print("Licence gate failed:\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}\n", file=sys.stderr)
        return 1

    count = len(manifest.get("dependency", []))
    print(f"Licence gate passed: {count} dependencies, all verified and within policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

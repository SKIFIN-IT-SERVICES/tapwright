# SPDX-License-Identifier: Apache-2.0

"""T0 gate: every source file carries an SPDX licence header (FW-REQ-050).

Apache-2.0 hygiene, and it makes the licence machine-checkable rather than a
claim in a README. Run over git-tracked files only, so a stray file in the
working tree does not fail the build.

    python tools/check_spdx.py            # check
    python tools/check_spdx.py --fix      # insert missing headers
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

EXPECTED = "SPDX-License-Identifier: Apache-2.0"

# Extension -> comment prefix. A file type we cannot comment in is a file type
# we do not check.
COMMENT_PREFIX = {
    ".py": "#",
    ".sh": "#",
    ".yml": "#",
    ".yaml": "#",
    ".toml": "#",
}

# Paths exempt from the header requirement. Kept deliberately short: every
# entry here is a hole in FW-REQ-050.
EXEMPT_PREFIXES = (
    "fixtures/",  # data, not source; provenance is tracked separately
    ".github/ISSUE_TEMPLATE/",
    ".github/dependabot.yml",  # generated-ish, and read by GitHub not by us
)

# How far into the file the header may appear. Shebangs and encoding
# declarations legitimately come first; a header on line 40 is not a header.
MAX_HEADER_LINE = 5


def tracked_files(repo_root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [repo_root / line for line in out.splitlines() if line]


def is_exempt(rel: str) -> bool:
    return any(rel.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def has_header(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8") as handle:
            for _, line in zip(range(MAX_HEADER_LINE), handle, strict=False):
                if EXPECTED in line:
                    return True
    except (UnicodeDecodeError, OSError):
        # Binary or unreadable: not a source file we can check.
        return True
    return False


def insert_header(path: Path, prefix: str) -> None:
    text = path.read_text(encoding="utf-8")
    header = f"{prefix} {EXPECTED}\n"
    lines = text.splitlines(keepends=True)

    # A shebang must stay on line 1.
    if lines and lines[0].startswith("#!"):
        lines.insert(1, header)
    else:
        lines.insert(0, header + "\n" if text.strip() else header)
    path.write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix", action="store_true", help="insert missing headers instead of failing"
    )
    # argv is a parameter so the test suite can call main([]) directly, rather
    # than shelling out or having pytest's own arguments parsed as ours.
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    missing: list[Path] = []

    for path in tracked_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        prefix = COMMENT_PREFIX.get(path.suffix)
        if prefix is None or is_exempt(rel) or not path.is_file():
            continue
        if has_header(path):
            continue
        if args.fix:
            insert_header(path, prefix)
            print(f"fixed: {rel}")
        else:
            missing.append(path)

    if missing:
        print(f"Missing SPDX header ({EXPECTED}) in {len(missing)} file(s):", file=sys.stderr)
        for path in missing:
            print(f"  {path.relative_to(repo_root).as_posix()}", file=sys.stderr)
        print("\nRun `python tools/check_spdx.py --fix` to insert them.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

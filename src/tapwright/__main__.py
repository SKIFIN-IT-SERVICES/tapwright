# SPDX-License-Identifier: Apache-2.0

"""Enables `python -m tapwright [pytest args...]` — the second of the two
invocation surfaces RUN-05 proves are identical (the other being the
installed `tapwright` console script). See `tapwright.runner.cli`.
"""

from __future__ import annotations

import sys

from tapwright.runner.cli import main

if __name__ == "__main__":
    sys.exit(main())

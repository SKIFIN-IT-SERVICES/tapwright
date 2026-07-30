"""Smoke test: the package installs and imports cleanly.

This is intentionally the only test today — it exists so CI is green from
the first commit and so `pip install -e .` failures are caught immediately.
Real tests land alongside real functionality starting Milestone M1; see
ROADMAP.md.
"""

import tapwright


def test_package_is_importable():
    assert tapwright.__version__


def test_layer_modules_are_importable():
    import tapwright.buses  # noqa: F401
    import tapwright.dbc_arxml  # noqa: F401
    import tapwright.diag  # noqa: F401
    import tapwright.hal  # noqa: F401
    import tapwright.report  # noqa: F401
    import tapwright.runner  # noqa: F401
    import tapwright.trace  # noqa: F401

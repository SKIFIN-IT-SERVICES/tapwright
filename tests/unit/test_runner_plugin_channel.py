# SPDX-License-Identifier: Apache-2.0

"""T1: the `bus`/`ecu` fixtures' channel is a config option, not a hardcoded
literal (RUN-01, TOOL-REQ-028) — matching HAL-01's "swap is a config change"
property, carried up to the fixture layer.

Tests `_resolve_channel()` directly rather than through a full pytester
sub-run: precedence logic (CLI option > env var > default) doesn't need a
live vcan interface to verify, so this stays in the fast T1 tier rather than
needing T2's `vcan` bring-up for a `--tapwright-channel` flag check.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from tapwright.runner.plugin import DEFAULT_CHANNEL, _resolve_channel


def _fake_request(cli_value: str | None) -> MagicMock:
    request = MagicMock()
    request.config.getoption.return_value = cli_value
    return request


def test_defaults_to_vcan0_with_no_cli_option_or_env_var(monkeypatch):
    monkeypatch.delenv("TAPWRIGHT_CHANNEL", raising=False)
    assert _resolve_channel(_fake_request(None)) == DEFAULT_CHANNEL == "vcan0"


def test_env_var_overrides_the_default(monkeypatch):
    monkeypatch.setenv("TAPWRIGHT_CHANNEL", "vcan7")
    assert _resolve_channel(_fake_request(None)) == "vcan7"


def test_cli_option_overrides_the_env_var(monkeypatch):
    monkeypatch.setenv("TAPWRIGHT_CHANNEL", "vcan7")
    assert _resolve_channel(_fake_request("vcan9")) == "vcan9"


def test_cli_option_is_registered_under_the_tapwright_group():
    """The --tapwright-channel flag actually exists as a pytest option, not
    just handled if someone happens to pass it — a typo'd or unregistered
    flag would otherwise fail with pytest's own "unrecognized arguments"
    rather than being silently ignored.
    """
    from tapwright.runner.plugin import pytest_addoption

    parser = MagicMock()
    group = MagicMock()
    parser.getgroup.return_value = group

    pytest_addoption(parser)

    parser.getgroup.assert_called_once_with("tapwright")
    group.addoption.assert_called_once()
    (option_name,), kwargs = group.addoption.call_args
    assert option_name == "--tapwright-channel"
    assert kwargs["default"] is None

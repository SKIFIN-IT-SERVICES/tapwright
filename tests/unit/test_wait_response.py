# SPDX-License-Identifier: Apache-2.0

"""T1 tests for `wait_for_response()` (RUN-10, `TOOL-REQ-029`).

Split out from `tests/integration/test_wait_helpers.py`: unlike
`wait_for_message()`/`wait_for_signal()`, `wait_for_response()` polls an
arbitrary callable, not a bus — no `vcan` needed, so these run as plain
unit tests rather than being needlessly gated behind `requires_vcan`.
"""

from __future__ import annotations

import pytest

from tapwright.runner.wait import WaitTimeoutError, wait_for_response


def test_wait_for_response_retries_the_callable_until_the_predicate_matches():
    calls = iter([1, 2, 3])
    result = wait_for_response(
        lambda: next(calls), predicate=lambda v: v == 3, timeout=1.0, poll_interval=0.01
    )
    assert result == 3


def test_wait_for_response_honors_poll_interval_bounding_call_count():
    calls = []

    def call():
        calls.append(1)
        return False

    with pytest.raises(WaitTimeoutError):
        wait_for_response(call, predicate=lambda v: v is True, timeout=0.2, poll_interval=0.05)

    # ~4 polls expected at 0.2s/0.05s; a wide band tolerant of CI scheduler
    # jitter, proving it isn't busy-looping (which would be hundreds of calls).
    assert 1 <= len(calls) <= 10


def test_wait_for_response_raises_wait_timeout_error_when_predicate_never_matches():
    with pytest.raises(WaitTimeoutError):
        wait_for_response(
            lambda: False, predicate=lambda v: v is True, timeout=0.2, poll_interval=0.05
        )

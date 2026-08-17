# SPDX-License-Identifier: Apache-2.0

"""The virtual UDS ECU responder (INF-05, `TOOL-REQ-026`).

Ships as part of the installed `tapwright` package — not repo-only tooling —
because `TOOL-REQ-026`'s acceptance criterion requires it: *"A `pip
install`-only user can run a full read-DID round trip against a simulated
ECU with zero hardware."* A `tools/`-only script could serve the CI-fixture
role but not that one, which is why this lives under `tapwright.diag` rather
than `tools/` — see `docs/inf-05-simulator-reuse-evaluation.md` and the
location note in `tests/differential/test_virtual_ecu_uds.py` for the full
reasoning and the correction history.

Layering, innermost first:

- `scenario.py` — data only: DIDs, DTCs, security levels, arbitration IDs,
  injected failures. No behaviour.
- `protocol.py` — the UDS state machine (`ProtocolState.handle_request`).
  No socket, thread, or bus code — this is what makes it testable at T1 on
  every platform, `vcan` or not.
- `transport.py` — binds `protocol.py` to a real `vcan` interface via
  `can-isotp`/`python-can`. T2/T3-only: needs a real interface.
- `ecu.py` — `VirtualECU`, the public class combining the two.
"""

from __future__ import annotations

from .ecu import VirtualECU
from .scenario import DTC, DIDConfig, FailureInjection, Scenario, SecurityLevelConfig

__all__ = [
    "DIDConfig",
    "DTC",
    "FailureInjection",
    "Scenario",
    "SecurityLevelConfig",
    "VirtualECU",
]

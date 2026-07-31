# SPDX-License-Identifier: Apache-2.0

"""L0 — Hardware abstraction.

One interface, many backends: SocketCAN, gs_usb (CANable/candleLight-class
devices), PEAK, Kvaser, Vector XL, TOSUN — via python-can — plus vcan for
zero-hardware CI and quick starts. Nothing above this layer branches on
interface vendor. See ARCHITECTURE.md at the repository root.

Only the SocketCAN backend (incl. vcan) is implemented so far, per
Milestone M1 — see ROADMAP.md.
"""

from .bus import Bus, open_bus
from .frame import Frame

__all__ = ["Bus", "Frame", "open_bus"]

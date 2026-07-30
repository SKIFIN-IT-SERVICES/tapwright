"""L0 — Hardware abstraction.

One interface, many backends: SocketCAN, gs_usb (CANable/candleLight-class
devices), PEAK, Kvaser, Vector XL, TOSUN — via python-can — plus vcan for
zero-hardware CI and quick starts. Nothing above this layer branches on
interface vendor. See ARCHITECTURE.md at the repository root.

Not yet implemented — this is scaffolding for Milestone M1.
"""

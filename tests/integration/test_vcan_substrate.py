# SPDX-License-Identifier: Apache-2.0

"""T2: the vcan substrate itself is up and usable (INF-02).

This is the trivial vcan test INF-02's exit criterion names — it verifies the
*runner*, not the product. Every T2/T3/T4 test that follows assumes a working
virtual bus; when a hundred of them fail at once, this one tells you whether the
cause is the bus or the code.

It is deliberately not a python-can test. python-can is not a dependency yet
(HAL-02 adds it), and this tier needs to work from the first commit of the
substrate rather than from the first commit of L0.
"""

from __future__ import annotations

import socket
import struct

import pytest

pytestmark = pytest.mark.requires_vcan

# SocketCAN frame: 4-byte ID, 1-byte DLC, 3 bytes padding, 8 bytes data.
CAN_FRAME_FMT = "=IB3x8s"
CAN_FRAME_SIZE = struct.calcsize(CAN_FRAME_FMT)


def test_vcan_interface_is_bindable(vcan_channel):
    """A raw CAN socket binds to the interface CI brought up."""
    with socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW) as sock:
        sock.bind((vcan_channel,))
        assert sock.getsockname()[0] == vcan_channel


def test_frame_sent_on_vcan_is_received(vcan_channel):
    """A frame written to vcan comes back byte-identical on a second socket.

    vcan loops frames back to all bound sockets, which is what makes it a real
    bus for test purposes rather than a stub — a sender and a receiver in the
    same suite genuinely exchange frames through the kernel.
    """
    can_id = 0x123
    payload = b"\xde\xad\xbe\xef"

    with socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW) as receiver:
        receiver.bind((vcan_channel,))
        receiver.settimeout(2.0)

        with socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW) as sender:
            sender.bind((vcan_channel,))
            sender.send(struct.pack(CAN_FRAME_FMT, can_id, len(payload), payload))

        frame = receiver.recv(CAN_FRAME_SIZE)

    received_id, dlc, data = struct.unpack(CAN_FRAME_FMT, frame)
    assert received_id == can_id
    assert dlc == len(payload)
    assert data[:dlc] == payload

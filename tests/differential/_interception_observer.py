# SPDX-License-Identifier: Apache-2.0

"""A standalone third-party observer process for DIAG-05's test suite.

Deliberately imports **nothing** from `tapwright` — this script simulates an
external tool (a future Gallia-based fuzzer, in a separate repository, per
ADR-004) that only ever speaks the plain newline-delimited-JSON protocol
over a TCP socket. If this script needed a `tapwright` import to work, the
interception point wouldn't actually be usable "without forking," which is
the whole point of DIAG-05.

Connects once and stays connected for the rest of the session (matching
realistic fuzzer usage — attach once, observe/mutate many messages), reading
one published message at a time in a loop until the connection closes or
`--messages` is exhausted.

Usage (spawned as a subprocess by the test suite, never imported directly):

    python _interception_observer.py <port> --messages N [--replace TYPE:HEX]

`--messages N`: exit after N messages (0 = until the connection closes).
`--replace TYPE:HEX`: for a published message of `"type": TYPE`
    ("request"/"response"), reply with a `replace` action substituting the
    given hex payload. Every other message type is passed through
    unmodified (an `observe` reply). Repeatable.
`--silent`: never reply to anything — simulates an unresponsive observer.
`--garbage`: reply with invalid JSON to everything — simulates a
    misbehaving observer.

Prints one line of JSON per message received, so the test process (reading
this script's stdout) can assert on exactly what the interception point
published, independent of what this script did in response.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("--messages", type=int, default=0)
    parser.add_argument("--replace", action="append", default=[])
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--garbage", action="store_true")
    args = parser.parse_args()

    replacements = dict(item.split(":", 1) for item in args.replace)

    with socket.create_connection(("127.0.0.1", args.port), timeout=5.0) as sock:
        sock.settimeout(5.0)
        buffer = b""
        received = 0
        while args.messages == 0 or received < args.messages:
            while b"\n" not in buffer:
                chunk = sock.recv(4096)
                if not chunk:
                    return 0  # peer closed the connection
                buffer += chunk
            line, _, buffer = buffer.partition(b"\n")
            received += 1
            message = json.loads(line.decode())
            print(json.dumps(message), flush=True)

            if args.silent:
                continue
            if args.garbage:
                sock.sendall(b"not valid json at all\n")
                continue

            message_type = message.get("type")
            if message_type in replacements:
                reply = {"action": "replace", "data": replacements[message_type]}
            else:
                reply = {"action": "observe"}
            sock.sendall((json.dumps(reply) + "\n").encode())

    return 0


if __name__ == "__main__":
    sys.exit(main())

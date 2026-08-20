# SPDX-License-Identifier: Apache-2.0
#
# RUN-08 / FW-REQ-021: a container image published alongside the PyPI
# package, day one -- ADR-001's "one package, no separate CI build
# artifact" property, demonstrated by `quickstart.py` at container start.
#
#     docker build -t tapwright .
#     docker run --rm --cap-add=NET_ADMIN --cap-add=NET_RAW tapwright

FROM python:3.10-slim

# iproute2: quickstart.py's `ip link add vcan0 ...` at container start.
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

# Runs as root -- deliberately, not an oversight. Two things were tried and
# rejected first:
#   1. `USER <non-root>` alone: `docker run --cap-add=NET_ADMIN` grants the
#      capability to the container's bounding set, not to a non-root
#      process's own inheritable/effective set at exec time -- fails with
#      "RTNETLINK answers: Operation not permitted".
#   2. `setcap cap_net_admin,cap_net_raw+eip` on the `ip` binary at build
#      time, to hand the capability to that one binary regardless of UID:
#      fails with "Invalid file 'setcap' for capability operation" -- a
#      known Docker overlay-filesystem limitation on security.capability
#      xattrs not persisting reliably across a build layer.
# A privileged-entrypoint-then-drop-to-non-root wrapper (su/gosu) is the
# standard fix for a persistent service; this is a one-shot script that
# exits after one round-trip, not a long-running process, so that
# machinery's cost isn't earning its keep yet -- noted as a real
# improvement if this image grows a long-running mode later, not silently
# dropped.
ENTRYPOINT ["python", "quickstart.py"]

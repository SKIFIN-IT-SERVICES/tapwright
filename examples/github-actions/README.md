# GitHub Actions example (RUN-06)

A minimal, standalone, cold-clone-able example of testing UDS diagnostics
with `tapwright` in GitHub Actions — no hardware, no bench, no licensed
tooling.

## What's here

- `test_vin_read.py` — the entire test a consumer writes: one function,
  reading a DID from `tapwright`'s own virtual ECU via `TOOL-REQ-028`'s
  `uds` pytest fixture. No `hal.Bus`, no `VirtualECU`, no connection
  wiring — that's the point.
- `requirements.txt` — installs `tapwright` (from this repository's git
  URL for now; `tapwright` isn't published to PyPI yet).
- `.github/workflows/test.yml` — the copy-pasteable workflow: 1 job, 5
  steps, a stock `ubuntu-latest` runner. Copy this file (adjusted for your
  own project layout) into your own repository's `.github/workflows/`.

## Try it yourself

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0
pytest
```

## The benchmark

`docs/run-06-benchmark.md` (repository root) compares this workflow
against Vector's own public CI reference, `vectorgrp/ci-siltest-demo`.

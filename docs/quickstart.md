# Quickstart

A real, runnable example against `tapwright`'s own current API — verified
by `doctest` in CI (INF-08, `FW-REQ-066`), not just prose that could
silently drift out of date.

## Decode a CAN frame from a DBC file

No hardware, no `vcan`, no network — just a DBC file and a frame's raw
bytes. This uses the same golden fixture and expected values as
`tests/differential/test_dbc_decode.py`'s own oracle
(`fixtures/expected/dbc_multiplexed_engine_data.json`), so this example
and the test suite can never silently disagree with each other.

```
>>> from tapwright.dbc_arxml import load_dbc
>>> from tapwright.hal import Frame
>>> db = load_dbc("fixtures/databases/multiplexed.dbc")
>>> frame = Frame(arbitration_id=100, data=bytes.fromhex("a00f640000000000"))
>>> decoded = db.decode(frame)
>>> decoded["EngineSpeed"]
1000.0
>>> decoded["EngineTemp"]
60

```

`EngineSpeed`'s raw value (`0x0FA0` = 4000) is scaled by `0.25` to `1000.0`
rpm; `EngineTemp`'s raw value (`100`) has a `-40` offset applied to `60`
degC — both declared directly in the DBC file, not hand-computed here.

## Next steps

- [`README.md`](README.md) — project overview.
- [`docs/architecture.md`](architecture.md) — the L0–L3 module layout this
  example's `dbc_arxml`/`hal` imports live in.
- [`docs/tooling-requirements.md`](tooling-requirements.md) — the full
  requirements catalog this and every other example traces back to.

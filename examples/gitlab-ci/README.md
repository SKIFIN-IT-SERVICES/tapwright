# GitLab CI example (RUN-07)

A minimal, standalone example of testing UDS diagnostics with `tapwright`
on GitLab CI — no hardware, no bench, no licensed tooling. Mirrors
[`examples/github-actions/`](../github-actions/) (RUN-06) as closely as
GitLab's syntax allows.

## What's here

- `test_vin_read.py` — identical content to RUN-06's own test: one
  function, reading a DID from `tapwright`'s own virtual ECU via
  `TOOL-REQ-028`'s `uds` pytest fixture.
- `requirements.txt` — installs `tapwright` (from this repository's git
  URL for now; `tapwright` isn't published to PyPI yet).
- `.gitlab-ci.yml` — the copy-pasteable pipeline: one `test` job, a stock
  `python:3.10` image.

## Important: not verified on real GitLab CI

Unlike RUN-06's GitHub Actions example — which this repository's own CI
actually runs on every push, proving "goes green from a cold clone" for
real — **this example has not been run against a real GitLab CI
pipeline.** No GitLab account or project was available to do that.

What *is* verified, mechanically, in this repository's own CI:
- `test_vin_read.py`'s core logic matches RUN-06's own proven GitHub
  Actions example — no drift between the two platforms' examples.
- `.gitlab-ci.yml` is valid YAML and validates against
  [GitLab's own official JSON Schema](https://gitlab.com/gitlab-org/gitlab-foss/-/raw/master/app/assets/javascripts/editor/schema/ci.json)
  for the format — the same schema GitLab's own web IDE editor uses.
  (GitLab's public CI Lint API's no-account global endpoint was removed
  in GitLab 16.0 — confirmed directly while building this example —
  so schema validation against GitLab's own official schema is the
  closest real, no-account equivalent still available.)
  Neither is a pipeline run.

## The open question, for whoever has real GitLab access to confirm

GitLab.com's shared runners default to Docker-executor containers,
unlike GitHub Actions' bare-VM `ubuntu-latest` runners (where
`tapwright`'s own `bring-up-vcan` composite action's `sudo modprobe`/
`ip link` commands work directly against the host kernel). `vcan` only
needs the `NET_ADMIN` capability to auto-load — it's a netdev module, not
an arbitrary kernel module needing full privileged/Docker-in-Docker mode
— but whether `NET_ADMIN` is available to a job on GitLab.com's *shared*
runner fleet, versus only configurable by a self-hosted runner's own
admin, could not be confirmed without an actual account to test against.

If you run this pipeline and the `before_script` step fails at
`modprobe vcan` or `ip link add` with a permission error, that is almost
certainly why — please open an issue so this note (and the pipeline
itself, if a workaround exists) can be corrected with real data instead
of this documented uncertainty.

## Try it yourself (locally, or on a self-hosted runner)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0
pytest
```

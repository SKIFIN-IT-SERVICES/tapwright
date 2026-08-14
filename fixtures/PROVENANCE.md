<!-- SPDX-License-Identifier: Apache-2.0 -->

# The fixture corpus

This directory is not test scaffolding. It is the **oracle library**: the
accumulated, independently-authored authority on what correct output looks like.
Every differential (T3) and property (T4) test in the project ultimately points
at something in here.

It is also the most valuable artifact the project builds, in a specific sense —
the implementation is comparatively cheap and can be rewritten; the corpus is
what makes it possible to know the rewrite is correct. Investment here compounds
across every subsequent loop.

Two rules govern it, and they pull in opposite directions on purpose: fixtures
must be **hard to change** (§1) and **impossible to add carelessly** (§2).

```
fixtures/
├── provenance.toml    the manifest — every file below has an entry
├── databases/         golden DBC / ARXML / LDF / A2L
├── traces/            recorded BLF / ASC / MDF4
├── expected/          known-good decode outputs, as JSON
└── odx/               sample PDX packages
```

## 1. Fixtures are immutable

**Never edit a fixture or an expected output to make a failing test pass.**
Full reasoning in [`AGENTS.md`](../AGENTS.md) §3 and [`PROCESS.md`](../PROCESS.md)
step 3; the short version is that a failing differential test is the process
*working*, and editing the expected value doesn't fix the bug — it deletes the
only thing that would ever have caught it, permanently and invisibly.

`tools/check_fixtures.py` records a SHA-256 for every file here and fails CI if
any of them changes. `CODEOWNERS` requires maintainer approval on this
directory. Both are backstops; the rule holds regardless.

**When a fixture is genuinely wrong** — and some will be — escalate, get it
confirmed by someone who didn't write the code under test, then land the change
as its own commit with a `fixture-change:` trailer:

```
fix(fixtures): correct expected scaling on EngineSpeed

The expected value assumed a 0.25 rpm/bit factor; the DBC declares 0.125.
Re-derived by hand from the raw frame bytes in the trace and cross-checked
against cantools' own decode, which agrees with 0.125.

fixture-change: fixtures/expected/engine_speed.json — expected value was wrong,
re-verified by hand from raw bytes and independently against cantools
```

Never bundled into the commit that needed it to pass.

## 2. Every fixture carries provenance

Add a file here and `provenance.toml` needs an entry for it in the same commit,
or CI fails. The manifest records where the file came from, under what licence,
who verified it, and what it is *for*.

This is not bureaucracy. Two distinct risks:

- **Legal.** Shipping an OEM-proprietary DBC or PDX in a public Apache-2.0
  repository is a serious problem — the kind that ends design-partner
  relationships and cannot be undone by deleting the file later, because the git
  history keeps it. It is also exactly the kind of thing that happens while
  someone is looking for "a realistic test fixture", with no bad intent
  whatsoever. **No customer data, ever, regardless of how good a fixture it
  would make.**
- **Epistemic.** An expected output nobody can explain the origin of is not an
  oracle. If we can't say how a value was derived, we can't say it's right, and
  a test asserting it proves nothing.

Preference order for sourcing:

1. **Self-generated on `vcan`** — traces we recorded ourselves. Licensing is
   unambiguous and the content is known by construction. Prefer this.
2. **Self-authored** — a DBC written by hand to exercise a specific edge case
   (multiplexing, extended IDs, negative offsets, scaling boundaries). Nearly as
   good, and usually a better test.
3. **Openly-licensed public samples** — with the licence and URL recorded, and
   the licence actually read.
4. **Anything else** — no.

### Manifest entry

```toml
[[fixture]]
path = "databases/multiplexed.dbc"
sha256 = "..."                      # tools/check_fixtures.py --update computes this
origin = "self-authored"            # self-authored | self-generated | public-sample
licence = "Apache-2.0"
source = "Written for BUS-01; no external source"
added = "2026-08-14"
verified_by = "handle-of-a-human"
description = "Multiplexed signals with a 2-bit multiplexor, to exercise cantools' multiplex handling"
```

`verified_by` names a **person**, not a tool or an agent. It is a claim that a
human looked at this and believes it is what it says it is. For an expected
output it means specifically: *this value was derived independently of the
implementation it will be used to test, and I can explain how.*

### Expected outputs

Files under `expected/` are held to the stricter standard, because they are the
oracle in its purest form:

- **Human-verified at creation.** Derived by hand, from a specification, or from
  a reference library invoked directly — never by running our implementation and
  saving what came out. That last one produces a test that asserts the code does
  what the code does, which passes forever and detects nothing.
- **Never regenerated to match code.** There is no `--regenerate` flag, and
  adding one would be a mistake.
- Record the derivation method in `description`. "Decoded by `cantools` 39.4.0
  directly" and "computed by hand from ISO 14229 §9.2" are both good;
  "generated" is not.

## 3. Adding a fixture

```bash
# 1. add the file, then record it
python tools/check_fixtures.py --update    # computes hashes, stubs missing entries

# 2. fill in origin / licence / source / verified_by / description by hand —
#    --update deliberately cannot infer these

# 3. verify
python tools/check_fixtures.py
```

Keep fixtures small and pointed. A 40 MB real-world trace is worse than a 4 KB
one that isolates the edge case being tested: it is slower, it is harder to
reason about when it fails, and its provenance is usually murkier.

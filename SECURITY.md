# Security Policy

Tapwright talks to real vehicle networks and real ECUs. We take security
reports seriously, including reports about the tool itself (not just the
vehicles it tests).

## Supported Versions

Tapwright is pre-release (pre-`v0.1`). Until a `1.0` is tagged, only the
latest commit on `main` is supported — there is no LTS branch yet.

| Version | Supported |
| ------- | --------- |
| `main`  | ✅ |
| anything else | ❌ |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting instead:

1. Go to the [Security tab](https://github.com/SKIFIN-IT-SERVICES/tapwright/security).
2. Click **"Report a vulnerability"**.
3. Describe the issue, the affected version/commit, and — if possible —
   reproduction steps.

This opens a private advisory visible only to maintainers until a fix is
ready, so a vulnerability isn't disclosed before it's patched.

We aim to acknowledge reports within 5 business days. Fix timelines depend
on severity — a security issue in the L2 diagnostics engine (the layer a
future fuzzing/security-testing feature will build on) is treated as
higher priority than a cosmetic reporting bug.

## Scope

In scope: the Tapwright codebase itself (parsing, protocol handling,
report generation, CI tooling shipped in this repository).

Out of scope: vulnerabilities in vehicles, ECUs, or third-party hardware
that Tapwright happens to be pointed at when you found the issue — please
report those to the vehicle/component manufacturer instead.

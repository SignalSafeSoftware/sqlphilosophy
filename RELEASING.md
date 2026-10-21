# Releasing `sqlphilosophy`

The source prepares **0.3.4**. This is an approval candidate, not a declaration
that publication happened. Repository: [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy).

## Checks and artifacts

```sh
uv sync --frozen --extra dev
uv lock --check
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src --install-types --non-interactive
uv run bandit -r src -q
uv run pytest -q
uv run python scripts/smoke_package.py
```

The smoke script builds wheel/sdist, validates metadata, installs the actual wheel
in a clean environment, and verifies public imports and `py.typed`. Inspect both
archives for source/metadata ownership before approving their hashes.
Run both SQLite examples (`docs/examples/typed_repository_sync.py` and
`docs/examples/typed_repository_async.py`) and verify SQLAlchemy 2.0.49 and 2.1.5
in separate disposable environments. Keep host SQLAlchemy constraints unchanged.

Build dependencies use setuptools `>=84.2.1,<85` and wheel `>=0.46,<1`.
They are build tools, not runtime dependencies. The source version, built metadata,
imported version and approved tag must agree; do not select a tag from a dirty checkout.

## Coordinated unpublished dependencies

For release preparation, test exact built upstream archives in disposable consumers.
A candidate dependency need not already exist in the public registry. Do not invent
registry URLs/hashes, commit temporary local source overrides, or claim a stale lock
passed frozen verification. Publish approved upstream packages first; regenerate
this repository's real registry lock, rerun frozen CI and installed-artifact checks,
and verify the runtime payload matches the reviewed candidate before dependent publication.

## Existing workflow interfaces

`.github/workflows/ci.yml` runs checks/tests on PRs. Same-repository PRs scan only
with the `scan` label; forks receive no scanner secret. Pushes to `main`, `v*`
tags and manual dispatch run scanning. Release requires successful checks, tests,
scan and package smoke; a skipped/failed scan cannot publish.

**Manual dispatch on `main` is a publishing action.** It is not a check-only preview.
After explicit release approval and all required checks, use the exact approved
`v0.3.4` tag on the reviewed main commit (or the existing approved main dispatch).
A PR, release note or this file does not itself authorize tag creation or upload.
Do not retag or retry a version until registry readback proves whether it exists.

## Publisher identity and verification

Existing PyPI trusted publisher: owner `SignalSafeSoftware`, repository `sqlphilosophy`,
workflow `ci.yml`, environment `pypi`. GitHub grants `id-token: write` only to the
publish job. Scanner configuration uses `PACKAGES_SONAR_TOKEN`; no credential
values belong in docs, build artifacts or review packets. Automatic Sonar analysis
must remain off because CI submits coverage-backed analysis.

After publication, read back wheel/sdist and metadata from PyPI, check version,
license, dependencies, imports and runtime/source hashes, then update the coordinated
consumer locks. Registry success and host adoption/deployment are separate evidence.

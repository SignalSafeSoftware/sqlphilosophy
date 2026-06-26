# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-06-26

### Changed

- Track `uv.lock` for reproducible CI; restore `--frozen` installs in CI.
- Exclude `scripts/*` from coverage metrics (pytest-cov and Sonar).

### Fixed

- CI `uv export --frozen` without a tracked lockfile.

## [0.1.0] - 2026-06-26

### Added

- Initial public release on PyPI as `sqlphilosophy`.
- Explicit sync API: `sqlphilosophy.sync.repository`, `sqlphilosophy.sync.query`, `sqlphilosophy.sync.protocols`.
- Explicit async API: `sqlphilosophy.aio.repository`, `sqlphilosophy.aio.query`, `sqlphilosophy.aio.protocols`.
- Shared modules: `sorting`, `sql`, `types`, `audit` (context, listener, model).
- No root-level reexports; compatibility shim modules removed.
- `SECURITY.md`, Dependabot, production-readiness documentation updates.

### Changed

- README boundaries and SQL/destructive helper documentation (Batch 4).

### CI

- Checks and tests on every PR; Sonar **`scan`** is label-gated on PRs and runs on tag push and manual dispatch (Batch 1).
- Publish only from manual **`main`** dispatch or **`v*`** tags (not PR labels); publish requires **`checks`**, **`tests`**, and **`scan`**.

### Documentation

- [RELEASING.md](./RELEASING.md) aligned with current **CI** publish job (not a separate `publish.yml`).

[Unreleased]: https://github.com/SignalSafeSoftware/sqlphilosophy/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/SignalSafeSoftware/sqlphilosophy/releases/tag/v0.1.1
[0.1.0]: https://github.com/SignalSafeSoftware/sqlphilosophy/releases/tag/v0.1.0

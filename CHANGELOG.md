# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-10

### Added

- Initial public release on PyPI as `sqlphilosophy`.
- Explicit sync API: `sqlphilosophy.sync.repository`, `sqlphilosophy.sync.query`, `sqlphilosophy.sync.protocols`.
- Explicit async API: `sqlphilosophy.aio.repository`, `sqlphilosophy.aio.query`, `sqlphilosophy.aio.protocols`.
- Shared modules: `sorting`, `sql`, `types`, `audit` (context, listener, model).
- No root-level reexports; compatibility shim modules removed.

[0.1.0]: https://github.com/SignalSafeSoftware/sqlphilosophy/releases/tag/v0.1.0

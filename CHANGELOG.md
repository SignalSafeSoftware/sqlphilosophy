# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.2.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.9] - 2026-07-09

### Added

- **`sqlphilosophy.trusted_sql`** — developer-trusted SQL fragment helpers (`sql_table`, `col_eq`, `col_icontains`, `col_range`, order helpers); re-exported from `sqlphilosophy.sql` for compatibility.
- **Documentation site under `docs/`** — [repository guide](./docs/repository-guide.md), [feature matrix](./docs/feature-matrix.md), and focused usage pages under [`docs/usage/`](./docs/usage/).
- **Strongly typed repository guide** — [`docs/usage/strongly-typed-repositories.md`](./docs/usage/strongly-typed-repositories.md) (protocols, factories, service patterns).
- **Before/after SQLAlchemy guide** — [`docs/usage/before-after-sqlalchemy.md`](./docs/usage/before-after-sqlalchemy.md) (sync/async migration examples for SELECT/INSERT/UPDATE/DELETE).
- Runnable typed repository demos moved to [`docs/examples/typed_repository_sync.py`](./docs/examples/typed_repository_sync.py) and [`docs/examples/typed_repository_async.py`](./docs/examples/typed_repository_async.py) (factory caching, `ListQuery`, `SortConfig`, cross-repo `for_repo`).
- CI **docs example validation** in the `smoke-package` job.

### Changed

- README rewritten as a concise entry point linking to the expanded docs.
- **Ruff** replaces Flake8 for lint/format (`pyproject.toml`, CI, RELEASING); removed `.flake8`.
- Shared partial-update planning in `_repository_shared.PartialUpdatePlan`; production `assert` replaced with explicit validation/errors.
- Expanded unit tests; removed coverage-chasing test modules; **100%** coverage retained.

### Documentation

- Usage pages for setup, reads, writes, deletes, query builder, sorting, mapping helpers, SQL helpers, trusted SQL, audit, and typing aliases.
- Feature matrix links each API group to practical usage examples.

## [0.1.8] - 2026-07-09

### Added

- `BaseRepositoryProtocol` and `AsyncBaseRepositoryProtocol` — full CRUD surface for typed repository subclasses.
- Runnable strongly typed repository examples: [`docs/examples/typed_repository_sync.py`](./docs/examples/typed_repository_sync.py) and [`docs/examples/typed_repository_async.py`](./docs/examples/typed_repository_async.py).
- README section on the strongly typed repository + factory pattern.

### Changed

- `AsyncBaseRepository` now accepts a second type parameter (`U`) for the factory type, matching sync `BaseRepository[T, U]`.
- Repository and protocol session/factory attributes are `_session` and `_factory` (replacing public `session` on implementations).
- `RepositoryFactory` / `AsyncRepositoryFactory` `get_repository()` and `for_repo()` typing tightened with `cast` for domain repo constructors.
- `.flake8` config (`max-line-length=120`) aligned with CI.

### Fixed

- `test_row_mapping_unwraps_duck_typed_entity` patches `sqlphilosophy.sql.sa_inspect` (the code path `row_mapping` actually uses).

### CI

- Bump GitHub Actions: `setup-uv` 8.3.0, `github-script` 9, Sonar scan action 8.2.0; bump dev dependency `greenlet` 3.5.3.

## [0.1.3] - 2026-06-28

### Changed

- CI: pass Sonar token for package scans; pin GitHub Actions to reviewed SHAs; bump official action majors (`checkout`, `setup-python`, `upload-artifact`, `download-artifact`, `setup-uv`).
- Package smoke script: tighten sdist contents audit (required metadata files; exclude tests from sdist).

### Fixed

- Replace `tar` subprocess with stdlib `tarfile` in `scripts/smoke_package.py` (Bandit B607/B603).

## [0.1.2] - 2026-06-26

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
- Expanded unit test coverage.
- Package artifact smoke test (`scripts/smoke_package.py`).

### Changed

- README boundaries and SQL/destructive helper documentation (Batch 4).

### CI

- Checks and tests on every PR; Sonar **`scan`** is label-gated on PRs and runs on tag push and manual dispatch (Batch 1).
- Publish only from manual **`main`** dispatch or **`v*`** tags (not PR labels); publish requires **`checks`**, **`tests`**, and **`scan`**.

### Documentation

- [RELEASING.md](./RELEASING.md) aligned with current **CI** publish job (not a separate `publish.yml`).

[Unreleased]: https://github.com/SignalSafeSoftware/sqlphilosophy/compare/v0.1.9...HEAD
[0.1.9]: https://github.com/SignalSafeSoftware/sqlphilosophy/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/SignalSafeSoftware/sqlphilosophy/compare/v0.1.7...v0.1.8
[0.1.3]: https://github.com/SignalSafeSoftware/sqlphilosophy/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/SignalSafeSoftware/sqlphilosophy/releases/tag/v0.1.2
[0.1.0]: https://github.com/SignalSafeSoftware/sqlphilosophy/releases/tag/v0.1.0

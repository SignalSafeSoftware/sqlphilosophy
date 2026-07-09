# Releasing `sqlphilosophy`

Standalone repository: [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy).

## CI publish policy

- **Checks and tests** run on every pull request.
- **`scan` (SonarCloud)** on pull requests is **optional** — it runs only when the PR has the **`scan`** label. On **`push`** (including **`v*`** tag pushes) and **`workflow_dispatch`**, **`scan`** runs automatically.
- **Fork pull requests never run `scan`** — secrets are not exposed to untrusted code.
- **Publish does not run** from pull requests.
- **Publish runs** when:
  - **Manual:** GitHub Actions → **CI** → **Run workflow** on branch **`main`**, or
  - **Tag:** push a semver tag matching `v*` (for example `vX.Y.Z`).
- **Publish requires** successful **`checks`**, **`tests`**, **`scan`**, and **`smoke-package`** jobs in the same workflow run (see [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)). **`scan` must succeed** — a skipped or failed scan blocks release.
- On publish events (`workflow_dispatch` on **`main`** or **`v*`** tag push), **`scan` always runs**; if **`PACKAGES_SONAR_TOKEN`** is missing, the workflow fails at a preflight step with an explicit error.
- Pushing a **`v*`** tag starts a workflow run where **`checks`**, **`tests`**, and **`scan`** run before **Publish** can proceed.
- **GitHub Releases do not trigger publish** in the current workflow.
- **PyPI trusted publishing** uses GitHub Environment **`pypi`**. npm-style provenance and npm Environment approval do not apply.

### SonarCloud secret

This org uses a shared SonarCloud token secret named **`PACKAGES_SONAR_TOKEN`** (not `SONAR_TOKEN`). Configure it at the organization or repository level. The scan job maps it to the conventional `SONAR_TOKEN` environment variable expected by the SonarCloud action.

## Before you release

1. Bump version in [`src/sqlphilosophy/VERSION`](./src/sqlphilosophy/VERSION) (single line, semver).
2. Update [CHANGELOG.md](./CHANGELOG.md) (`[Unreleased]` → new version section when tagging).
3. Run locally (matches CI checks):

   ```bash
   uv sync --extra dev
   uv lock --check
   uv run ruff check src tests docs/examples
   uv run ruff format --check src tests docs/examples
   uv run mypy src --install-types --non-interactive
   uv run bandit -r src -q -x ./tests,./.venv
   uv run pytest -q
   uv run --extra dev python docs/examples/typed_repository_sync.py
   uv run --extra dev python docs/examples/typed_repository_async.py
   uv run python -m build
   uv run twine check dist/*
   ```

4. Run artifact smoke test: `uv run python scripts/smoke_package.py` (build, `twine check`, wheel install, import/`py.typed` checks — enforced in CI before publish).

## Publish

1. Commit the version and changelog updates on **`main`**:

   ```bash
   git add src/sqlphilosophy/VERSION CHANGELOG.md
   git commit -m "Release vX.Y.Z"
   git push origin main
   ```

2. Tag and push (recommended — triggers **Publish** when required jobs succeed):

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

   **Option B — Manual dispatch:** merge release commits to **`main`**, then GitHub → **Actions** → **CI** → **Run workflow** (branch **`main`**). Ensure [`VERSION`](./src/sqlphilosophy/VERSION) matches the tag you intend to ship.

## After publish

```bash
pip index versions sqlphilosophy
```

CI runs `scripts/smoke_package.py` before publish.

## One-time PyPI setup

1. Register **`sqlphilosophy`** on PyPI.
2. On PyPI → project **Publishing** → **Add a new pending publisher**, configure **exactly**:

   | Field | Value |
   | ----- | ----- |
   | Project name | `sqlphilosophy` |
   | Publisher platform | GitHub Actions |
   | Owner | `SignalSafeSoftware` |
   | Repository name | `sqlphilosophy` |
   | Workflow filename | `ci.yml` |
   | Environment name | `pypi` |

   Use `ci.yml` only — not `.github/workflows/ci.yml`. The workflow filename must match the OIDC claim `SignalSafeSoftware/sqlphilosophy/.github/workflows/ci.yml`.

3. Create GitHub Environment **`pypi`** in [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy/settings/environments) (no secrets required for trusted publishing).

If publish fails with `invalid-publisher: valid token, but no corresponding publisher`, PyPI has no publisher matching the workflow claims. Fix the PyPI publisher table above, then **Re-run** the failed workflow — do not bump the version or retag unless `0.1.2` was actually uploaded.

## Manual upload (fallback)

Only if CI publish is unavailable:

```bash
uv run python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-api-token> uv run twine upload dist/*
```

Use a project-scoped API token.

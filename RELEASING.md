# Releasing `sqlphilosophy`

Standalone repository: [SignalSafeSoftware/sqlphilosophy](https://github.com/SignalSafeSoftware/sqlphilosophy).

## CI publish policy

- **Checks and tests** run on every pull request.
- **`scan` (Sonar)** on pull requests is **optional** — it runs only when the PR has the **`scan`** label. On **`push`** (including **`v*`** tag pushes) and **`workflow_dispatch`**, **`scan`** runs automatically.
- **Publish does not run** from PR labels.
- **Publish runs** when:
  - **Manual:** GitHub Actions → **CI** → **Run workflow** on branch **`main`**, or
  - **Tag:** push a semver tag matching `v*` (for example `vX.Y.Z`).
- **Publish requires** successful **`checks`**, **`tests`**, and **`scan`** jobs in the same workflow run (see [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)).
- Pushing a **`v*`** tag starts a workflow run where **`checks`**, **`tests`**, and **`scan`** run before **Publish** can proceed.
- **GitHub Releases do not trigger publish** in the current workflow.
- **PyPI trusted publishing** uses GitHub Environment **`pypi`**. npm-style provenance and npm Environment approval do not apply.

## Before you release

1. Bump version in [`src/sqlphilosophy/VERSION`](./src/sqlphilosophy/VERSION) (single line, semver).
2. Update [CHANGELOG.md](./CHANGELOG.md) (`[Unreleased]` → new version section when tagging).
3. Run locally:

   ```bash
   uv sync --extra dev
   uv run pytest
   uv run python -m build
   uv run twine check dist/*
   ```

4. **Future required gate (not yet in CI):** install the wheel in a clean venv and smoke-test documented imports (Batch 6).

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

Wheel install smoke tests are planned but not yet required in CI (Batch 6).

## One-time PyPI setup

1. Register **`sqlphilosophy`** on PyPI.
2. Configure **trusted publishing** for owner `SignalSafeSoftware`, repository `sqlphilosophy`, workflow **`ci.yml`**, environment **`pypi`**.
3. Create GitHub Environment **`pypi`**.

## Manual upload (fallback)

Only if CI publish is unavailable:

```bash
uv run python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-api-token> uv run twine upload dist/*
```

Use a project-scoped API token.

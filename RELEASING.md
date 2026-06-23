# Releasing sqlphilosophy

This directory is the **publishable Python package** (`pip install sqlphilosophy`). It can ship as a standalone public GitHub repository and to PyPI.

## One-time setup

### 1. Create the public GitHub repository

From the monorepo root (or after running `scripts/export-sqlphilosophy-standalone.sh`):

```bash
gh repo create SignalSafeSoftware/sqlphilosophy --public --source=. --remote=origin --push
```

Recommended remote: `https://github.com/SignalSafeSoftware/sqlphilosophy`

The standalone export includes `.github/workflows/ci.yml` and `publish.yml`.

### 2. Register the PyPI project

1. Create an account at [pypi.org](https://pypi.org) if needed.
2. Reserve the project name **`sqlphilosophy`** (must match `pyproject.toml` `[project].name`).
3. Enable **trusted publishing** for the GitHub repo:
   - PyPI → Account settings → Publishing → Add a new pending publisher
   - Owner: `SignalSafeSoftware`, repository: `sqlphilosophy`, workflow: `publish.yml`, environment: `pypi`
4. In the GitHub repo, create an environment named **`pypi`** (Settings → Environments). No secrets required when using trusted publishing.

### 3. Monorepo consumers

DeliveryPlus continues to use the path dependency in root `pyproject.toml`:

```toml
sqlphilosophy = { path = "libs/sqlphilosophy", develop = true }
```

Released versions can also be pinned from PyPI when you choose to decouple.

## Version bump

Version lives in `src/sqlphilosophy/VERSION` (single line, semver).

From monorepo root:

```bash
bash scripts/bump-python-repository-version.sh patch   # or minor | major
```

Update `CHANGELOG.md` for the release.

## Pre-release checks

From **this directory** (`libs/sqlphilosophy`):

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pip install build twine
python -m build
twine check dist/*
```

From monorepo root:

```bash
./scripts/run_package.sh python-repository verify
./scripts/run_package.sh python-repository wheel
./scripts/smoke-python-repository-wheel.sh
```

## Publish to PyPI (recommended: GitHub Release)

1. Commit version bump + changelog.
2. Tag and push:

   ```bash
   git tag sqlphilosophy-v0.1.0
   git push origin sqlphilosophy-v0.1.0
   ```

   In the **standalone** repo, use `v0.1.0` instead of `sqlphilosophy-v0.1.0`.

3. Create a GitHub Release from the tag (Publish release). That triggers `.github/workflows/publish.yml`.

## Manual PyPI upload (fallback)

```bash
cd libs/sqlphilosophy
python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... python -m twine upload dist/*
```

Use an API token with scope limited to this project.

## Package boundaries

- No imports from `phobos`, `backend`, `vega`, Django, or Celery.
- Enforced by `tests/test_package_boundaries.py` and monorepo `backend/shared/tests/policy/test_sqlphilosophy_package_boundaries.py`.

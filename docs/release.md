# Release and clean archives

Use this guide when preparing a source archive for review, handoff, or release notes — separate from the PyPI publish flow in [RELEASING.md](../RELEASING.md).

## Create a clean archive from git

`git archive` exports only tracked files at a given revision. It does **not** include your working tree, local virtualenv, or ignored build artifacts:

```bash
git archive --format=zip --output sqlphilosophy-clean.zip HEAD
```

Replace `HEAD` with a tag (for example `v1.2.3`) or branch name when archiving a specific release.

The archive includes source, tests, docs, and package metadata (`pyproject.toml`, `CHANGELOG.md`, etc.) as committed in the repository.

## Do not include in uploaded or review archives

When sharing a zip or tarball outside `git archive`, strip or avoid packaging:

| Exclude | Why |
| ------- | --- |
| `.git/` | VCS history; not needed for source review |
| `.venv/`, `venv/` | Local Python environment |
| `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Tool caches |
| `.coverage`, `htmlcov/`, `coverage.xml` | Coverage output |
| `dist/`, `build/`, `*.egg-info/` | Build and install artifacts |
| `.DS_Store`, `__MACOSX/` | macOS metadata |

These paths are listed in [`.gitignore`](../.gitignore) so they stay out of commits; `git archive` already omits ignored untracked files, but manual zips often accidentally include them.

## Quick check before upload

```bash
unzip -l sqlphilosophy-clean.zip | grep -E '\.venv|__pycache__|\.pytest_cache|\.coverage|egg-info|\.DS_Store'
```

No matches means the archive is clean.

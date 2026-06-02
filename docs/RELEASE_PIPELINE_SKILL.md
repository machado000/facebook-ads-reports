# Release Pipeline Skill (GitHub Actions + PyPI)

This runbook describes the CI/CD release routine for this project using GitHub Actions and `uv`.

## Scope

- Python package versioning in `pyproject.toml`
- Changelog management in `docs/CHANGELOG.md`
- Automated publish to PyPI from GitHub Releases

Target release for this runbook: `v2.3.0` (minor release; API v25 and report model `date_preset` standardization)

## Workflow Files

- `.github/workflows/test.yml`: quality gates on `push` and `pull_request` to `main`
- `.github/workflows/release.yml`: release automation on `release.published`

## Required Repository Configuration

1. Add secret `PYPI_TOKEN` in GitHub repository or environment secrets.
2. Create environment `release` (recommended) and optionally require reviewer approval.
3. Protect `main` branch and require CI checks from `test.yml`.

## CI Workflow (Quality Gates)

Triggered on:

- push to `main`
- pull request to `main`

Runs matrix against Python 3.11-3.14:

```bash
uv sync --all-groups
uv run pytest
uv run mypy facebook_ads_reports
```

## Release Workflow (Automated Publish)

Triggered on:

- published GitHub Release with tag format `vX.Y.Z`

Steps executed:

1. Validate release tag follows semantic version pattern.
2. Install dependencies and rerun quality gates.
3. Update `pyproject.toml` version from release tag.
4. Insert new dated section in `docs/CHANGELOG.md` using release notes body.
5. Commit and push release metadata update to default branch.
6. Build package artifacts with `uv build`.
7. Skip publish if version already exists on PyPI.
8. Publish with `uv publish` using `PYPI_TOKEN`.
9. Upload `dist/*` artifacts to workflow run.

## Release Operator Checklist

1. Ensure all intended changes are merged into `main`.
2. Create a GitHub Release with tag `vX.Y.Z` and meaningful release notes.
3. Publish the release.
4. Monitor `.github/workflows/release.yml` run to completion.
5. Verify package availability on PyPI.
6. Verify updated `pyproject.toml` and `docs/CHANGELOG.md` commit landed on default branch.

## Local Verification Commands

Use this before opening a release:

```bash
uv sync --all-groups
uv run pytest
uv run mypy facebook_ads_reports
uv build
```

## Common Failure Modes

- `PYPI_TOKEN` missing or invalid: publish step fails.
- Release tag not in `vX.Y.Z` format: workflow fails at validation step.
- Empty/poor release notes: changelog entry is generated with limited context.
- Existing version on PyPI: publish is skipped by guard step.

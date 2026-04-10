# Generic Release Pipeline Skill (Python + uv)

Use this checklist to run a repeatable patch/minor/major release with `uv`, including docs, build, publish, commit, and push.

## Scope

- Python packages managed with `pyproject.toml`
- Build and publish using `uv`
- Changelog-driven release updates

## Prerequisites

- Clean branch strategy defined (usually `main` or release branch)
- PyPI authentication already configured for `uv publish`
- Local environment has `uv` installed

## Step 1: Baseline Safety

```bash
git status --short
git branch --show-current
```

- Confirm what is already modified.
- Do not revert unrelated user changes unless explicitly requested.

## Step 2: Version Bump

- Update `version` in `pyproject.toml`.
- Use semantic versioning:
  - Patch: bug fixes / internal clarity
  - Minor: backward-compatible feature additions
  - Major: breaking changes

## Step 3: Docs and Release Notes

- Update `CHANGELOG.md` with a new version section and release date.
- Update `README.md` release/development commands if process changed.
- Ensure examples and API docs reflect code-level behavior.

## Step 4: Dependency and Quality Gates

```bash
uv sync --all-groups
uv run pytest
uv run mypy facebook_ads_reports
```

- If quality checks fail, stop and fix before publishing.

## Step 5: Build

```bash
uv build
```

- Confirm artifacts were generated in `dist/` (wheel and sdist).

## Step 6: Publish

```bash
uv publish
```

- Publish target in this pipeline: direct PyPI.
- Verify published version availability on index/package page.

## Step 7: Commit and Push

```bash
git add <intended-files>
git commit -m "chore(release): vX.Y.Z"
git push
```

- Stage only files intended for this release.
- Keep commit message explicit and traceable.

## Optional Step 8: Tag

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

- Tagging is recommended for release traceability.

## Release Artifact Summary Template

Record this at the end of the run:

- Version:
- Branch:
- Commit SHA:
- Files changed:
- Test result:
- Type-check result:
- Build result:
- Publish result:
- Push result:

## Common Failure Modes

- `uv publish` auth failure: confirm token and repository access.
- Mypy failures from unrelated legacy paths: separate into pre-existing vs release-introduced failures.
- Dirty working tree confusion: always inspect `git status --short` before staging.

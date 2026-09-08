# Releasing SuperEnalotto Analysis

Releases are prepared and published by GitHub Actions. Do not edit the version,
create release branches, create version tags, or publish GitHub Releases by
hand during the normal release flow.

## Create a release

1. Open **Actions** in GitHub.
2. Select **Prepare Release**.
3. Choose **Run workflow** from `main`.
4. Enter the next stable SemVer version in `MAJOR.MINOR.PATCH` form, for
   example `0.2.1` or `0.3.0`.
5. Run the workflow.

The preparation workflow then:

- verifies that the requested version is valid and greater than the current
  project version;
- refuses to reuse an existing release branch or version tag;
- updates `pyproject.toml`;
- regenerates `uv.lock` with `uv lock`;
- runs Ruff, mypy strict, and pytest;
- verifies that only `pyproject.toml` and `uv.lock` changed;
- creates `release/vX.Y.Z`;
- commits the release metadata;
- opens a pull request against `main`; and
- explicitly dispatches the normal CI workflow on the release branch.

Review the generated pull request normally. Merge it only when the CI result is
green.

## Automatic publication

After the release PR is merged, the normal `CI` workflow runs on `main`.
`Publish Release` reacts only to a successful `CI` run produced by a push to
`main`.

Before publishing a new version, it verifies that:

- the CI-validated commit is still the current `main` HEAD;
- the project version is stable SemVer;
- the project package version in `uv.lock` matches `pyproject.toml`; and
- the new version is greater than every existing SemVer tag.

For a new version it creates an annotated `vX.Y.Z` tag and a GitHub Release
with generated release notes. It then removes the merged
`release/vX.Y.Z` branch.

The publisher is idempotent: ordinary later commits to `main` keep the already
released project version until the next release PR, so an existing tag plus an
existing GitHub Release is treated as a clean no-op even though the tag points
to the earlier release commit rather than the newest `main` commit.

If tag creation succeeded but GitHub Release creation failed, a later successful
CI run can recover the missing GitHub Release. Before doing so, the publisher
reads `pyproject.toml` and `uv.lock` from the tagged commit and verifies that
their project version matches the tag/current release version.

## Repository setting

`Prepare Release` uses the repository `GITHUB_TOKEN` to open its pull request.
GitHub therefore needs the repository setting that allows GitHub Actions to
create pull requests to be enabled under **Settings → Actions → General →
Workflow permissions**.

If that permission is disabled, preparation fails at the PR creation step
without publishing or merging anything; the pushed `release/vX.Y.Z` branch can
be removed and the workflow rerun after the setting is enabled.

# Shared workflows

Reusable release automation for NEAR Rust repositories.

## Release-plz

Keep the caller in `.github/workflows/release-plz.yml` so existing crates.io trusted publisher registrations continue to match. Configure each crate for its own repository and this caller filename, with no environment.

```yaml
name: Release-plz
on:
  push:
    branches: [main]

permissions: {}

jobs:
  release:
    uses: near/shared-workflows/.github/workflows/release-plz.yml@v1
    permissions:
      contents: write
      pull-requests: write
      id-token: write
      attestations: write
    secrets:
      pr-token: ${{ secrets.NEARPROTOCOL_CI_PR_ACCESS }}
```

If releases depend on CI, keep a reusable CI job in the caller and add `needs: validate` to `release`.

The workflow creates release PRs and publishes through Release-plz's native crates.io OIDC support. It attests the original published archives. It does not need a Cargo registry token. Release-plz uses its defaults unless the repository supplies `release-plz.toml` or `.release-plz.toml`.

- `pr-token` is required: use a bot token so release PRs trigger CI.
- `release-token` is optional: pass a bot token when tags or releases must trigger downstream workflows. Otherwise publishing uses the caller's `GITHUB_TOKEN` for GitHub operations.
- `apt-packages` is optional: a space-separated list of Ubuntu build dependencies, such as `libudev-dev`.

Release PR updates can cancel superseded updates. In-flight publishing is never cancelled by concurrency. The caller controls its triggers, CI dependencies, and granted permissions.

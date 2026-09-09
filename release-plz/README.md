# release-plz

A GitHub Action that automates versioning, changelog generation, and publishing for Rust crates using [release-plz](https://release-plz.ieni.dev/).

This action was highly inspired by [Marco Ieni's release-plz/action](https://github.com/release-plz/action)

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `command` | The release-plz command to run: `release-pr` or `release` | **Yes** | - |
| `config` | Path to `release-plz.toml` config file | No | `release-plz.toml` |
| `manifest-path` | Path to the project's `Cargo.toml` | No | - |
| `release-plz-version` | `release-plz` binary version | No | `0.3.157` |
| `cargo-semver-checks-version` | `cargo-semver-checks` version | No | `0.47.0` |
| `cargo-binstall-version` | `cargo-binstall` version | No | `1.18.1` |
| `token` | Token used to publish to the cargo registry | No | - |
| `verbose` | Print module and source locations in logs | No | - |
| `dry-run` | Add `--dry-run` flag to the `release` command | No | - |
| `crate-build-target-arch` | Build target architecture triple (e.g. `wasm32-unknown-unknown`) | No | host platform |
| `crate-toolchain-version` | Rust toolchain used to build and publish | No | - |

## Outputs

| Output | Description |
|---|---|
| `pr` | The first release PR opened by `release-plz` (JSON object) |
| `prs_created` | Whether any release PR was created (`true` / `false`) |
| `releases` | JSON array of releases created by the `release` command |
| `releases_created` | Whether any package was released (`true` / `false`) |

## Examples

### 1. Minimal - Release PR + Token-Based Publish

The simplest setup: one job opens release PRs, another publishes with a `CARGO_REGISTRY_TOKEN` secret.

```yaml
name: Release-plz

on:
  push:
    branches: [main]

jobs:
  release-plz-pr:
    name: Create release PR
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    concurrency:
      group: release-plz-${{ github.ref }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: dtolnay/rust-toolchain@stable
      - uses: near/actions/release-plz@main
        with:
          command: release-pr
          # cargo-toolchain-version: "stable" # <- enables downloading a rust inside action without specifying action
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  release-plz-release:
    name: Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: dtolnay/rust-toolchain@stable
      - uses: near/actions/release-plz@main
        with:
          command: release
          # cargo-toolchain-version: "stable" # <- enables downloading a rust inside action without specifying action
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
```

### 2. Trusted Publishing (crates.io OIDC)

Uses crates.io trusted publishing - no registry token needed. Requires that your crate is already registered on crates.io with a trusted publisher configured for your GitHub repository.

> **Note:** Trusted publishing does not support first-time crate publication.
> You must publish the crate manually at least once before enabling trusted publishing.

> **Note:** Additionally, we need to specify `persist-credentials : false` to prevent the checkout token from being stored in the local git config.

```yaml
name: Release-plz (Trusted Publishing)

on:
  push:
    branches: [main]

jobs:
  release-plz-pr:
    name: Create release PR
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    concurrency:
      group: release-plz-${{ github.ref }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: dtolnay/rust-toolchain@stable
      - uses: near/actions/release-plz@main
        with:
          command: release-pr
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  release-plz-release:
    name: Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
      id-token: write          # Required for OIDC trusted publishing
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: dtolnay/rust-toolchain@stable
      - uses: near/actions/release-plz@main
        with:
          command: release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # No CARGO_REGISTRY_TOKEN - crates.io uses the OIDC id-token
```

### 3. Token-Based Publish to a Private Registry

Pass the registry token directly via the `token` input or through the appropriate `CARGO_REGISTRIES_<NAME>_TOKEN` environment variable.

```yaml
name: Release to private registry

on:
  push:
    branches: [main]

jobs:
  release:
    name: Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: dtolnay/rust-toolchain@stable
      - uses: near/actions/release-plz@main
        with:
          command: release
          token: ${{ secrets.PRIVATE_REGISTRY_TOKEN }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 4. Cross-Compilation Target (e.g. WASM for NEAR)

Build and publish a crate targeting `wasm32-unknown-unknown` - typical for NEAR smart contracts.

> **Note**: Here, we utilize `crate-build-target-arch` and `crate-toolchain-version` to install desired arch and toolchain inside the action.

```yaml
name: Release NEAR contract

on:
  push:
    branches: [main]

jobs:
  release-plz-pr:
    name: Create release PR
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    concurrency:
      group: release-plz-${{ github.ref }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: near/actions/release-plz@main
        with:
          command: release-pr
          crate-build-target-arch: "wasm32-unknown-unknown"
          crate-toolchain-version: 1.86.0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  release-plz-release:
    name: Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
    concurrency:
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: near/actions/release-plz@main
        with:
          command: release
          crate-build-target-arch: "wasm32-unknown-unknown"
          crate-toolchain-version: 1.86.0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
```

### 5. Custom Config, Manifest Path, and Toolchain

Useful in monorepos or workspaces where the crate lives in a subdirectory.

```yaml
name: Release (workspace crate)

on:
  push:
    branches: [main]

jobs:
  release:
    name: Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: near/actions/release-plz@main
        with:
          command: release
          config: crates/my-crate/release-plz.toml
          manifest-path: crates/my-crate/Cargo.toml
          crate-build-target-arch: "aarch64-apple-darwin"
          crate-toolchain-version: "1.82.0"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
```

### 6. Dry Run

Validate what would be released without actually publishing anything.

```yaml
name: Release (dry run)

on:
  pull_request:
    branches: [main]

jobs:
  dry-run:
    name: Dry run
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: dtolnay/rust-toolchain@stable
      - uses: near/actions/release-plz@main
        with:
          command: release
          dry-run: "true"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 7. Using Outputs - Post-Release Notifications

React to releases by reading step outputs (e.g. send a Slack notification, trigger a deployment).

```yaml
name: Release and notify

on:
  push:
    branches: [main]

jobs:
  release:
    name: Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Run release-plz
        id: release-plz
        uses: near/actions/release-plz@main
        with:
          command: release
          crate-toolchain-version: "stable"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}

      - name: Print released packages
        if: steps.release-plz.outputs.releases_created == 'true'
        run: |
          echo "Releases: ${{ steps.release-plz.outputs.releases }}"
          # Parse individual releases
          echo '${{ steps.release-plz.outputs.releases }}' \
            | jq -r '.[] | "\(.package_name) \(.version)"'

      - name: Notify on release
        if: steps.release-plz.outputs.releases_created == 'true'
        run: echo "::notice::New releases published - see output above."
```

## Notes

- **`fetch-depth: 0`** is required so release-plz can read the full git history for changelog generation.
- **`persist-credentials: false`** prevents the checkout token from being stored in the local git config.
- **Concurrency** should only be applied to the `release-pr` job. Do **not** add it to the `release` job - cancelling an in-progress release could skip package publications.
- **Trusted publishing** requires the crate to already exist on crates.io with a trusted publisher configured for your repo. First-time publication must be done manually.
- **Token-based publishing** works with any registry. Set `CARGO_REGISTRY_TOKEN` for crates.io, or `CARGO_REGISTRIES_<NAME>_TOKEN` for alternative registries.

# Implementation Plan

## 1. Repository and documentation audit

- Record Windows identity, repository root, status, remotes, tracking branch,
  fetch result, divergence graph, and object IDs.
- Read applicable instructions, README files, manifests, build scripts, Trellis
  task/spec indexes, and CI/container/version files.
- Verify the writable remote is the user's fork and upstream pushing is disabled.

## 2. macOS audit

- Verify the actual remote host identity.
- Discover the matching checkout by remote URL.
- Fetch and record status, remotes, tracking state, divergence, outgoing
  commits, staged/unstaged/untracked paths, and ignored candidates.
- If a complete change set exists, inspect, test, privacy-scan, commit by
  concern, and push normally; otherwise leave the checkout untouched.

## 3. Local-only file reconciliation

- Inventory useful candidates from both active checkouts, the authorized legacy
  tree, and the private-file archive.
- Exclude dependencies, virtual environments, caches, generated build output,
  and Trellis backup/runtime directories.
- Compare metadata and SHA-256 without emitting values from sensitive files.
- Copy only required missing files, verify hashes, and re-check Git ignore state.

## 4. Environment and workflow verification

- Record Python, `uv`, .NET SDK, PowerShell, Git, and other repository-required
  tool versions.
- Materialize MCP dependencies from the lockfile and run help/import/compile or
  available test entry points.
- Discover the installed game location without writing shared configuration.
- Run a real .NET restore/build against the local game assemblies and exercise
  the build script in build-only mode.
- Verify the live local HTTP/MCP bridge only when the game/mod is already
  running; do not start gameplay or mutate a run.
- Inspect WSL and Docker installation health only as contextual evidence and
  mark their project workflows not applicable unless repository evidence says
  otherwise.

## 5. Fix and synchronize when necessary

- Search before changing any shared value or behavior.
- Make the smallest cross-platform fix and add proportional validation.
- Run the complete affected workflow matrix and `git diff --check`.
- Review staged and outgoing content for secrets, absolute paths, credentials,
  local account data, and unfamiliar files.
- Commit logically and push normally to the user's fork.
- Fetch and fast-forward the other checkout, then rerun affected checks there.

## 6. Final acceptance

- On both devices: fetch/prune, status, HEAD/upstream comparison, divergence,
  outgoing commits, and `git diff --check`.
- Confirm required local-only files exist where needed and remain untracked.
- Produce the requested two-device result table and complete evidence list,
  including all skipped or unverified workflows and reasons.

## Validation Commands

Exact device-specific paths are resolved at runtime and are not recorded here.
The validation set includes:

- `git status --short --branch`
- `git rev-list --left-right --count '@{u}...HEAD'`
- `git diff --check`
- `dotnet --info` and `dotnet build`
- `uv --version`, `uv sync --locked`, and MCP server help/import checks
- project-provided test commands discovered during source inspection
- local HTTP and MCP state probes when the game bridge is already available

## Stop Conditions

Stop before copying, committing, or pushing if file ownership, deletion intent,
secret content, remote ownership, or divergent tracked history cannot be safely
resolved. Preserve that state and continue all independent read-only checks.

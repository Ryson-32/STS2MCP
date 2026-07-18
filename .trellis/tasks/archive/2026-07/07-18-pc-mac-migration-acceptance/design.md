# Design: PC/Mac migration and compatibility acceptance

## Boundaries

The public Git repository carries source code, project documentation, tests,
and shared Trellis artifacts. Each device retains its own ignored MCP client
configuration, mod runtime configuration, virtual environment, compiled output,
and other machine-specific state.

The writable public fork is the only publication target. The original project
remote remains fetch-only. Legacy and archive trees are read-only inputs.

## Evidence Flow

1. Establish repository identity and Git safety on Windows.
2. Locate the macOS checkout by remote URL, then establish the same evidence.
3. Build metadata-only inventories for valuable local-only candidates on both
   devices and read-only legacy/archive sources.
4. Classify each candidate as required local state, divergent device state, or
   reproducible output.
5. Copy only a clearly required missing file. Verify the destination hash and
   confirm it remains ignored.
6. Discover the real workflow matrix from repository artifacts, then validate
   the Windows environment and run those workflows.
7. If code changes are needed, keep one device as the writer, verify, privacy
   scan, commit and push, then fast-forward the other device.
8. Re-run final Git and privacy checks on both devices.

## Private File Contract

- Inventory output contains path/purpose, byte size, modification time,
  SHA-256, and configuration key names only.
- Secret values and machine-specific command paths are never copied into task
  artifacts or shared documentation.
- Same-path hash differences are not resolved by overwriting. Both variants are
  preserved until their device-specific purpose is understood.
- Active databases, if any are discovered, are exported through their native
  backup path rather than copied live.

## Compatibility Strategy

- Windows mod build: .NET 9 plus local game assemblies.
- macOS mod build: .NET 9 plus assemblies inside the application bundle.
- MCP bridge: Python 3.11+ managed by `uv` from the checked-in lockfile.
- WSL and Docker are conditional checks, not default execution targets, because
  the repository currently defines neither Linux-only nor container workflows.
- Fixes must be path-agnostic and avoid hard-coded OS accounts, absolute game
  paths, Homebrew prefixes, or local AI client configuration.

## Rollback and Publication

No destructive rollback commands are used. A failed copy leaves the source
unchanged; a conflicting destination is not overwritten. A failed validation
prevents commit and push. Publication uses ordinary commits on the current
shared branch and a normal push to the user's fork only.

# PC/Mac migration and compatibility acceptance

## Goal

Complete a safe two-device migration acceptance for the public fork so that the
Windows and macOS checkouts share the same published Git state, required
local-only runtime files are present on the devices that need them, and every
applicable non-production development workflow has been exercised on Windows.

## Confirmed Facts

- The writable remote is the user's public fork; the original upstream remote
  is fetch-only and has pushing disabled.
- Both active checkouts currently use `main`, track `origin/main`, and had no
  tracked or untracked work before this task began.
- There are no GitHub Actions workflows, Dockerfiles, Compose files, or Node
  manifests in this repository.
- The mod build targets .NET 9 and compiles against assemblies from a local
  Slay the Spire 2 installation.
- The MCP bridge requires Python 3.11 or newer and uses `uv.lock` for an
  isolated environment.
- Local MCP client configuration, mod configuration, build outputs, virtual
  environments, and Trellis runtime backups must remain outside Git.

## Requirements

- Preserve unfamiliar files and history. Do not reset, clean, rebase shared
  history, force-push, or overwrite same-path files whose ownership is unclear.
- Identify the macOS checkout by Git remote identity and collect evidence from
  the real remote device.
- Inspect the Windows checkout, macOS checkout, legacy read-only source, and
  private-file archive for useful ignored or local-only project files.
- Compare candidate private files by relative purpose, size, modification time,
  and SHA-256. Report configuration keys without reporting secret values.
- Restore only files that are clearly required and missing. Preserve divergent
  same-path files rather than replacing them.
- Keep all machine-specific paths, credentials, tokens, private keys, user data,
  and local MCP/client configuration out of commits.
- Install only the smallest missing runtime or project dependency that the
  repository actually requires.
- Run the applicable Windows build, MCP dependency, syntax/test, packaging, and
  local smoke workflows. Treat WSL and Docker as not applicable unless an
  existing repository workflow requires them.
- If a low-risk compatibility defect is found, make the smallest project-level
  correction, add proportional validation, commit by concern, push normally to
  the writable fork, and fast-forward the other checkout.
- End with both checkouts clean, at the same upstream commit, with divergence
  `0 0`, `git diff --check` passing, and no private file tracked.

## Acceptance Criteria

- [x] Windows and macOS repository identity, remotes, branch, upstream, HEAD,
      divergence, dirty state, and outgoing commits are verified.
- [x] No complete macOS development result remains uncommitted or unpushed.
- [x] Useful ignored/private candidates from all authorized sources are
      inventoried and either restored with matching SHA-256 or explicitly
      excluded as divergent, obsolete, or reproducible.
- [x] Required Windows runtimes and project environments are present and their
      versions are recorded.
- [x] Every applicable non-production workflow discovered from documentation,
      manifests, scripts, and source is run and its result recorded.
- [x] WSL and Docker are either verified because the repository requires them,
      or explicitly marked not applicable with repository evidence.
- [x] Any compatibility fix is validated, privacy-scanned, committed in a
      logical batch, pushed normally, and fast-forwarded to the other checkout.
- [x] Final Windows and macOS Git checks are clean and synchronized.
- [x] The final report distinguishes passed, failed, skipped, and unverified
      work without claiming success from file presence alone.

## Out of Scope

- Production deployment, releases, tags, pull requests, remote repository
  settings, and third-party upstream writes.
- Destructive cleanup of caches, build outputs, Docker resources, archives, or
  unknown files.
- Changing user-level AI client configuration.
- Reconstructing intentionally deleted legacy repositories.

## Open Questions

None. The user supplied the operational and safety boundaries and explicitly
authorized execution through normal commit/push and cross-device fast-forward.

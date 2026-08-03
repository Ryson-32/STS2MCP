# Python MCP Bridge Contract

## Boundary

`mcp/server.py` is a thin pass-through from MCP tools to the C# HTTP API at
`http://localhost:15526`. It may validate tool arguments, apply small ergonomic coercions and
format transport errors. It must not interpret game rules, maintain a second game state, choose
actions or mutate the game outside the C# API.

## Tool mapping

- Each MCP tool maps to one documented HTTP request unless the public API explicitly defines a
  multi-step operation.
- Tool names, arguments and docstrings must remain consistent with `docs/raw-full.md` and
  `docs/raw-simplified.md`.
- Surface connection, timeout and HTTP errors with enough context to diagnose the bridge; never
  pretend an action succeeded when the mod did not confirm it.
- Keep client URLs, game paths and MCP-client registration details in user-local configuration,
  not committed machine-specific files.

## Validation

- For Python-only changes, run the package's narrow import/syntax check from `mcp/` and exercise
  the affected tool against a running mod when runtime behavior changed.
- For shared API changes, build and smoke-test the C# side first, then verify the MCP mapping and
  update all reference documentation in the same change.

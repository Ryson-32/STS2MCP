# C# Mod And HTTP API Contract

## Ownership

The C# mod is the authoritative game-integration layer. It reads and mutates game state, validates
game rules, exposes the local HTTP API on `localhost:15526`, and owns multiplayer behavior.
The Python MCP package is only a client adapter and must not duplicate this logic.

## Change contract

- Keep state serialization in the `McpMod.*.cs` partial classes and reuse the existing formatting,
  state-builder and action helpers instead of adding a second protocol layer.
- A new state field, action, screen or endpoint is a public API change. Update
  `docs/raw-full.md`, `docs/raw-simplified.md` and the matching MCP tool/docstring together.
- Preserve existing action response and error shapes. When the game is not in the required state,
  return an explicit error rather than guessing or silently advancing.
- Multiplayer-specific changes must be checked with the mod enabled and disabled before attributing
  a problem to the base game.

## Validation

- Build with `./build.ps1 -GameDir "<game path>"` on Windows or the README's documented
  `dotnet build` flow on macOS/Linux.
- Non-trivial game integration changes require a manual in-game smoke test of the affected state
  and action path. A build alone does not prove runtime compatibility.
- Record the tested game version and keep the README's “Tested against” statement accurate.
